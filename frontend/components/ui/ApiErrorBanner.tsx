import { AlertTriangle, WifiOff } from "lucide-react";

/** Affiché sur les pages catalogue lorsqu'une source API n'a pas pu être chargée.
 * Un HTTP 429 signifie que le serveur répond mais limite le trafic : ce cas ne doit
 * pas être présenté comme une panne réseau. */
export default function ApiErrorBanner({ message }: { message?: string }) {
  const throttled = message?.startsWith("Trop de requêtes") ?? false;
  const Icon = throttled ? AlertTriangle : WifiOff;

  return (
    <div className="mb-6 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <Icon size={18} className="mt-0.5 shrink-0" />
      <div>
        <p className="font-semibold">
          {throttled ? "Chargement temporairement limité." : "Impossible de charger les données."}
        </p>
        <p className="mt-1 text-red-600">
          {throttled
            ? "Le serveur est accessible, mais il limite momentanément le nombre de requêtes. Réessayez dans quelques instants."
            : "Le contenu ci-dessous peut être incomplet. Vérifiez que le backend est démarré et accessible, puis rechargez la page."}
          {message && <span className="mt-1 block font-mono text-xs text-red-500">{message}</span>}
        </p>
      </div>
    </div>
  );
}
