import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

// Remove the fragment before network calls, rendering, or subsequent navigation.
const fragment = new URLSearchParams(location.hash.slice(1));
let bootstrap: string | null = fragment.get("bootstrap");
history.replaceState(null, "", location.pathname);

function Foundation() {
  const [status, setStatus] = useState("Connecting to your local runtime…");
  useEffect(() => {
    const value = bootstrap;
    bootstrap = null;
    const request = value
      ? fetch("/api/v1/auth/bootstrap", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token: value }) })
      : fetch("/api/v1/auth/session");
    void request.then(result => {
      setStatus(result.ok ? "Local session connected." : "Open this page through the LILA launcher to reconnect.");
    }).catch(() => setStatus("Local runtime unavailable. Check the launcher."));
  }, []);
  return <main><h1>LILA Claw</h1><p role="status">{status}</p><p>Foundation preview. Task execution is not available yet.</p></main>;
}
createRoot(document.getElementById("root")!).render(<Foundation />);
