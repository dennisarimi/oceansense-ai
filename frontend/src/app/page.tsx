"use client"

import {useState} from 'react';
import Image from 'next/image';
import styles from './styles.module.css';
import ChatBox from '@/components/ChatBox/chatbox';
import ChatMessage from '@/components/ChatMessage/chatmessage';

export default function LandingPage() {
  const [inputValue, setInputValue] = useState('');
  const [queries, setQueries] = useState<string[]>([]);

  const handleSend = () => {
    if (inputValue.trim()) {
      setQueries((prev) => [...prev, inputValue]);
      setInputValue('');
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
      {queries.length > 0 && (
        <div className={styles.chatQueries}>
          {queries.map((query, index) => (
            <ChatMessage
              sender="user"
              message={query}
              key={index}
            />
          ))}
        </div>
      )}
      <ChatBox
        inputValue={inputValue}
        setInputValue={setInputValue}
        onSend={handleSend}
      />
    </main>
  );
}
