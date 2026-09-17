"use client"

import { useEffect, useState } from 'react'
import { sendMessageToLLM, ChatMessage } from '@/utils/api';

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

    // How fast revealed text appears on screen, independent of how fast the
    // backend actually generates it (a GPU can produce chunks far faster
    // than is comfortable to read).
    const REVEAL_MS_PER_CHAR = 15;

    const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

    const appendVisible = (piece: string) => {
        setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (!last || last.sender !== "assistant") {
                return [...prev, { sender: "assistant", message: piece }];
            }
            const updated = [...prev];
            updated[updated.length - 1] = { ...last, message: last.message + piece };
            return updated;
        });
    };

    // Streams a reply for `query`. Incoming chunks land in a buffer as fast
    // as the network delivers them; a separate loop drains that buffer one
    // character at a time at a fixed pace, so generation speed and display
    // speed are decoupled. `isLoading` stays true (showing the "thinking"
    // indicator) until the first character is revealed.
    //
    // The setMessages updater in appendVisible must stay pure (derive
    // everything from `prev`, no closure mutation) — React's Strict Mode
    // double-invokes updater functions in dev to catch impurity.
    const streamAssistantReply = async (query: string, history: ChatMessage[]) => {
        setIsLoading(true);

        const state: { buffer: string; fetchDone: boolean; fetchError: unknown } = {
            buffer: "",
            fetchDone: false,
            fetchError: null,
        };

        const revealLoop = async () => {
            while (state.buffer.length > 0 || !state.fetchDone) {
                if (state.buffer.length > 0) {
                    const piece = state.buffer[0];
                    state.buffer = state.buffer.slice(1);
                    setIsLoading(false);
                    appendVisible(piece);
                }
                await sleep(REVEAL_MS_PER_CHAR);
            }
        };

        const fetchPromise = sendMessageToLLM(query, history, (chunk) => {
            state.buffer += chunk;
        })
            .catch((err) => {
                state.fetchError = err;
            })
            .finally(() => {
                state.fetchDone = true;
            });

        await Promise.all([fetchPromise, revealLoop()]);

        if (state.fetchError) {
            console.error("Failed to fetch response:", state.fetchError);
            setMessages((prev) => {
                const last = prev[prev.length - 1];
                const errorMsg: ChatMessage = { sender: "assistant", message: "[Error fetching response]" };
                return last && last.sender === "assistant"
                    ? [...prev.slice(0, -1), errorMsg]
                    : [...prev, errorMsg];
            });
        }
        setIsLoading(false);
    };

    // Handle initial message (if only one user message exists after loading)
    useEffect(() => {
        if (isSessionLoaded && messages.length === 1 && messages[0].sender === 'user') {
            streamAssistantReply(messages[0].message, []);
        }
    }, [isSessionLoaded]);

    const handleSend = async () => {
        const trimmed = inputValue.trim();
        if (!trimmed || isLoading) return;

        const userMsg: ChatMessage = { sender: "user", message: trimmed };
        const history = messages;
        setMessages((prev) => [...prev, userMsg]);
        setInputValue("");

        await streamAssistantReply(trimmed, history);
    };

    return {
        messages,
        inputValue,
        setInputValue,
        handleSend,
        isLoading,
    };
}