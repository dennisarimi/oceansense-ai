const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const sendMessageToLLM = async (message: string): Promise<string> => {
  const res = await fetch(`${API_URL}/ask`, {
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

export const checkHealth = async (): Promise<boolean> => {
  try {
    const res = await fetch(`${API_URL}/health`);
    return res.ok;
  } catch (error) {
    console.error("Health check failed:", error);
    return false;
  }
};
