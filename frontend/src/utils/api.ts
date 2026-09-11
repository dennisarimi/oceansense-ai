const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Streams the assistant's reply, invoking onChunk as each piece of text
 * arrives. Resolves with the full accumulated answer once done.
 */
export const sendMessageToLLM = async (
  message: string,
  onChunk: (chunk: string) => void
): Promise<string> => {
  const res = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query: message }),
  });

  if (!res.ok || !res.body) throw new Error("Failed to fetch response");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let full = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const text = decoder.decode(value, { stream: true });
    full += text;
    onChunk(text);
  }

  return full;
};

export const checkHealth = async (): Promise<boolean> => {
  try {
    const res = await fetch(`${API_URL}/health`);
    return res.ok;
  } catch (error) {
    console.error("Health check failed:", error);
    return false;
  }
};
