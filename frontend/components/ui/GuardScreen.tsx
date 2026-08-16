import { Loader2 } from "lucide-react";

/** Affiché tant que useAuthGuard n'a pas confirmé l'accès — jamais le vrai contenu. */
export default function GuardScreen() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Loader2 className="animate-spin text-brand-600" size={32} />
    </div>
  );
}
