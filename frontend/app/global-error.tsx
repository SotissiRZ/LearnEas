"use client";

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="fr">
      <body>
        <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24, fontFamily: "system-ui, sans-serif" }}>
          <div style={{ maxWidth: 520, textAlign: "center" }}>
            <h1>Impossible d’afficher KalanPro</h1>
            <p>Une erreur inattendue est survenue. Vous pouvez réessayer sans perdre votre compte.</p>
            <button type="button" onClick={reset} style={{ padding: "10px 18px", cursor: "pointer" }}>Réessayer</button>
          </div>
        </main>
      </body>
    </html>
  );
}
