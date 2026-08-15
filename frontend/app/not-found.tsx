import Link from "next/link";
import { GraduationCap } from "lucide-react";

export default function NotFound() {
  return (
    <div className="container-app flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <GraduationCap size={48} className="text-gray-300" />
      <h1 className="text-3xl font-extrabold">Page introuvable</h1>
      <p className="text-gray-500">Le contenu que vous cherchez n'existe pas ou a été déplacé.</p>
      <Link href="/" className="btn-primary">Retour à l'accueil</Link>
    </div>
  );
}
