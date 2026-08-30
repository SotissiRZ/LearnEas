import fs from 'node:fs'; import path from 'node:path';
const roots=['app','components']; let files=[];
function walk(d){for(const n of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,n.name); if(n.isDirectory()) walk(p); else if(/\.(tsx|ts|css)$/.test(n.name)) files.push(p)}}
roots.forEach(r=>walk(r)); let warns=[];
for(const f of files){const s=fs.readFileSync(f,'utf8');
  const fixed=[...s.matchAll(/min-w-\[(\d+)px\]/g)].filter(m=>Number(m[1])>=400);
  if(fixed.length && !/overflow-x-auto|overflow-auto/.test(s)) warns.push(`${f}: min-width fixe >=400px sans zone de défilement`);
  for(const m of s.matchAll(/<img\b[^>]*>/gs)){ if(!/loading=/.test(m[0])) warns.push(`${f}: image sans loading=lazy`); if(!/decoding=/.test(m[0])) warns.push(`${f}: image sans decoding=async`); }
}
console.log(`Audit mobile: ${files.length} fichiers inspectés`); if(warns.length){console.error(warns.join('\n')); process.exitCode=1}else console.log('OK · aucune alerte bloquante.');
