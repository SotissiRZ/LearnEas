import { WifiOff } from "lucide-react";

/** Affiché sur les pages catalogue quand l'API est injoignable — à ne pas confondre
 * avec "aucun résultat" (cas normal, pas une erreur). */
export default function ApiErrorBanner({ message }: { message?: string }) {
  return (
    <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <WifiOff size={18} className="mt-0.5 shrink-0" />
      <div>
        <p className="font-semibold">Impossible de contacter le serveur.</p>
        <p className="mt-1 text-red-600">
          Le contenu ci-dessous peut être incomplet. Vérifiez que le backend est démarré et
          accessible, puis rechargez la page.
          {message && <span className="mt-1 block font-mono text-xs text-red-500">{message}</span>}
        </p>
      </div>
    </div>
  );
}
