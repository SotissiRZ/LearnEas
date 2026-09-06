import Link from "next/link";
import { Facebook, Instagram, Linkedin, Twitter } from "lucide-react";
import BrandLogo from "@/components/layout/BrandLogo";

export default function Footer() {
  return (
    <footer className="border-t border-white/10 bg-navy-950 text-white">
      <div className="container-app grid grid-cols-1 gap-8 py-10 sm:grid-cols-2 lg:grid-cols-6 lg:py-12">
        <div className="sm:col-span-2">
          <BrandLogo />
          <p className="mt-4 max-w-sm text-sm leading-6 text-white/60">
            Formation, mentorat, projets, certificats et opportunités professionnelles réunis dans une plateforme pensée pour l'Afrique francophone.
          </p>
          <div className="mt-5 flex gap-3 text-white/40"><Facebook size={18} /><Instagram size={18} /><Linkedin size={18} /><Twitter size={18} /></div>
        </div>
        <FooterColumn title="Apprendre" items={[["/courses","Formations"],["/formations","Cohortes live"],["/mentorship","Mentorat"],["/pdfs","PDF & Guides"],["/instructors","Instructeurs"]]} />
        <FooterColumn title="Carrière" items={[["/opportunities","Opportunités"],["/dashboard/student/projects","Mes projets"],["/dashboard/student/portfolio","Portfolio"],["/certificates/verify","Vérifier un certificat"]]} />
        <FooterColumn title="Support" items={[["/pricing","Tarifs"],["/about","À propos"],["/contact","Contact"],["/faq","Centre d'aide"],["/support","Support & sécurité"],["/login","Connexion"]]} />
        <FooterColumn title="Légal" items={[["/legal/terms","Conditions d'utilisation"],["/legal/privacy","Confidentialité"],["/legal/notices","Mentions légales"],["/legal/cookies","Cookies"],["/legal/refunds","Paiements & remboursements"]]} />
      </div>
      <div className="border-t border-white/10 py-4 text-center text-xs text-white/40">© {new Date().getFullYear()} KalanPro. Tous droits réservés.</div>
    </footer>
  );
}

function FooterColumn({ title, items }: { title: string; items: [string, string][] }) {
  return <div><h4 className="mb-3 text-sm font-bold text-white">{title}</h4><ul className="space-y-2 text-sm text-white/60">{items.map(([href,label]) => <li key={href}><Link className="transition hover:text-brand-400" href={href}>{label}</Link></li>)}</ul></div>;
}
