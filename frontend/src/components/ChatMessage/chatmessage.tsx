import styles from './styles.module.css'

type ChatMessageProps = {
    message: string;
    sender?: "user" | "bot";
};

export default function ChatMessage({ message, sender = "user" }: ChatMessageProps) {

    return (
        <div className={sender === "user" ? styles.userMessage : styles.botMessage}>
            {message.split('\n').map((line, i) => (
                <span key={i}>
                    {line}
                    <br />
                </span>
            ))}
        </div>
    );
}