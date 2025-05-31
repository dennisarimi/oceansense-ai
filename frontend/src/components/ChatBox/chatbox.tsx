import styles from './styles.module.css'
import {useRef, useEffect} from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPaperPlane } from '@fortawesome/free-solid-svg-icons';

export default function ChatBox({inputValue, setInputValue, onSend}) {
    const textareaRef = useRef<HTMLTextAreaElement | null>(null);

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
        }
    }, [inputValue]);

    return (
        <div className={styles.chatBox}>
            <textarea 
                className={styles.textbox} 
                placeholder="Ask anything"
                value={inputValue}
                ref={textareaRef}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                    if(e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        onSend();
                    }
                }}
            />
            <div className={styles.chatBottom}>
                <button className={styles.sendButton} onClick={onSend}>
                    <FontAwesomeIcon icon={faPaperPlane}/>
                </button>
            </div>
        </div>
    );
}