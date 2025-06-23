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

    // Handle initial message (if only one user message exists after loading)
    useEffect(() => {
        const handleInitialMessage = async () => {
            if (messages.length === 1 && messages[0].sender === 'user') {
                setIsLoading(true);
                try {
                    const response = await sendMessageToLLM(messages[0].message);
                    const botMsg: ChatMessage = { sender: "assistant", message: response };
                    setMessages((prev) => [...prev, botMsg]);
                } catch (err) {
                    console.error("Failed to fetch response for initial message:", err);
                    const errorMsg: ChatMessage = { sender: "assistant", message: "[Error fetching initial response]" };
                    setMessages((prev) => [...prev, errorMsg]);
                } finally {
                    setIsLoading(false);
                }
            }
        };

        if (isSessionLoaded) {
            handleInitialMessage();
        }
    }, [isSessionLoaded]);

    const handleSend = async () => {
        const trimmed = inputValue.trim();
        if (!trimmed || isLoading) return;

        const userMsg: ChatMessage = { sender: "user", message: trimmed };
        setMessages((prev) => [...prev, userMsg]);
        setInputValue("");
        setIsLoading(true);

        try {
            const response = await sendMessageToLLM(trimmed);
            const botMsg: ChatMessage = { sender: "assistant", message: response };
            setMessages((prev) => [...prev, botMsg]);
        } catch (err) {
            console.error("Failed to fetch response:", err);
            const errorMsg: ChatMessage = { sender: "assistant", message: "[Error fetching response]" };
            setMessages((prev) => [...prev, errorMsg]);
        } finally {
            setIsLoading(false);
        }
    };

    return {
        messages,
        inputValue,
        setInputValue,
        handleSend,
        isLoading,
    };
}