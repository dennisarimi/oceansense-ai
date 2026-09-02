"use client";

import styles from './styles.module.css'
import { useParams } from "next/navigation";
import { useRef, useEffect } from "react";
import ChatBox from "@/components/ChatBox/chatbox";
import ChatMessage from "@/components/ChatMessage/chatmessage";
import useChatSession from '@/hooks/useChatSession';

export default function ChatPage() {
    const { chatId } = useParams();
    const { messages, inputValue, setInputValue, handleSend, isLoading } = useChatSession();
    const messagesEndRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);
    
    return(
        <div className={styles.chatContainer}>
            <div className={styles.chatMessages}>
                {messages.map((msg, index) => (
                <ChatMessage
                    key={`${chatId}-${index}`}
                    sender={msg.sender}
                    message={msg.message}
                />
                ))}
                {isLoading && (
                    <div className={styles.loadingMessage}>
                        <div className={styles.loadingDots}>
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                        <span>OceanSense AI is thinking...</span>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>
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