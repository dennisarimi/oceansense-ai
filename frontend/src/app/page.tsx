"use client"

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';
import Image from 'next/image';
import styles from './styles.module.css';
import ChatBox from '@/components/ChatBox/chatbox';

export default function LandingPage() {
  const [inputValue, setInputValue] = useState('');
  const router = useRouter();

  const handleStartChat = () => {
    if (inputValue.trim()) {
      // Send the initial message and immediately navigate
      const message = inputValue.trim();
      const chatId = uuidv4();
      
      // Store the message in sessionStorage before navigating
      const userMsg = { sender: "user" as const, message };
      sessionStorage.setItem("chatMessages", JSON.stringify([userMsg]));
      
      // Navigate immediately to the chat page
      router.push(`/chat/${chatId}`);
    }
  };

  return (
    <main className={styles.main}>
      <div className={styles.welcome_message}>
        <div className={styles.logo}>
          <Image src="/logo.png" alt="Logo" width={250} height={250}/>
        </div>
        <div className={styles.heading}>
          <h1>Welcome to OceanSense AI</h1>
        </div>
      </div>
      <ChatBox
        inputValue={inputValue}
        setInputValue={setInputValue}
        onSend={handleStartChat}
      />
    </main>
  );
}
