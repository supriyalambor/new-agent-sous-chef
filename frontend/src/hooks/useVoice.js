import { useState, useEffect, useRef } from "react";

export function useVoice(onResult) {
  const [listening, setListening] = useState(false);
  const [supported, setSupported] = useState(false);
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setSupported(true);
      const recognition = new SpeechRecognition();
      recognition.lang = "en-IN";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        onResult(transcript);
        setListening(false);
      };

      recognition.onend = () => setListening(false);
      recognition.onerror = () => setListening(false);
      recognitionRef.current = recognition;
    }
  }, []);

  function startListening() {
    if (!recognitionRef.current || listening) return;
    recognitionRef.current.start();
    setListening(true);
  }

  function stopListening() {
    if (!recognitionRef.current || !listening) return;
    recognitionRef.current.stop();
    setListening(false);
  }

  return { listening, supported, startListening, stopListening };
}
