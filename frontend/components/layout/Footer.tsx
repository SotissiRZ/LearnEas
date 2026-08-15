import Link from "next/link";
import { GraduationCap, Facebook, Instagram, Linkedin, Twitter } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-gray-100 bg-gray-50">
      <div className="container-app grid grid-cols-2 gap-8 py-12 md:grid-cols-5">
        <div className="col-span-2">
          <Link href="/" className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white">
              <GraduationCap size={20} />
            </div>
            <span className="text-lg font-extrabold">Learn<span className="text-brand-600">Eas</span></span>
          </Link>
          <p className="mt-3 max-w-sm text-sm text-gray-500">
            Apprenez à votre rythme grâce à des cours complets (playlists vidéo) et des ressources
            PDF conçus par des instructeurs experts.
          </p>
          <div className="mt-4 flex gap-3 text-gray-400">
            <Facebook size={18} /> <Instagram size={18} /> <Linkedin size={18} /> <Twitter size={18} />
          </div>
        </div>

        <div>
          <h4 className="mb-3 text-sm font-semibold text-gray-900">Découvrir</h4>
          <ul className="space-y-2 text-sm text-gray-500">
            <li><Link href="/courses">Tous les cours</Link></li>
            <li><Link href="/pdfs">Tous les PDF</Link></li>
            <li><Link href="/instructors">Instructeurs</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="mb-3 text-sm font-semibold text-gray-900">Compte</h4>
          <ul className="space-y-2 text-sm text-gray-500">
            <li><Link href="/dashboard/student">Mon espace</Link></li>
            <li><Link href="/dashboard/instructor">Devenir instructeur</Link></li>
            <li><Link href="/faq">FAQ</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="mb-3 text-sm font-semibold text-gray-900">Support</h4>
          <ul className="space-y-2 text-sm text-gray-500">
            <li><Link href="/contact">Contactez-nous</Link></li>
            <li><Link href="/faq">Centre d'aide</Link></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-gray-100 py-4 text-center text-xs text-gray-400">
        © {new Date().getFullYear()} LearnEas. Tous droits réservés.
      </div>
    </footer>
  );
}
