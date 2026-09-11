# File: app/rag_pipeline.py
"""
RAGPipeline for OceanSense AI.

Query routing:
  1. General knowledge  → pass straight to LLM (no retrieval needed)
  2. Live / current     → ONC API fetch → summarise → inject as context
  3. Historical / trend → vector store retrieval → inject as context
  4. Hybrid             → ONC API + vector store combined

The LLM (Mistral via Ollama) always gets a structured prompt with:
  - A system role defining its persona
  - Any retrieved context (live or historical)
  - The user's original question
"""

import os
import re
import logging
from typing import Iterator, List, Tuple, Optional

from .chroma_utils import ChromaRetriever
from .mistral_utils import MistralLLM
from .data_utils import (
    load_all_csvs,
    load_all_csvs_multiparams,
    extract_metadata_from_file,
)
from .onc_client import ONCClient, ONCAPIError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Query classification helpers
# ---------------------------------------------------------------------------

_LIVE_KEYWORDS = [
    r"\b(today|tonight|right now|currently|current|live|latest|now|recent)\b",
    r"\b(this week|this month|last \d+ (hour|day|week)s?)\b",
    r"\b(what is|what'?s) the (water |sea )?(temperature|salinity|oxygen|turbidity|chlorophyll)\b",
    r"\b(how (warm|cold|hot) is|how (high|low) is)\b",
]

_HISTORICAL_KEYWORDS = [
    r"\b(trend|over time|historically|long.?term|past (year|month|decade|season))\b",
    r"\b(in 20\d{2}|between \d{4} and \d{4}|from \d{4} to \d{4})\b",
    r"\b(average|mean|maximum|minimum) (over|across|during)\b",
    r"\b(has .+ changed|how has|variation|variability|anomal)\b",
]

_OCEAN_SCIENCE_KEYWORDS = [
    r"\b(ocean|marine|sea|coastal|salinity|temperature|oxygen|chlorophyll|"
    r"turbidity|fluorescence|conductivity|dissolved|tidal|upwelling|thermocline|"
    r"halocline|pycnocline|bloom|hypoxic|dead zone|carbon|pH|acidification)\b",
]

_PARAMETER_PATTERNS = {
    "temperature":  r"\b(temperature|temp|warm|cold|heat)\b",
    "salinity":     r"\b(salinity|saline|salt)\b",
    "oxygen":       r"\b(oxygen|dissolved oxygen|do\b|hypoxic|anoxic)\b",
    "chlorophyll":  r"\b(chlorophyll|algae|bloom|phytoplankton)\b",
    "turbidity":    r"\b(turbidity|turbid|murky|clarity|sediment)\b",
    "conductivity": r"\b(conductivity|conduct)\b",
    "fluorescence": r"\b(fluorescence|fluor|cdom)\b",
}

_LOCATION_PATTERNS = {
    "cambridge bay":  r"\b(cambridge bay|cambridge)\b",
    "saanich":        r"\b(saanich)\b",
    "bamfield":       r"\b(bamfield|barkley)\b",
    "victoria":       r"\b(victoria)\b",
    "fraser":         r"\b(fraser)\b",
    "tsawwassen":     r"\b(tsawwassen|swartz bay|ferry)\b",
}


def _matches_any(text: str, patterns: List[str]) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in patterns)


def _extract_parameter(query: str) -> Optional[str]:
    q = query.lower()
    for param, pattern in _PARAMETER_PATTERNS.items():
        if re.search(pattern, q):
            return param
    return None


def _extract_location(query: str) -> Optional[str]:
    q = query.lower()
    for location, pattern in _LOCATION_PATTERNS.items():
        if re.search(pattern, q):
            return location
    return None


class QueryIntent:
    GENERAL     = "general"       # No ocean data needed
    LIVE        = "live"          # Needs ONC API
    HISTORICAL  = "historical"    # Needs vector store
    HYBRID      = "hybrid"        # Needs both


def classify_query(query: str) -> str:
    is_ocean   = _matches_any(query, _OCEAN_SCIENCE_KEYWORDS)
    is_live    = _matches_any(query, _LIVE_KEYWORDS)
    is_hist    = _matches_any(query, _HISTORICAL_KEYWORDS)

    if not is_ocean:
        return QueryIntent.GENERAL
    if is_live and is_hist:
        return QueryIntent.HYBRID
    if is_live:
        return QueryIntent.LIVE
    if is_hist:
        return QueryIntent.HISTORICAL
    # Ocean topic but no time signal → try historical retrieval
    return QueryIntent.HISTORICAL


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are OceanSense AI, a knowledgeable and approachable assistant specialising in \
ocean science and marine environmental data from Ocean Networks Canada (ONC). \
You help educators, students, community members, and researchers explore and understand ocean data.

