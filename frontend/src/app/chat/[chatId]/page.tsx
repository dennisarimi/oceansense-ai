"use client";

import styles from './styles.module.css'
import { useParams, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import ChatBox from "@/components/ChatBox/chatbox";
import ChatMessage from "@/components/ChatMessage/chatmessage";
import useChatSession from '@/hooks/useChatSession';

export default function ChatPage() {
    const { chatId } = useParams();
    const { messages, inputValue, setInputValue, handleSend } = useChatSession();
    
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