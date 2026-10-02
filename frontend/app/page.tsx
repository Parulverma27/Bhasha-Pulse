"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [status, setStatus] = useState<string>("Checking backend...");

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then((d) => setStatus(`Backend is up (v${d.version}, ${d.outlets_configured} outlets configured)`))
      .catch(() => setStatus("Backend not reachable. Start it with: uvicorn backend.app.main:app --reload"));
  }, []);

  return (
    <main>
      <h1>News Intelligence India</h1>
      <p>Setup complete. The dashboard arrives in Milestone 8.</p>
      <p>{status}</p>
    </main>
  );
}