Guidelines:
- When context is provided (sensor data), ground your answer in that data first.
- Always include units when discussing measurements.
- If data shows anomalies or concerning trends, flag them clearly but calmly.
- If you are uncertain or the data is insufficient, say so honestly.
- For general science questions not requiring sensor data, answer from your knowledge.
- Keep answers clear and accessible — avoid unnecessary jargon.
- Never fabricate sensor readings. If no data is available, say so explicitly.
"""


def _build_prompt(query: str, context_chunks: List[str]) -> str:
    if context_chunks:
        context_block = "\n".join(f"  - {c}" for c in context_chunks)
        context_section = f"\nRelevant sensor data context:\n{context_block}\n"
    else:
        context_section = "\n(No sensor data context available for this query.)\n"

    return (
        f"[INST] <<SYS>>\n{SYSTEM_PROMPT}<</SYS>>\n"
        f"{context_section}\n"
        f"User question: {query}\n\n"
        f"Provide a clear, accurate answer. If multiple sensor readings are given, "
        f"summarise the trends rather than listing every value.\n"
        f"[/INST]"
    )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

class RAGPipeline:
    def __init__(self, dataset_dir: str):
        self.retriever   = ChromaRetriever()
        self.llm         = MistralLLM()
        self.onc_client  = ONCClient()          # reads ONC_TOKEN from env
        self.dataset_dir = dataset_dir

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def initialize_dataset(self):
        """
        Index all CSVs in dataset_dir.
        Files sharing a device code + time span are merged into
        multi-parameter daily chunks before indexing.
        """
        self.retriever = ChromaRetriever()

        logger.info("Building multi-parameter chunks from datasets …")
        all_docs = load_all_csvs_multiparams(self.dataset_dir)

        # Also index single-file docs for any files not caught by grouping
        for fname in os.listdir(self.dataset_dir):
            if not fname.endswith(".csv"):
                continue
            fpath = os.path.join(self.dataset_dir, fname)
            meta  = extract_metadata_from_file(fpath)
            docs  = load_all_csvs(fpath, meta)
            # Deduplicate by content (multi-param already included some of these)
            all_docs.extend(docs)

        # Deduplicate
        seen = set()
        unique_docs = []
        for d in all_docs:
            if d not in seen:
                seen.add(d)
                unique_docs.append(d)

        logger.info(f"Total unique documents to index: {len(unique_docs)}")

        BATCH_SIZE = 5000
        for i in range(0, len(unique_docs), BATCH_SIZE):
            self.retriever.add_documents(unique_docs[i:i + BATCH_SIZE])
            logger.info(f"Indexed batch {i // BATCH_SIZE + 1}")

        return True

    # ------------------------------------------------------------------
    # Query handling
    # ------------------------------------------------------------------

    def _retrieve_historical(self, query: str, k: int = 5) -> List[str]:
        """Retrieve relevant chunks from the vector store."""
        try:
            return self.retriever.query(query, k=k)
        except Exception as e:
            logger.warning(f"Vector store retrieval failed: {e}")
            return []

    def _retrieve_live(self, query: str) -> Tuple[List[str], str]:
        """
        Attempt a live ONC API fetch based on the query.
        Returns (context_chunks, status_message).
        """
        parameter = _extract_parameter(query)
        location  = _extract_location(query)

        if not parameter:
            return [], "Could not identify a parameter in the query for live lookup."
        if not location:
            return [], "Could not identify a location in the query for live lookup."

        df, status = self.onc_client.fetch_recent_for_query(
            parameter=parameter,
            location_hint=location,
        )
        if df.empty:
            return [], status

        summary = ONCClient.dataframe_to_summary(df, parameter, location)
        return [summary], status

    def _resolve_context(self, query: str) -> Tuple[str, List[str], str]:
        """Classify the query and gather any context chunks it needs."""
        intent = classify_query(query)
        logger.info(f"Query intent: {intent} | Query: {query!r}")

        context_chunks: List[str] = []
        live_status = ""

        if intent == QueryIntent.GENERAL:
            # No retrieval — LLM answers from its own knowledge
            pass

        elif intent == QueryIntent.LIVE:
            live_chunks, live_status = self._retrieve_live(query)
            context_chunks.extend(live_chunks)
            # If live failed, fall back to historical
            if not live_chunks:
                logger.info(f"Live fetch failed ({live_status}), falling back to historical.")
                context_chunks.extend(self._retrieve_historical(query))

        elif intent == QueryIntent.HISTORICAL:
            context_chunks.extend(self._retrieve_historical(query))

        elif intent == QueryIntent.HYBRID:
            live_chunks, live_status = self._retrieve_live(query)
            context_chunks.extend(live_chunks)
            context_chunks.extend(self._retrieve_historical(query))

        return intent, context_chunks, live_status

    def ask(self, query: str) -> str:
        intent, context_chunks, live_status = self._resolve_context(query)

        prompt = _build_prompt(query, context_chunks)
        answer = self.llm.generate_answer(prompt)

        # Append live status as a footnote if it contains useful info
        if live_status and intent in (QueryIntent.LIVE, QueryIntent.HYBRID):
            answer = answer.strip() + f"\n\n_[Data source: {live_status}]_"

        return answer

    def ask_stream(self, query: str) -> Iterator[str]:
        """Same as ask(), but yields answer text chunks as they're generated."""
        intent, context_chunks, live_status = self._resolve_context(query)

        prompt = _build_prompt(query, context_chunks)
        for chunk in self.llm.stream_answer(prompt):
            yield chunk

        if live_status and intent in (QueryIntent.LIVE, QueryIntent.HYBRID):
            yield f"\n\n_[Data source: {live_status}]_"
