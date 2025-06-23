export const sendMessageToLLM = async (message: string): Promise<string> => {
  const res = await fetch("http://localhost:8000/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query: message }),
  });

  if (!res.ok) throw new Error("Failed to fetch response");
  const data = await res.json();
  return data.answer;
};
