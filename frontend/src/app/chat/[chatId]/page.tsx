"use client";

import styles from './styles.module.css'
import { useParams } from "next/navigation";
import { useState } from "react";
import ChatBox from "@/components/ChatBox/chatbox";
import ChatMessage from "@/components/ChatMessage/chatmessage";

export default function ChatPage() {
    const { chatId } = useParams();
    const [inputValue, setInputValue] = useState('');
    const [messages, setMessages] = useState<string[]>([]);

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