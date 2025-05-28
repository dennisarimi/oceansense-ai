import styles from "./styles.module.css"
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPaperPlane } from '@fortawesome/free-solid-svg-icons';

export default function ChatBox() {
    return (
        <div className={styles.chatbox}>
            <input className={styles.input} placeholder="Ask anything" />
            <button className={styles.sendButton}>
                <FontAwesomeIcon icon={faPaperPlane}/>
            </button>
        </div>
    );
}