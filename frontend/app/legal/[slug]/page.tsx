"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

type Settings = {
  site_name: string; support_email: string; legal_company_name: string; legal_address: string;
  legal_country: string; legal_registration_number: string; legal_tax_number: string;
  privacy_email: string; terms_updated_at: string | null; privacy_updated_at: string | null;
  refund_policy_days: number;
};

const TITLES: Record<string,string> = {
  terms: "Conditions d'utilisation", privacy: "Politique de confidentialité", notices: "Mentions légales",
  cookies: "Politique relative aux cookies", refunds: "Paiements et remboursements",
};

export default function LegalPage() {
  const { slug } = useParams<{ slug: string }>();
  const [settings, setSettings] = useState<Settings | null>(null);
  useEffect(() => { api.get<Settings>("/auth/platform-settings/").then(setSettings).catch(() => setSettings(null)); }, []);
  const title = TITLES[slug] || "Informations légales";
  return (
    <div className="container-app max-w-4xl py-12">
      <div className="mb-8"><p className="text-sm font-semibold text-brand-700">Légal</p><h1 className="mt-1 text-3xl font-extrabold">{title}</h1>{slug === "terms" && settings?.terms_updated_at && <p className="mt-2 text-xs text-gray-400">Dernière mise à jour : {new Date(settings.terms_updated_at).toLocaleDateString("fr-FR")}</p>}{slug === "privacy" && settings?.privacy_updated_at && <p className="mt-2 text-xs text-gray-400">Dernière mise à jour : {new Date(settings.privacy_updated_at).toLocaleDateString("fr-FR")}</p>}</div>
      <article className="card space-y-7 p-6 text-sm leading-7 text-gray-700 sm:p-8">
        {slug === "terms" && <Terms s={settings} />}
        {slug === "privacy" && <Privacy s={settings} />}
        {slug === "notices" && <Notices s={settings} />}
        {slug === "cookies" && <Cookies />}
        {slug === "refunds" && <Refunds s={settings} />}
        {!TITLES[slug] && <p>Cette page juridique n'existe pas.</p>}
      </article>
      <p className="mt-5 text-xs text-gray-400">Ces pages utilisent les informations administratives configurées dans le back-office. Elles doivent être adaptées aux obligations légales applicables à l'entité qui exploite la plateforme.</p>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) { return <section><h2 className="mb-2 text-lg font-bold text-ink">{title}</h2>{children}</section>; }
function Terms({ s }: { s: Settings | null }) { return <><Section title="Objet"><p>Les présentes conditions encadrent l'accès à {s?.site_name || "LearnEas"}, l'achat et l'utilisation des cours, PDF, formations interactives et certificats proposés sur la plateforme.</p></Section><Section title="Compte utilisateur"><p>L'utilisateur est responsable de ses identifiants, de l'exactitude des informations fournies et de l'usage réalisé depuis son compte. Les contenus acquis sont destinés à un usage personnel sauf autorisation contraire.</p></Section><Section title="Contenus et propriété intellectuelle"><p>Les vidéos, documents, supports pédagogiques, marques et éléments graphiques restent protégés par les droits de leurs titulaires. Leur redistribution non autorisée est interdite.</p></Section><Section title="Certificats"><p>Un certificat atteste du respect des critères configurés pour le contenu concerné. Il ne constitue pas, à lui seul, un diplôme d'État ni une qualification réglementée.</p></Section><Section title="Contact"><p>Support : <a className="text-brand-700" href={`mailto:${s?.support_email || "support@learneas.com"}`}>{s?.support_email || "support@learneas.com"}</a>.</p></Section></>; }
function Privacy({ s }: { s: Settings | null }) { return <><Section title="Données traitées"><p>La plateforme traite notamment les données de compte, d'achat, de progression pédagogique, de présence aux séances live, de messagerie et de certification nécessaires au fonctionnement du service.</p></Section><Section title="Finalités"><p>Ces données servent à fournir les contenus achetés, sécuriser les accès, suivre la progression, rémunérer les instructeurs, délivrer et vérifier les certificats, assister les utilisateurs et administrer la plateforme.</p></Section><Section title="Durée et sécurité"><p>Les données sont conservées pendant les durées nécessaires aux finalités et obligations applicables. Des mesures techniques et organisationnelles doivent être maintenues par l'exploitant.</p></Section><Section title="Vos demandes"><p>Pour les questions relatives à la confidentialité : <a className="text-brand-700" href={`mailto:${s?.privacy_email || "privacy@learneas.com"}`}>{s?.privacy_email || "privacy@learneas.com"}</a>.</p></Section></>; }
function Notices({ s }: { s: Settings | null }) { return <><Section title="Éditeur"><p><strong>{s?.legal_company_name || "LearnEas"}</strong><br />{s?.legal_address || "Adresse à renseigner dans les paramètres administrateur"}<br />{s?.legal_country || "Pays à renseigner"}</p></Section><Section title="Immatriculation"><p>Numéro d'immatriculation : {s?.legal_registration_number || "Non renseigné"}<br />Identifiant fiscal : {s?.legal_tax_number || "Non renseigné"}</p></Section><Section title="Contact"><p>{s?.support_email || "support@learneas.com"}</p></Section></>; }
function Cookies() { return <><Section title="Cookies nécessaires"><p>La plateforme peut utiliser des mécanismes de stockage nécessaires à l'authentification, à la sécurité, au panier et aux préférences utilisateur.</p></Section><Section title="Mesure d'audience et services tiers"><p>Tout outil non strictement nécessaire ajouté ultérieurement doit être documenté et, lorsque la réglementation l'exige, soumis au consentement de l'utilisateur.</p></Section><Section title="Gestion"><p>Vous pouvez supprimer les données de site depuis les paramètres de votre navigateur. Cela peut vous déconnecter ou réinitialiser certaines préférences.</p></Section></>; }
function Refunds({ s }: { s: Settings | null }) { return <><Section title="Paiements"><p>Les prix et moyens de paiement applicables sont affichés avant validation. La plateforme doit confirmer un paiement avant d'attribuer définitivement l'accès payant.</p></Section><Section title="Remboursements"><p>La politique par défaut est configurée sur {s?.refund_policy_days ?? 14} jour(s), sous réserve des conditions particulières, de la consommation du contenu et du droit applicable.</p></Section><Section title="Formations live"><p>Les règles d'annulation ou de report doivent tenir compte de la date de la séance et des prestations déjà réalisées.</p></Section><Section title="Assistance"><p>Pour une demande relative à une commande, contactez <Link className="text-brand-700" href="/contact">l'assistance</Link>.</p></Section></>; }
