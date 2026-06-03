/**
 * VoiceSearch.jsx — Voice input for PlacementIQ (Groq Whisper API)
 *
 * Replaces the Web Speech API with Groq's Whisper large-v3 model.
 *
 * Advantages over Web Speech API:
 *   ✓ Works in ALL browsers (Chrome, Firefox, Safari, Edge)
 *   ✓ Works on HTTP localhost AND HTTPS
 *   ✓ Much higher accuracy for Telugu and Hindi
 *   ✓ No browser vendor limitations
 *   ✓ Groq free tier: 7,200 audio minutes/day (very generous)
 *
 * Props:
 *   onTranscript(text)  — called with the final transcript string
 *   apiKey              — your Groq API key (from https://console.groq.com)
 *   disabled            — boolean to disable the button
 *
 * Usage:
 *   <VoiceSearch
 *     apiKey={import.meta.env.VITE_GROQ_API_KEY}
 *     onTranscript={(text) => setSearchQuery(text)}
 *   />
 *
 * .env file:
 *   VITE_GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
 *
 * Install nothing — uses native MediaRecorder + fetch.
 */

import { useState, useRef, useEffect } from "react";
import { Mic, MicOff, Loader2 } from "lucide-react";

// ─── Language options ────────────────────────────────────────────────────────
// Groq Whisper uses ISO-639-1 language codes (2-letter), not BCP-47 like Web Speech API
const LANGUAGES = [
  { code: "en", label: "EN", full: "English" },
  { code: "te", label: "తె", full: "Telugu"  },
  { code: "hi", label: "हि", full: "Hindi"   },
];

// ─── Groq Whisper endpoint ────────────────────────────────────────────────────
const GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions";
const WHISPER_MODEL           = "whisper-large-v3";

// ─── Preferred MIME types (ordered by quality / browser support) ──────────────
const PREFERRED_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/mp4",
];

function getSupportedMimeType() {
  for (const mimeType of PREFERRED_MIME_TYPES) {
    if (MediaRecorder.isTypeSupported(mimeType)) return mimeType;
  }
  return ""; // browser default
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function VoiceSearch({ onTranscript, apiKey, disabled }) {
  const [recording,  setRecording]  = useState(false);
  const [loading,    setLoading]    = useState(false); // waiting for Groq response
  const [langIndex,  setLangIndex]  = useState(0);
  const [statusMsg,  setStatusMsg]  = useState("");
  const [supported,  setSupported]  = useState(true);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef   = useRef([]);
  const streamRef        = useRef(null);

  // Check browser support for MediaRecorder
  useEffect(() => {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setSupported(false);
    }
  }, []);

  const currentLang = LANGUAGES[langIndex];

  // ── Cycle language (only when not recording) ──────────────────────────────
  const cycleLang = (e) => {
    e.stopPropagation();
    if (!recording && !loading) {
      setLangIndex(i => (i + 1) % LANGUAGES.length);
      setStatusMsg("");
    }
  };

  // ── Start recording ───────────────────────────────────────────────────────
  const startRecording = async () => {
    if (!apiKey) {
      setStatusMsg("⚠ No Groq API key provided.");
      setTimeout(() => setStatusMsg(""), 4000);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType    = getSupportedMimeType();
      const options     = mimeType ? { mimeType } : {};
      const recorder    = new MediaRecorder(stream, options);
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = () => handleRecordingStop(mimeType || "audio/webm");

      recorder.start(250); // collect chunks every 250ms
      mediaRecorderRef.current = recorder;
      setRecording(true);
      setStatusMsg(`🎙 Recording in ${currentLang.full}...`);

    } catch (err) {
      if (err.name === "NotAllowedError") {
        setStatusMsg("Microphone permission denied.");
      } else {
        setStatusMsg(`Microphone error: ${err.message}`);
      }
      setTimeout(() => setStatusMsg(""), 4000);
    }
  };

  // ── Stop recording ────────────────────────────────────────────────────────
  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach(t => t.stop());
    setRecording(false);
    setStatusMsg("Processing...");
  };

  // ── Send audio to Groq Whisper ────────────────────────────────────────────
  const handleRecordingStop = async (mimeType) => {
    setLoading(true);

    try {
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });

      // Groq requires a filename with the correct extension
      const ext      = mimeType.includes("ogg") ? "ogg"
                     : mimeType.includes("mp4") ? "mp4"
                     : "webm";
      const fileName = `recording.${ext}`;

      const formData = new FormData();
      formData.append("file",               audioBlob, fileName);
      formData.append("model",              WHISPER_MODEL);
      formData.append("language",           currentLang.code);
      formData.append("response_format",    "json");
      // Optional: improve accuracy for placement/campus context
      formData.append("prompt",
        "PlacementIQ student placement query. " +
        "Companies, colleges, CGPA, salary, job roles."
      );

      const response = await fetch(GROQ_TRANSCRIPTION_URL, {
        method:  "POST",
        headers: { Authorization: `Bearer ${apiKey}` },
        body:    formData,
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        throw new Error(errBody?.error?.message || `HTTP ${response.status}`);
      }

      const data       = await response.json();
      const transcript = data.text?.trim();

      if (transcript) {
        setStatusMsg(`✓ "${transcript}"`);
        onTranscript(transcript);
        setTimeout(() => setStatusMsg(""), 4000);
      } else {
        setStatusMsg("No speech detected. Try again.");
        setTimeout(() => setStatusMsg(""), 3000);
      }

    } catch (err) {
      setStatusMsg(`Error: ${err.message}`);
      setTimeout(() => setStatusMsg(""), 5000);
    } finally {
      setLoading(false);
      audioChunksRef.current = [];
    }
  };

  // ── Toggle button handler ─────────────────────────────────────────────────
  const toggle = () => {
    if (loading) return; // don't interrupt while waiting for API
    if (recording) stopRecording();
    else startRecording();
  };

  // ── Unsupported browser fallback ──────────────────────────────────────────
  if (!supported) {
    return (
      <div
        className="flex items-center gap-1 text-xs text-zinc-500"
        title="Microphone not available in this browser"
      >
        <MicOff size={14} />
        <span>Mic unavailable</span>
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="flex items-center gap-2">

      {/* Status message */}
      {statusMsg && (
        <span className="text-xs text-zinc-400 max-w-[200px] truncate" title={statusMsg}>
          {statusMsg}
        </span>
      )}

      {/* Language switcher — disabled while recording/loading */}
      <button
        onClick={cycleLang}
        title={`Switch language (current: ${currentLang.full})`}
        disabled={recording || loading}
        className="text-xs px-2 py-1 rounded-md bg-zinc-700/60 border border-zinc-600
          text-zinc-300 hover:text-white hover:border-violet-500/50 transition-all
          font-mono select-none disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {currentLang.label}
      </button>

      {/* Mic / Stop / Loading button */}
      <button
        onClick={toggle}
        disabled={disabled || loading}
        title={
          loading    ? "Transcribing..."
          : recording ? "Stop & transcribe"
          : `Speak in ${currentLang.full}`
        }
        className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all
          ${recording
            ? "bg-red-500 hover:bg-red-400 animate-pulse"
            : loading
              ? "bg-violet-700 cursor-wait"
              : "bg-zinc-700 hover:bg-violet-600 border border-zinc-600 hover:border-violet-500"
          }
          disabled:opacity-30`}
      >
        {loading
          ? <Loader2 size={15} className="text-white animate-spin" />
          : recording
            ? <MicOff size={15} className="text-white" />
            : <Mic    size={15} className="text-zinc-300" />
        }
      </button>
    </div>
  );
}