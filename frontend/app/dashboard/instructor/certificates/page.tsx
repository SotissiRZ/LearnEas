"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Award, CheckCircle2, Loader2, RefreshCw, Search, Settings2, ShieldX } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Certificate, Course, InteractiveFormation, Paginated } from "@/types";
import GuardScreen from "@/components/ui/GuardScreen";
import { useAuthGuard } from "@/hooks/useAuthGuard";

type Eligible = { enrollment_id:number; kind:"course"|"formation"; user_id:number; student_name:string; student_email:string; eligible:boolean; percent:number; threshold:number; reason:string; certificate_id:number|null };

type CertConfig = {
  certificate_enabled:boolean; certificate_auto_issue:boolean; certificate_threshold_percent?:number;
  certificate_attendance_percent?:number; certificate_validity_months?:number|null; certificate_title:string;
  certificate_subtitle:string; certificate_description:string; certificate_signatory_name:string;
  certificate_signatory_title:string; certificate_accent_color:string; certificate_number_prefix:string;
  certificate_show_duration:boolean; certificate_show_instructor:boolean; certificate_show_completion_date:boolean;
};

export default function InstructorCertificatesPage(){
  const {ready}=useAuthGuard({roles:["instructor","admin"],redirectTo:"/dashboard/instructor"});
  const [courses,setCourses]=useState<Course[]>([]); const [formations,setFormations]=useState<InteractiveFormation[]>([]);
  const [certs,setCerts]=useState<Certificate[]>([]); const [eligible,setEligible]=useState<Eligible[]>([]);
  const [kind,setKind]=useState<"course"|"formation">("course"); const [selected,setSelected]=useState("");
  const [config,setConfig]=useState<CertConfig|null>(null); const [q,setQ]=useState(""); const [busy,setBusy]=useState(false); const [message,setMessage]=useState(""); const [error,setError]=useState("");

  async function loadBase(){
    const [c,f,r]=await Promise.all([
      api.get<Paginated<Course>|Course[]>("/catalog/courses/my_courses/"),
      api.get<InteractiveFormation[]>("/formations/my_formations/"),
      api.get<Paginated<Certificate>|Certificate[]>("/enrollments/certificates/"),
    ]);
    const ca=(c as any).results||c; const fa=Array.isArray(f)?f:(f as any).results||[]; const ra=(r as any).results||r;
    setCourses(ca); setFormations(fa); setCerts(ra);
  }
  useEffect(()=>{if(ready)loadBase().catch(e=>setError(e instanceof ApiError?e.message:"Erreur de chargement."));},[ready]);

  async function choose(value:string){
    setSelected(value); setEligible([]); setMessage(""); setError(""); if(!value){setConfig(null);return;}
    const id=Number(value); const content=kind==="course"?courses.find(c=>c.id===id):formations.find(f=>f.id===id); if(!content)return;
    let detail:any=content;
    if(kind==="course") detail=await api.get<Course>(`/catalog/courses/${(content as Course).slug}/`);
    else detail=await api.get<InteractiveFormation>(`/formations/${(content as InteractiveFormation).slug}/`);
    setConfig({
      certificate_enabled:detail.certificate_enabled??true, certificate_auto_issue:detail.certificate_auto_issue??true,
      certificate_threshold_percent:detail.certificate_threshold_percent??100, certificate_attendance_percent:detail.certificate_attendance_percent??80,
      certificate_validity_months:detail.certificate_validity_months??null, certificate_title:detail.certificate_title||"Certificat",
      certificate_subtitle:detail.certificate_subtitle||"", certificate_description:detail.certificate_description||"",
      certificate_signatory_name:detail.certificate_signatory_name||"", certificate_signatory_title:detail.certificate_signatory_title||"",
      certificate_accent_color:detail.certificate_accent_color||"#1f6f5c", certificate_number_prefix:detail.certificate_number_prefix||"LE-CERT",
      certificate_show_duration:detail.certificate_show_duration??true, certificate_show_instructor:detail.certificate_show_instructor??true,
      certificate_show_completion_date:detail.certificate_show_completion_date??true,
    });
    const rows=await api.get<Eligible[]>(`/enrollments/certificates/eligible/?${kind}=${id}`); setEligible(rows);
  }

  async function saveConfig(){
    if(!selected||!config)return; setBusy(true);setError("");setMessage("");
    try{const id=Number(selected); const content=kind==="course"?courses.find(c=>c.id===id):formations.find(f=>f.id===id); if(!content)return;
      const body:any={...config}; if(kind==="course") delete body.certificate_attendance_percent; else delete body.certificate_threshold_percent;
      await api.patch(kind==="course"?`/catalog/courses/${(content as Course).slug}/`:`/formations/${(content as InteractiveFormation).slug}/`,body); setMessage("Configuration enregistrée.");
    }catch(e){setError(e instanceof ApiError?e.message:"Enregistrement impossible.");}finally{setBusy(false)}
  }

  async function issue(row:Eligible){setBusy(true);setError("");try{await api.post("/enrollments/certificates/issue/",row.kind==="course"?{course_enrollment_id:row.enrollment_id}:{formation_enrollment_id:row.enrollment_id});await choose(selected);await loadBase();}catch(e){setError(e instanceof ApiError?e.message:"Émission impossible.");}finally{setBusy(false)}}
  async function issueBulk(){if(!selected)return;setBusy(true);setError("");setMessage("");try{const payload=kind==="course"?{course_id:Number(selected)}:{formation_id:Number(selected)};const r=await api.post<{issued_count:number}>("/enrollments/certificates/issue-bulk/",payload);setMessage(`${r.issued_count} certificat(s) délivré(s).`);await choose(selected);await loadBase();}catch(e){setError(e instanceof ApiError?e.message:"Délivrance groupée impossible.");}finally{setBusy(false)}}
  async function revoke(cert:Certificate){const reason=window.prompt("Motif de révocation :","")||""; if(!window.confirm("Révoquer ce certificat ?"))return; await api.post(`/enrollments/certificates/${cert.id}/revoke/`,{reason}); await loadBase();}
  async function reissue(cert:Certificate){if(!window.confirm("Réémettre ce certificat avec un nouveau numéro et un nouveau code de vérification ?"))return;await api.post(`/enrollments/certificates/${cert.id}/reissue/`,{});await loadBase();}
  const filtered=useMemo(()=>certs.filter(c=>`${c.student_name} ${c.content_title} ${c.certificate_number}`.toLowerCase().includes(q.toLowerCase())),[certs,q]);
  if(!ready)return <GuardScreen/>;
  return <div className="space-y-6">
    <div><h1 className="text-2xl font-bold">Certificats</h1><p className="text-sm text-gray-500">Configurez les règles de délivrance, contrôlez l'éligibilité et gérez les certificats émis.</p></div>
    {error&&<div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}{message&&<div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
    <section className="card p-5"><div className="mb-4 flex items-center gap-2 font-bold"><Settings2 size={18}/> Configuration par contenu</div><div className="grid gap-3 md:grid-cols-[180px_1fr]"><select className="input-admin" value={kind} onChange={e=>{setKind(e.target.value as any);setSelected("");setConfig(null);setEligible([])}}><option value="course">Cours</option><option value="formation">Formation live</option></select><select className="input-admin" value={selected} onChange={e=>choose(e.target.value)}><option value="">Sélectionner...</option>{(kind==="course"?courses:formations).map((x:any)=><option key={x.id} value={x.id}>{x.title}</option>)}</select></div>{config&&<CertificateConfigForm config={config} kind={kind} onChange={setConfig} onSave={saveConfig} busy={busy}/>}</section>
    {selected&&<section className="card p-5"><div className="mb-4 flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-bold">Apprenants et éligibilité</h2><p className="text-xs text-gray-400">Le pourcentage est calculé automatiquement à partir de la progression ou du temps réel de présence.</p></div><div className="flex flex-wrap gap-2"><button onClick={()=>choose(selected)} className="btn-outline !py-1.5 !text-xs"><RefreshCw size={14}/> Actualiser</button><button disabled={busy||!eligible.some(r=>r.eligible&&!r.certificate_id)} onClick={issueBulk} className="btn-primary !py-1.5 !text-xs disabled:opacity-40"><Award size={14}/> Délivrer tous les éligibles</button></div></div><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-sm"><thead className="table-head"><tr><th>Apprenant</th><th>Progression / présence</th><th>Seuil</th><th>État</th><th></th></tr></thead><tbody className="divide-y divide-gray-100">{eligible.map(r=><tr key={`${r.kind}-${r.enrollment_id}`}><td className="px-4 py-3"><p className="font-semibold">{r.student_name}</p><p className="text-xs text-gray-400">{r.student_email}</p></td><td className="px-4 py-3">{Number(r.percent).toFixed(1)} %</td><td className="px-4 py-3">{r.threshold} %</td><td className="px-4 py-3">{r.certificate_id?<span className="badge bg-blue-50 text-blue-700">Émis</span>:r.eligible?<span className="badge bg-emerald-50 text-emerald-700">Éligible</span>:<span className="badge bg-amber-50 text-amber-700">En attente</span>}</td><td className="px-4 py-3 text-right">{!r.certificate_id&&<button disabled={!r.eligible||busy} onClick={()=>issue(r)} className="btn-primary !py-1.5 !text-xs disabled:opacity-40"><Award size={14}/> Délivrer</button>}</td></tr>)}</tbody></table>{eligible.length===0&&<p className="py-6 text-center text-sm text-gray-400">Aucune inscription.</p>}</div></section>}
    <section><div className="mb-3 flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-bold">Registre de mes certificats</h2><p className="text-xs text-gray-400">Révocation et réémission sont tracées par le registre.</p></div><label className="relative"><Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/><input className="input-admin pl-8" value={q} onChange={e=>setQ(e.target.value)} placeholder="Rechercher..."/></label></div><div className="card overflow-x-auto"><table className="w-full min-w-[900px] text-sm"><thead className="table-head"><tr><th>Apprenant</th><th>Contenu</th><th>N°</th><th>Émis</th><th>Statut</th><th>Actions</th></tr></thead><tbody className="divide-y divide-gray-100">{filtered.map(c=><tr key={c.id}><td className="px-4 py-3 font-semibold">{c.student_name}</td><td className="px-4 py-3">{c.content_title}</td><td className="px-4 py-3 text-xs">{c.certificate_number}</td><td className="px-4 py-3 text-gray-500">{new Date(c.issued_at).toLocaleDateString("fr-FR")}</td><td className="px-4 py-3"><span className={`badge ${c.effective_status==="active"?"bg-emerald-50 text-emerald-700":"bg-red-50 text-red-600"}`}>{c.effective_status}</span></td><td className="px-4 py-3"><div className="flex gap-2"><Link href={`/certificates/${c.id}`} className="text-xs font-semibold text-brand-700">Voir</Link>{c.effective_status==="active"?<button onClick={()=>revoke(c)} className="text-xs font-semibold text-red-600"><ShieldX size={13} className="inline"/> Révoquer</button>:<button onClick={()=>reissue(c)} className="text-xs font-semibold text-brand-700"><CheckCircle2 size={13} className="inline"/> Réémettre</button>}</div></td></tr>)}</tbody></table></div></section>
  </div>;
}

function CertificateConfigForm({config,kind,onChange,onSave,busy}:{config:CertConfig;kind:"course"|"formation";onChange:(c:CertConfig)=>void;onSave:()=>void;busy:boolean}){const set=(k:keyof CertConfig,v:any)=>onChange({...config,[k]:v});return <div className="mt-5 space-y-4 border-t border-gray-100 pt-5"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"><Toggle label="Certificat activé" value={config.certificate_enabled} set={v=>set("certificate_enabled",v)}/><Toggle label="Délivrance automatique" value={config.certificate_auto_issue} set={v=>set("certificate_auto_issue",v)}/><Toggle label="Afficher l'instructeur" value={config.certificate_show_instructor} set={v=>set("certificate_show_instructor",v)}/><Toggle label="Afficher la durée" value={config.certificate_show_duration} set={v=>set("certificate_show_duration",v)}/><Toggle label="Afficher la date" value={config.certificate_show_completion_date} set={v=>set("certificate_show_completion_date",v)}/></div><div className="grid gap-3 md:grid-cols-3"><Field label={kind==="course"?"Seuil de progression (%)":"Présence minimale (%)"} type="number" value={kind==="course"?config.certificate_threshold_percent??100:config.certificate_attendance_percent??80} onChange={v=>set(kind==="course"?"certificate_threshold_percent":"certificate_attendance_percent",Number(v))}/><Field label="Validité (mois, vide = illimitée)" type="number" value={config.certificate_validity_months??""} onChange={v=>set("certificate_validity_months",v===""?null:Number(v))}/><Field label="Préfixe du numéro" value={config.certificate_number_prefix} onChange={v=>set("certificate_number_prefix",v)}/><Field label="Titre" value={config.certificate_title} onChange={v=>set("certificate_title",v)}/><Field label="Sous-titre" value={config.certificate_subtitle} onChange={v=>set("certificate_subtitle",v)}/><Field label="Couleur" type="color" value={config.certificate_accent_color} onChange={v=>set("certificate_accent_color",v)}/><Field label="Signataire" value={config.certificate_signatory_name} onChange={v=>set("certificate_signatory_name",v)}/><Field label="Fonction du signataire" value={config.certificate_signatory_title} onChange={v=>set("certificate_signatory_title",v)}/></div><label className="block text-xs font-medium text-gray-500">Description<textarea className="input-admin mt-1 min-h-24 w-full" value={config.certificate_description} onChange={e=>set("certificate_description",e.target.value)}/></label><button disabled={busy} onClick={onSave} className="btn-primary">{busy&&<Loader2 size={14} className="animate-spin"/>} Enregistrer la configuration</button></div>}
function Field({label,value,onChange,type="text"}:{label:string;value:string|number;onChange:(v:string)=>void;type?:string}){return <label className="text-xs font-medium text-gray-500">{label}<input type={type} className="input-admin mt-1 w-full" value={value} min={type==="number"?0:undefined} max={label.includes("%")?100:undefined} onChange={e=>onChange(e.target.value)}/></label>}
function Toggle({label,value,set}:{label:string;value:boolean;set:(v:boolean)=>void}){return <label className="flex items-center justify-between gap-3 rounded-xl border border-gray-100 p-3 text-sm"><span>{label}</span><input type="checkbox" checked={value} onChange={e=>set(e.target.checked)}/></label>}
