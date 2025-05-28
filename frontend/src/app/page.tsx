import Image from "next/image";
import styles from './styles.module.css';
import ChatBox from "@/components/ChatBox/chatbox";

export default function Home() {
  return (
    <main className={styles.main}>
      <div className={styles.welcome_message}>
        <div className={styles.logo}>
          <Image src="/logo.png" alt="Logo" width={250} height={250}/>
        </div>
        <div className={styles.heading}>
          <h1>Welcome to OceanSense AI</h1>
        </div>
        <div className={styles.chatbox}>
          <ChatBox/>
        </div>
      </div>
    </main>
  );
}
