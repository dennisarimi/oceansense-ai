"use client"

import { useRouter } from 'next/navigation';
import {useState} from 'react';
import { v4 as uuidv4 } from 'uuid';
import Image from 'next/image';
import styles from './styles.module.css';
import ChatBox from '@/components/ChatBox/chatbox';
import useChatSession from '@/hooks/useChatSession';

export default function LandingPage() {
  const { inputValue, setInputValue, handleSend } = useChatSession();
  const router = useRouter();

  const handleStartChat = () => {
    if (inputValue.trim()) {
      handleSend(); // Stores initial message
      
      // route to specific chat
      const chatId = uuidv4(); // Generates a unique chat ID
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
