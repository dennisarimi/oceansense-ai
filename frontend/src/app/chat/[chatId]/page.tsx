"use client";

import styles from './styles.module.css'
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import ChatBox from "@/components/ChatBox/chatbox";
import ChatMessage from "@/components/ChatMessage/chatmessage";

export default function ChatPage() {
    const { chatId } = useParams();
    const searchParams = useSearchParams();

    const [inputValue, setInputValue] = useState('');
    const [messages, setMessages] = useState<string[]>([]);

    // Read initial message from URL
    useEffect(() => {
        const initialMessage = sessionStorage.getItem('initialMessage');
        if (initialMessage) {
            setMessages([initialMessage]);
            // sessionStorage.removeItem('initialMessage');
        }
    }, [searchParams]);
    
    const handleSend = () => {
        if (inputValue.trim()) {
        setMessages((prev) => [...prev, inputValue]);
        setInputValue('');
        }
    };
    
    return(
        <div className={styles.chatContainer}>
            {messages.length > 0 && (
                <div className={styles.chatMessages}>
                {messages.map((query, index) => (
                    <ChatMessage
                    sender="user"
                    message={query}
                    key={index}
                    />
                ))}
                </div>
            )}
            <div className={styles.chatBoxWrapper}>
                <ChatBox
                    inputValue={inputValue}
                    setInputValue={setInputValue}
                    onSend={handleSend}
                />
            </div>
        </div>
    );
}