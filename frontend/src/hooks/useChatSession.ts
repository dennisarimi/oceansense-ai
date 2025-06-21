"use client"

import { useEffect, useState } from 'react'

export default function useChatSession(sessionkKey: string = "chatMessages") {
    const [messages, setMessages] = useState<string[]>([]);
    const [inputValue, setInputValue] = useState('');

    // load messages from session on mount
    useEffect(() => {
        const stored = sessionStorage.getItem(sessionkKey);
        if (stored) {
            setMessages(JSON.parse(stored));

        }
    }, [sessionkKey]);

    // send handler: update messages and seesionStorage
    const handleSend = () => {
        const trimmed = inputValue.trim();
        if (!trimmed) return;

        const updated = [...messages, trimmed];
        setMessages(updated);
        sessionStorage.setItem(sessionkKey, JSON.stringify(updated));
        setInputValue('');
    };

    return {
        messages,
        inputValue,
        setInputValue,
        handleSend,
    };
}