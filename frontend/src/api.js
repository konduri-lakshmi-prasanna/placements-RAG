/**
 * api.js — All backend API calls.
 * Base URL reads from env or defaults to localhost:8000.
 */

// const BASE_URL = import.meta.env.VITE_API_URL || "https://placements-rag-backend.onrender.com";
// const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function post(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

async function get(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export const api = {
  /** Send a query to the RAG system */
  query: (question, useAgent = false) =>
    post("/query", { question, use_agent: useAgent }),

  /** Get all 19 companies with eligibility data */
  companies: () => get("/companies"),

  /** System stats (chunk count, models used) */
  stats: () => get("/stats"),

  /** Run full 30-query evaluation */
  runEval: () => post("/eval", {}),

  /** Health check */
  health: () => get("/health"),
};