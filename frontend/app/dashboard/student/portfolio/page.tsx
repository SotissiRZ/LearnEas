"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Check, Copy, ExternalLink, Eye, EyeOff, Globe2, Loader2, Mail, Plus, ShieldCheck,
  Star, Trash2, UploadCloud, Pencil, X, Award, Video,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Certificate, Paginated, PortfolioItem, PortfolioProfile } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";
import DashboardNav from "@/components/dashboard/DashboardNav";

type ItemFormState = {
  title: string;
  description: string;
  role: string;
  problem: string;
  objective: string;
  outcome: string;
  stack: string;
  video_url: string;
  started_at: string;
  completed_at: string;
  external_url: string;
  repository_url: string;
  skills: string;
};

const emptyItem: ItemFormState = {
  title: "", description: "", role: "", problem: "", objective: "", outcome: "", stack: "",
  video_url: "", started_at: "", completed_at: "", external_url: "", repository_url: "", skills: "",
};

export default function StudentPortfolioPage() {
  const { ready } = useAuthGuard();
  const [profile, setProfile] = useState<PortfolioProfile | null>(null);
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [selectedCertificateIds, setSelectedCertificateIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [copied, setCopied] = useState(false);
  const [skillsText, setSkillsText] = useState("");
  const [editingItem, setEditingItem] = useState<PortfolioItem | null>(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [p, i, certData] = await Promise.all([
        api.get<PortfolioProfile>("/projects/portfolio-profile/me/"),
        api.get<PortfolioItem[]>("/projects/portfolio-items/"),
        api.get<Paginated<Certificate> | Certificate[]>("/enrollments/certificates/"),
      ]);
      const certs = Array.isArray(certData) ? certData : certData.results;
      setProfile(p);
      setSkillsText((p.skills || []).join(", "));
      setItems(i);
      setCertificates(certs);
      setSelectedCertificateIds((p.certificates || []).map(c => c.id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Impossible de charger votre portfolio.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { if (ready) void load(); }, [ready]);
  const publicCount = useMemo(() => items.filter(i => i.is_public).length, [items]);
  const activeCertificates = useMemo(() => certificates.filter(c => c.effective_status === "active"), [certificates]);

  async function saveProfile() {
    if (!profile) return;
    setSaving(true); setError(""); setMessage("");
    try {
      const p = await api.patch<PortfolioProfile>("/projects/portfolio-profile/me/", {
        slug: profile.slug,
        is_public: profile.is_public,
        title: profile.title,
        about: profile.about,
        skills: splitList(skillsText),
        website_url: profile.website_url,
        linkedin_url: profile.linkedin_url,
        github_url: profile.github_url,
        open_to_work: profile.open_to_work,
        show_country: profile.show_country,
        show_project_scores: profile.show_project_scores,
        show_certificates: profile.show_certificates,
        public_contact_email: profile.public_contact_email,
        show_contact_email: profile.show_contact_email,
        selected_certificate_ids: selectedCertificateIds,
      });
      setProfile(p);
      setSkillsText((p.skills || []).join(", "));
      setSelectedCertificateIds((p.certificates || []).map(c => c.id));
      setMessage("Portfolio enregistré.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Enregistrement impossible.");
    } finally {
      setSaving(false);
    }
  }

  async function patchItem(item: PortfolioItem, body: Record<string, unknown>) {
    setError("");
    try { await api.patch(`/projects/portfolio-items/${item.id}/`, body); await load(); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Modification impossible."); }
  }

  async function remove(item: PortfolioItem) {
    if (!confirm(`Retirer « ${item.title} » du portfolio ? Le projet validé reste conservé dans KalanPro.`)) return;
    try { await api.del(`/projects/portfolio-items/${item.id}/`); await load(); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Suppression impossible."); }
  }

  async function copy() {
    if (!profile) return;
    const url = profile.public_url.startsWith("http") ? profile.public_url : `${window.location.origin}${profile.public_url}`;
    await navigator.clipboard.writeText(url);
    setCopied(true); setTimeout(() => setCopied(false), 1500);
  }

  function toggleCertificate(id: number) {
    setSelectedCertificateIds(current => current.includes(id) ? current.filter(v => v !== id) : [...current, id]);
  }

  if (!ready) return <GuardScreen />;
  return <div className="container-app py-10">
    <DashboardNav role="student" />
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-2xl font-bold">Mon portfolio professionnel</h1><p className="mt-1 text-sm text-gray-500">Présentez des preuves concrètes : rôle, problème, résultat, stack, démo et certificats vérifiables.</p></div>
      <div className="flex gap-2">{profile?.is_public && <Link href={`/portfolio/${profile.slug}`} target="_blank" className="btn-outline !py-2 !text-xs"><ExternalLink size={14}/> Voir le portfolio</Link>}<button onClick={() => setShowAdd(v => !v)} className="btn-primary !py-2 !text-xs"><Plus size={14}/> Projet externe</button></div>
    </div>
    {error && <div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}
    {message && <div className="mb-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}

    {loading || !profile ? <div className="card p-10 text-center text-gray-400"><Loader2 className="mx-auto mb-2 animate-spin"/>Chargement...</div> : <>
      <section className="card mb-6 p-5 sm:p-6">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-bold">Page publique</h2><p className="mt-1 text-xs text-gray-500">Les coordonnées ne sont affichées que si vous les activez explicitement.</p></div><label className="flex items-center gap-2 text-sm font-medium"><input type="checkbox" checked={profile.is_public} onChange={e => setProfile({...profile, is_public:e.target.checked})}/> Portfolio public</label></div>
        <div className="grid gap-4 md:grid-cols-2"><Field label="Adresse publique"><div className="flex"><span className="rounded-l-lg border border-r-0 border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-400">/portfolio/</span><input value={profile.slug} onChange={e => setProfile({...profile,slug:e.target.value.toLowerCase().replace(/[^a-z0-9-]/g,"-")})} className="input-admin min-w-0 flex-1 rounded-l-none"/></div></Field><Field label="Titre professionnel"><input value={profile.title} onChange={e => setProfile({...profile,title:e.target.value})} className="input-admin w-full" placeholder="Data Analyst · Excel & Power BI"/></Field></div>
        <Field label="À propos"><textarea rows={5} value={profile.about} onChange={e => setProfile({...profile,about:e.target.value})} className="input-admin w-full" placeholder="Expertise, problèmes résolus, résultats et objectif professionnel."/></Field>
        <Field label="Compétences"><input value={skillsText} onChange={e => setSkillsText(e.target.value)} className="input-admin w-full" placeholder="Excel, Power BI, SQL, Marketing digital"/></Field>
        <div className="grid gap-4 md:grid-cols-3"><Field label="Site web"><input type="url" value={profile.website_url} onChange={e => setProfile({...profile,website_url:e.target.value})} className="input-admin w-full"/></Field><Field label="LinkedIn"><input type="url" value={profile.linkedin_url} onChange={e => setProfile({...profile,linkedin_url:e.target.value})} className="input-admin w-full"/></Field><Field label="GitHub"><input type="url" value={profile.github_url} onChange={e => setProfile({...profile,github_url:e.target.value})} className="input-admin w-full"/></Field></div>
        <div className="mt-4 grid gap-4 md:grid-cols-[1fr_auto]"><Field label="Email public de contact"><div className="relative"><Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/><input type="email" value={profile.public_contact_email} onChange={e => setProfile({...profile,public_contact_email:e.target.value})} className="input-admin w-full pl-9" placeholder="contact@exemple.com"/></div></Field><label className="mt-8 flex items-center gap-2 text-sm"><input type="checkbox" checked={profile.show_contact_email} onChange={e => setProfile({...profile,show_contact_email:e.target.checked})}/> Afficher cet email</label></div>
        <div className="mt-5 flex flex-wrap gap-x-6 gap-y-3 text-sm"><label className="flex items-center gap-2"><input type="checkbox" checked={profile.open_to_work} onChange={e => setProfile({...profile,open_to_work:e.target.checked})}/> Disponible pour opportunités</label><label className="flex items-center gap-2"><input type="checkbox" checked={profile.show_country} onChange={e => setProfile({...profile,show_country:e.target.checked})}/> Afficher mon pays</label><label className="flex items-center gap-2"><input type="checkbox" checked={profile.show_project_scores} onChange={e => setProfile({...profile,show_project_scores:e.target.checked})}/> Afficher mes notes de projets</label><label className="flex items-center gap-2"><input type="checkbox" checked={profile.show_certificates} onChange={e => setProfile({...profile,show_certificates:e.target.checked})}/> Afficher mes certificats sélectionnés</label></div>

        <div className="mt-6 border-t border-gray-100 pt-5"><div className="flex items-center justify-between gap-3"><div><h3 className="flex items-center gap-2 text-sm font-bold"><Award size={16}/> Certificats publics</h3><p className="mt-1 text-xs text-gray-500">Sélection explicite uniquement. Un certificat révoqué ou expiré n'est jamais présenté comme actif sur le portfolio.</p></div><span className="text-xs text-gray-400">{selectedCertificateIds.length} sélectionné(s)</span></div>{activeCertificates.length === 0 ? <p className="mt-3 text-xs text-gray-400">Aucun certificat actif disponible.</p> : <div className="mt-3 grid gap-2 md:grid-cols-2">{activeCertificates.map(cert => <label key={cert.id} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 ${selectedCertificateIds.includes(cert.id)?"border-brand-200 bg-brand-50/40":"border-gray-100"}`}><input type="checkbox" className="mt-1" checked={selectedCertificateIds.includes(cert.id)} onChange={() => toggleCertificate(cert.id)}/><div className="min-w-0"><p className="truncate text-sm font-semibold">{cert.content_title}</p><p className="mt-0.5 text-[11px] text-gray-400">{cert.certificate_number} · {new Date(cert.issued_at).toLocaleDateString("fr-FR")}</p></div></label>)}</div>}</div>

        <div className="mt-6 flex flex-wrap gap-2"><button disabled={saving} onClick={() => void saveProfile()} className="btn-primary !py-2 !text-xs">{saving?<Loader2 size={14} className="animate-spin"/>:<Check size={14}/>} Enregistrer</button>{profile.is_public && <button onClick={() => void copy()} className="btn-outline !py-2 !text-xs">{copied?<Check size={14}/>:<Copy size={14}/>} {copied?"Copié":"Copier le lien"}</button>}<span className="ml-auto text-xs text-gray-400">{publicCount} projet(s) visible(s)</span></div>
      </section>

      {showAdd && <ManualItemForm onDone={async () => { setShowAdd(false); await load(); }} onError={setError}/>} 
      <section><div className="mb-4 flex items-center justify-between"><div><h2 className="text-lg font-bold">Projets du portfolio</h2><p className="text-xs text-gray-500">Les projets avec le badge KalanPro ont été validés par un instructeur.</p></div><Link href="/dashboard/student/projects" className="text-xs font-semibold text-brand-700">Mes projets KalanPro</Link></div>{items.length===0?<div className="card p-10 text-center text-gray-500">Aucun projet publié pour le moment.</div>:<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{items.map(item=><article key={item.id} className="card overflow-hidden"><div className="aspect-[16/9] bg-gray-100">{item.cover_image?<img src={item.cover_image} alt="" loading="lazy" decoding="async" className="h-full w-full object-cover"/>:<div className="grid h-full place-items-center text-gray-300"><Globe2 size={32}/></div>}</div><div className="p-5"><div className="flex items-start justify-between gap-2"><h3 className="font-bold">{item.title}</h3>{item.is_verified&&<span title="Projet validé sur KalanPro" className="badge bg-emerald-50 text-emerald-700"><ShieldCheck size={12}/> Vérifié</span>}</div>{item.role&&<p className="mt-1 text-xs font-medium text-brand-700">Rôle : {item.role}</p>}{item.is_verified&&<p className="mt-1 text-[11px] text-gray-400">{item.verified_course_title} · {item.verified_instructor_name}</p>}<p className="mt-3 line-clamp-3 text-sm leading-6 text-gray-600">{item.description||item.outcome||"Aucune description."}</p><div className="mt-3 flex flex-wrap gap-1">{(item.stack.length?item.stack:item.skills).slice(0,5).map(s=><span key={s} className="rounded-full bg-gray-100 px-2 py-1 text-[10px] font-medium text-gray-600">{s}</span>)}</div><div className="mt-4 flex flex-wrap gap-2"><button onClick={()=>setEditingItem(item)} className="btn-outline !px-2.5 !py-1.5 !text-xs"><Pencil size={13}/> Modifier</button><button onClick={()=>void patchItem(item,{is_public:!item.is_public})} className="btn-outline !px-2.5 !py-1.5 !text-xs">{item.is_public?<Eye size={13}/>:<EyeOff size={13}/>} {item.is_public?"Visible":"Masqué"}</button><button onClick={()=>void patchItem(item,{featured:!item.featured})} className="btn-outline !px-2.5 !py-1.5 !text-xs"><Star size={13}/>{item.featured?"À la une":"Mettre en avant"}</button><button onClick={()=>void remove(item)} className="rounded-lg border border-red-100 px-2.5 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50"><Trash2 size={13}/></button></div></div></article>)}</div>}</section>
    </>}
    {editingItem && <ItemEditModal item={editingItem} onClose={() => setEditingItem(null)} onDone={async () => { setEditingItem(null); await load(); }} onError={setError}/>} 
  </div>;
}

function ItemEditModal({item,onClose,onDone,onError}:{item:PortfolioItem;onClose:()=>void;onDone:()=>Promise<void>;onError:(v:string)=>void}) {
  const [f,setF]=useState<ItemFormState>({title:item.title,description:item.description,role:item.role,problem:item.problem,objective:item.objective,outcome:item.outcome,stack:item.stack.join(", "),video_url:item.video_url,started_at:item.started_at||"",completed_at:item.completed_at||"",external_url:item.external_url,repository_url:item.repository_url,skills:item.skills.join(", ")});
  const [cover,setCover]=useState<File|null>(null); const [busy,setBusy]=useState(false);
  async function submit(e:React.FormEvent){e.preventDefault();setBusy(true);onError("");try{const fd=buildItemFormData(f,cover,!item.is_verified);await api.patch(`/projects/portfolio-items/${item.id}/`,fd);await onDone()}catch(e){onError(e instanceof ApiError?e.message:"Modification impossible.")}finally{setBusy(false)}}
  return <div className="fixed inset-0 z-[90] grid place-items-center bg-black/50 p-4"><form onSubmit={submit} className="card max-h-[92vh] w-full max-w-3xl overflow-y-auto p-6"><div className="flex items-center justify-between"><div><h2 className="font-bold">Modifier le projet</h2>{item.is_verified&&<p className="mt-1 text-xs text-emerald-700">La preuve KalanPro reste immuable ; vous modifiez uniquement sa présentation.</p>}</div><button type="button" onClick={onClose} className="rounded-lg p-2 hover:bg-gray-100"><X size={18}/></button></div><RichItemFields f={f} setF={setF} allowEvidenceLinks={!item.is_verified}/><Upload cover={cover} setCover={setCover}/><div className="mt-5 flex gap-2"><button type="button" onClick={onClose} className="btn-outline">Annuler</button><button disabled={busy} className="btn-primary">{busy?<Loader2 size={14} className="animate-spin"/>:<Check size={14}/>} Enregistrer</button></div></form></div>;
}

function ManualItemForm({onDone,onError}:{onDone:()=>Promise<void>;onError:(v:string)=>void}) {
  const [f,setF]=useState<ItemFormState>(emptyItem); const [cover,setCover]=useState<File|null>(null); const [busy,setBusy]=useState(false);
  async function submit(e:React.FormEvent){e.preventDefault();setBusy(true);onError("");try{const fd=buildItemFormData(f,cover,true);fd.append("is_public","true");await api.post("/projects/portfolio-items/",fd);await onDone()}catch(e){onError(e instanceof ApiError?e.message:"Impossible d'ajouter le projet.")}finally{setBusy(false)}}
  return <form onSubmit={submit} className="card mb-6 p-5 sm:p-6"><h2 className="font-bold">Ajouter une réalisation externe</h2><p className="mt-1 text-xs text-gray-500">Décrivez le problème, votre rôle, la stack et le résultat obtenu.</p><RichItemFields f={f} setF={setF} allowEvidenceLinks/><Upload cover={cover} setCover={setCover}/><button disabled={busy} className="btn-primary mt-5 !py-2 !text-xs">{busy?<Loader2 size={14} className="animate-spin"/>:<Plus size={14}/>} Ajouter au portfolio</button></form>;
}

function RichItemFields({f,setF,allowEvidenceLinks}:{f:ItemFormState;setF:(v:ItemFormState)=>void;allowEvidenceLinks:boolean}) {
  return <><div className="grid gap-4 md:grid-cols-2"><Field label="Titre"><input required value={f.title} onChange={e=>setF({...f,title:e.target.value})} className="input-admin w-full"/></Field><Field label="Votre rôle"><input value={f.role} onChange={e=>setF({...f,role:e.target.value})} className="input-admin w-full" placeholder="Lead designer, Développeur backend..."/></Field></div><Field label="Résumé"><textarea rows={3} value={f.description} onChange={e=>setF({...f,description:e.target.value})} className="input-admin w-full"/></Field><div className="grid gap-4 md:grid-cols-2"><Field label="Problème / contexte"><textarea rows={3} value={f.problem} onChange={e=>setF({...f,problem:e.target.value})} className="input-admin w-full"/></Field><Field label="Objectif"><textarea rows={3} value={f.objective} onChange={e=>setF({...f,objective:e.target.value})} className="input-admin w-full"/></Field></div><Field label="Résultat / impact"><textarea rows={3} value={f.outcome} onChange={e=>setF({...f,outcome:e.target.value})} className="input-admin w-full" placeholder="Résultat mesurable, impact, apprentissage..."/></Field><div className="grid gap-4 md:grid-cols-2"><Field label="Stack / outils"><input value={f.stack} onChange={e=>setF({...f,stack:e.target.value})} className="input-admin w-full" placeholder="Django, React, PostgreSQL"/></Field><Field label="Compétences"><input value={f.skills} onChange={e=>setF({...f,skills:e.target.value})} disabled={!allowEvidenceLinks} className="input-admin w-full disabled:bg-gray-50"/></Field></div><div className="grid gap-4 md:grid-cols-2"><Field label="Début"><input type="date" value={f.started_at} onChange={e=>setF({...f,started_at:e.target.value})} className="input-admin w-full"/></Field><Field label="Fin"><input type="date" value={f.completed_at} onChange={e=>setF({...f,completed_at:e.target.value})} className="input-admin w-full"/></Field></div><Field label="Vidéo de démonstration"><div className="relative"><Video size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/><input type="url" value={f.video_url} onChange={e=>setF({...f,video_url:e.target.value})} className="input-admin w-full pl-9" placeholder="https://..."/></div></Field>{allowEvidenceLinks&&<div className="grid gap-4 md:grid-cols-2"><Field label="Lien du projet"><input type="url" value={f.external_url} onChange={e=>setF({...f,external_url:e.target.value})} className="input-admin w-full"/></Field><Field label="Dépôt / code"><input type="url" value={f.repository_url} onChange={e=>setF({...f,repository_url:e.target.value})} className="input-admin w-full"/></Field></div>}</>;
}

function buildItemFormData(f:ItemFormState, cover:File|null, includeEvidenceLinks:boolean) {
  const fd=new FormData();
  for (const key of ["title","description","role","problem","objective","outcome","video_url","started_at","completed_at"] as const) fd.append(key,f[key]);
  fd.append("stack",JSON.stringify(splitList(f.stack)));
  if(includeEvidenceLinks){fd.append("external_url",f.external_url);fd.append("repository_url",f.repository_url);fd.append("skills",JSON.stringify(splitList(f.skills)))}
  if(cover)fd.append("cover_image",cover);
  return fd;
}

function Upload({cover,setCover}:{cover:File|null;setCover:(v:File|null)=>void}) { return <label className="mt-4 flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-gray-300 p-3 text-xs text-gray-500"><UploadCloud size={15}/>{cover?cover.name:"Image de couverture"}<input type="file" accept="image/*" className="hidden" onChange={e=>setCover(e.target.files?.[0]||null)}/></label>; }
function Field({label,children}:{label:string;children:React.ReactNode}){return <label className="mt-4 block"><span className="mb-1.5 block text-xs font-semibold text-gray-700">{label}</span>{children}</label>}
function splitList(value:string){return value.split(",").map(v=>v.trim()).filter(Boolean)}
