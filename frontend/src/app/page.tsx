"use client"

import {useState} from 'react';
import Image from 'next/image';
import styles from './styles.module.css';
import ChatBox from '@/components/ChatBox/chatbox';

export default function Home() {
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
      <div className={styles.chatQueries}>
        {queries.map((query, index) => (
          <div key={index} className={styles.query}>
            {query}
          </div>
        ))}
      </div>
      <div className={styles.chatbox}>
        <ChatBox
          inputValue={inputValue}
          setInputValue={setInputValue}
          onSend={handleSend}
        />
      </div>
    </main>
  );
}
