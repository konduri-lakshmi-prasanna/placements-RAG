/**
 * VoiceSearch.jsx — Voice input for PlacementIQ
 *
 * Supports:
 *   - English (en-IN)
 *   - Telugu (te-IN)
 *   - Hindi (hi-IN)
 *
 * Uses the Web Speech API (built into Chrome/Edge — no extra package needed).
 * Works on localhost and HTTPS deployed URLs.
 * Does NOT work on Firefox (no Web Speech API support).
 */

import { useState, useRef, useEffect } from "react";
import { Mic, MicOff, Loader2 } from "lucide-react";

const LANGUAGES = [
  { code: "en-IN", label: "EN", full: "English" },
  { code: "te-IN", label: "తె",  full: "Telugu"  },
  { code: "hi-IN", label: "हि",  full: "Hindi"   },
];

export default function VoiceSearch({ onTranscript, disabled }) {
  const [listening,  setListening]  = useState(false);
  const [langIndex,  setLangIndex]  = useState(0);   // 0=EN, 1=TE, 2=HI
  const [statusMsg,  setStatusMsg]  = useState("");
  const [supported,  setSupported]  = useState(true);
  const recognitionRef = useRef(null);

  // Check browser support on mount
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSupported(false);
    }
  }, []);

  const currentLang = LANGUAGES[langIndex];

  const cycleLang = (e) => {
    e.stopPropagation();
    if (!listening) {
      setLangIndex(i => (i + 1) % LANGUAGES.length);
    }
  };

  const startListening = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setStatusMsg("Voice not supported in this browser. Use Chrome.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang            = currentLang.code;
    recognition.interimResults  = true;
    recognition.maxAlternatives = 1;
    recognition.continuous      = false;

    recognition.onstart = () => {
      setListening(true);
      setStatusMsg(`Listening in ${currentLang.full}...`);
    };

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(r => r[0].transcript)
        .join("");
      const isFinal = event.results[event.results.length - 1].isFinal;

      if (isFinal) {
        setStatusMsg(`✓ "${transcript}"`);
        onTranscript(transcript);
        setListening(false);
      } else {
        setStatusMsg(`Hearing: "${transcript}"`);
      }
    };

    recognition.onerror = (event) => {
      setListening(false);
      if (event.error === "no-speech") {
        setStatusMsg("No speech detected. Try again.");
      } else if (event.error === "not-allowed") {
        setStatusMsg("Microphone permission denied.");
      } else {
        setStatusMsg(`Error: ${event.error}`);
      }
      setTimeout(() => setStatusMsg(""), 3000);
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const stopListening = () => {
    recognitionRef.current?.stop();
    setListening(false);
    setStatusMsg("");
  };

  const toggle = () => {
    if (listening) stopListening();
    else startListening();
  };

  // Not supported
  if (!supported) {
    return (
      <div className="flex items-center gap-1 text-xs text-zinc-600" title="Use Chrome for voice">
        <MicOff size={14} />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">

      {/* Status message */}
      {statusMsg && (
        <span className="text-xs text-zinc-400 max-w-[180px] truncate">
          {statusMsg}
        </span>
      )}

      {/* Language switcher */}
      <button
        onClick={cycleLang}
        title={`Switch language (current: ${currentLang.full})`}
        className="text-xs px-2 py-1 rounded-md bg-zinc-700/60 border border-zinc-600
          text-zinc-300 hover:text-white hover:border-violet-500/50 transition-all
          font-mono select-none"
      >
        {currentLang.label}
      </button>

      {/* Mic button */}
      <button
        onClick={toggle}
        disabled={disabled}
        title={listening ? "Stop listening" : `Speak in ${currentLang.full}`}
        className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all
          ${listening
            ? "bg-red-500 hover:bg-red-400 animate-pulse"
            : "bg-zinc-700 hover:bg-violet-600 border border-zinc-600 hover:border-violet-500"
          }
          disabled:opacity-30`}
      >
        {listening
          ? <MicOff size={15} className="text-white" />
          : <Mic    size={15} className="text-zinc-300" />
        }
      </button>
    </div>
  );
}