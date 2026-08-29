import Link from "next/link";
import { GraduationCap, Facebook, Instagram, Linkedin, Twitter } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-gray-100 bg-gray-50">
      <div className="container-app grid grid-cols-2 gap-8 py-12 md:grid-cols-6">
        <div className="col-span-2">
          <Link href="/" className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white"><GraduationCap size={20} /></div>
            <span className="text-lg font-extrabold">Learn<span className="text-brand-600">Eas</span></span>
          </Link>
          <p className="mt-3 max-w-sm text-sm text-gray-500">Apprenez à votre rythme grâce à des cours complets, des formations interactives et des ressources PDF conçus par des instructeurs experts.</p>
          <div className="mt-4 flex gap-3 text-gray-400"><Facebook size={18} /><Instagram size={18} /><Linkedin size={18} /><Twitter size={18} /></div>
        </div>
        <FooterColumn title="Découvrir" items={[["/courses","Tous les cours"],["/formations","Formations interactives"],["/pdfs","Tous les PDF"],["/instructors","Instructeurs"]]} />
        <FooterColumn title="Compte" items={[["/dashboard/student","Mon espace"],["/dashboard/instructor","Devenir instructeur"],["/dashboard/student/certificates","Mes certificats"],["/faq","FAQ"]]} />
        <FooterColumn title="Support" items={[["/contact","Contactez-nous"],["/faq","Centre d'aide"],["/certificates/verify","Vérifier un certificat"]]} />
        <FooterColumn title="Légal" items={[["/legal/terms","Conditions d'utilisation"],["/legal/privacy","Confidentialité"],["/legal/notices","Mentions légales"],["/legal/cookies","Cookies"],["/legal/refunds","Paiements & remboursements"]]} />
      </div>
      <div className="border-t border-gray-100 py-4 text-center text-xs text-gray-400">© {new Date().getFullYear()} LearnEas. Tous droits réservés.</div>
    </footer>
  );
}

function FooterColumn({ title, items }: { title: string; items: [string, string][] }) {
  return <div><h4 className="mb-3 text-sm font-semibold text-gray-900">{title}</h4><ul className="space-y-2 text-sm text-gray-500">{items.map(([href,label]) => <li key={href}><Link className="hover:text-brand-700" href={href}>{label}</Link></li>)}</ul></div>;
}
