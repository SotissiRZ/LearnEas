"use client";

import { useEffect } from "react";

export default function ErrorBoundary({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    const body = JSON.stringify({
      name: error?.name || "Error",
      digest: error?.digest || "",
      pathname: window.location.pathname,
    });
    fetch("/api/telemetry/client-error/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      credentials: "same-origin",
      keepalive: true,
    }).catch(() => undefined);
  }, [error]);

  return (
    <main className="container-app py-20">
      <div className="mx-auto max-w-xl rounded-2xl border border-red-100 bg-white p-8 text-center shadow-sm">
        <h1 className="text-xl font-bold text-navy-950">Cette page a rencontré un problème</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Réessayez. Si le problème persiste, rechargez la page avant de recommencer l’action.
        </p>
        {error?.digest ? <p className="mt-3 text-xs text-slate-400">Référence : {error.digest}</p> : null}
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={reset} className="btn-primary">Réessayer</button>
          <button type="button" onClick={() => window.location.reload()} className="btn-outline">Recharger</button>
        </div>
      </div>
    </main>
  );
}
