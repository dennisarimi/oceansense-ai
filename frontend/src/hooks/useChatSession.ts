"use client"

import { useEffect, useState } from 'react'
import { sendMessageToLLM } from '@/utils/api';

type ChatMessage = {
  sender: "user" | "assistant";
  message: string;
};

export default function useChatSession(sessionKey: string = "chatMessages") {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isSessionLoaded, setIsSessionLoaded] = useState(false);

    // Load messages from session on mount
    useEffect(() => {
        const stored = sessionStorage.getItem(sessionKey);
        if (stored) {
            try {
                const parsedMessages = JSON.parse(stored);
                setMessages(parsedMessages);
            } catch (e) {
                console.error("Failed to parse stored messages:", e);
            }
        }
        setIsSessionLoaded(true);
    }, [sessionKey]);

    // Save messages to sessionStorage whenever they change
    useEffect(() => {
        if (isSessionLoaded) {
            sessionStorage.setItem(sessionKey, JSON.stringify(messages));
        }
    }, [messages, isSessionLoaded, sessionKey]);

    // Streams a reply for `query`, appending a new assistant bubble on the
    // first chunk and growing it as more text arrives. `isLoading` stays
    // true (showing the "thinking" indicator) until that first chunk.
    //
    // The setMessages updaters here must stay pure (derive everything from
    // `prev`, no closure mutation) — React's Strict Mode double-invokes
    // updater functions in dev to catch impurity, and an updater that
    // mutates an outer flag will see stale/inconsistent state on the
    // second invocation.
    const streamAssistantReply = async (query: string) => {
        setIsLoading(true);
        try {
            await sendMessageToLLM(query, (chunk) => {
                setIsLoading(false);
                setMessages((prev) => {
                    const last = prev[prev.length - 1];
                    if (!last || last.sender !== "assistant") {
                        return [...prev, { sender: "assistant", message: chunk }];
                    }
                    const updated = [...prev];
                    updated[updated.length - 1] = { ...last, message: last.message + chunk };
                    return updated;
                });
            });
        } catch (err) {
            console.error("Failed to fetch response:", err);
            setMessages((prev) => {
                const last = prev[prev.length - 1];
                const errorMsg: ChatMessage = { sender: "assistant", message: "[Error fetching response]" };
                return last && last.sender === "assistant"
                    ? [...prev.slice(0, -1), errorMsg]
                    : [...prev, errorMsg];
            });
        } finally {
            setIsLoading(false);
        }
    };

    // Handle initial message (if only one user message exists after loading)
    useEffect(() => {
        if (isSessionLoaded && messages.length === 1 && messages[0].sender === 'user') {
            streamAssistantReply(messages[0].message);
        }
    }, [isSessionLoaded]);

    const handleSend = async () => {
        const trimmed = inputValue.trim();
        if (!trimmed || isLoading) return;

        const userMsg: ChatMessage = { sender: "user", message: trimmed };
        setMessages((prev) => [...prev, userMsg]);
        setInputValue("");

        await streamAssistantReply(trimmed);
    };

    return {
        messages,
        inputValue,
        setInputValue,
        handleSend,
        isLoading,
    };
}