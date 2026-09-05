(() => {
  const DB_NAME = "kalanpro-offline-media", DB_VERSION = 2, STORE = "videos";
  const list = document.getElementById("list"), video = document.getElementById("video"), player = document.getElementById("player");
  const playerTitle = document.getElementById("playerTitle"), playerMeta = document.getElementById("playerMeta"), network = document.getElementById("network");
  let active = null, activeUrl = null, lastVideoTime = 0, lastWall = 0, pendingWatch = 0, seeking = false, lastPersist = 0;
  const currentUserId = Number(localStorage.getItem("kalanpro:offline-user-id") || 0);

  function updateNetwork(){ network.textContent = navigator.onLine ? "En ligne" : "Hors ligne"; network.style.background = navigator.onLine ? "#ecfdf5" : "#fff7ed"; network.style.color = navigator.onLine ? "#047857" : "#c2410c"; }
  addEventListener("online", updateNetwork); addEventListener("offline", updateNetwork); updateNetwork();
  function fmt(bytes){ const mb=Number(bytes||0)/1048576; return mb>=1024 ? (mb/1024).toFixed(1)+" Go" : Math.max(1,Math.round(mb))+" Mo"; }
  function resumeKey(row){ return `kalanpro:resume:${row.userId}:${row.courseId}`; }
  function readResume(row){ try{return JSON.parse(localStorage.getItem(resumeKey(row))||"{}")}catch{return{}} }
  function persistProgress(force=false){
    if(!active) return;
    const now=Date.now(); if(!force && now-lastPersist<3000) return; lastPersist=now;
    try{
      const rows=readResume(active), key=String(active.lessonId), prev=rows[key]||{};
      rows[key]={ position:Math.max(0,Math.floor(video.currentTime||0)), updatedAt:now, watchedPending:Math.max(0,Math.floor((prev.watchedPending||0)+pendingWatch)), offlinePending:true };
      pendingWatch=0; localStorage.setItem(resumeKey(active),JSON.stringify(rows));
    }catch{}
  }
  function resetTracker(){ lastVideoTime=Number(video.currentTime||0); lastWall=performance.now(); }
  video.addEventListener("play", resetTracker);
  video.addEventListener("seeking",()=>{seeking=true; persistProgress(true)});
  video.addEventListener("seeked",()=>{seeking=false; resetTracker(); persistProgress(true)});
  video.addEventListener("timeupdate",()=>{
    const current=Number(video.currentTime||0), wall=performance.now();
    if(!video.paused && !seeking && lastWall>0){
      const advance=current-lastVideoTime, elapsed=Math.max(0,(wall-lastWall)/1000);
      if(advance>0 && advance<15 && elapsed<15) pendingWatch += Math.max(0,Math.min(advance,elapsed*2.2));
    }
    lastVideoTime=current; lastWall=wall; persistProgress(false);
  });
  video.addEventListener("pause",()=>persistProgress(true));
  video.addEventListener("ended",()=>persistProgress(true));
  addEventListener("beforeunload",()=>persistProgress(true));

  function openDb(){ return new Promise((resolve,reject)=>{ const req=indexedDB.open(DB_NAME,DB_VERSION); req.onupgradeneeded=(event)=>{ const db=req.result; let store;if(!db.objectStoreNames.contains(STORE)) store=db.createObjectStore(STORE,{keyPath:"key"}); else store=req.transaction.objectStore(STORE); if(!store.indexNames.contains("courseId"))store.createIndex("courseId","courseId",{unique:false});if(!store.indexNames.contains("userId"))store.createIndex("userId","userId",{unique:false});if(!store.indexNames.contains("userCourse"))store.createIndex("userCourse",["userId","courseId"],{unique:false});if((event.oldVersion||0)<2)store.clear();}; req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error); }); }
  async function rows(){ const db=await openDb(); return new Promise((resolve,reject)=>{ const tx=db.transaction(STORE,"readonly"), idx=tx.objectStore(STORE).index("userId"), req=idx.getAll(IDBKeyRange.only(currentUserId)); req.onsuccess=()=>resolve(req.result||[]);req.onerror=()=>reject(req.error);tx.oncomplete=()=>db.close(); }); }
  async function remove(row){ const db=await openDb(); await new Promise((resolve,reject)=>{ const tx=db.transaction(STORE,"readwrite"),req=tx.objectStore(STORE).delete(row.key);req.onsuccess=resolve;req.onerror=()=>reject(req.error);tx.oncomplete=()=>db.close();}); if(active&&active.key===row.key){persistProgress(true);video.pause();video.removeAttribute("src");video.load();player.classList.remove("active");if(activeUrl)URL.revokeObjectURL(activeUrl);active=null;activeUrl=null;} await render(); }
  function play(row){ persistProgress(true); if(activeUrl)URL.revokeObjectURL(activeUrl); active=row;activeUrl=URL.createObjectURL(row.blob);video.src=activeUrl;playerTitle.textContent=row.title;playerMeta.textContent=`Copie locale · ${fmt(row.size)}`;player.classList.add("active");const resume=readResume(row)[String(row.lessonId)];video.onloadedmetadata=()=>{ if(resume&&Number(resume.position)>0&&Number(resume.position)<video.duration-3)video.currentTime=Number(resume.position);resetTracker();};void video.play().catch(()=>{});player.scrollIntoView({behavior:"smooth",block:"start"}); }
  async function render(){
    if(!currentUserId){list.innerHTML='<div class="empty">Aucun utilisateur hors connexion actif. Connectez-vous au moins une fois à KalanPro avant de télécharger vos leçons.</div>';return;}
    try{
      const data=(await rows()).sort((a,b)=>b.downloadedAt-a.downloadedAt); if(!data.length){list.innerHTML='<div class="empty">Aucune vidéo téléchargée pour ce compte.</div>';return;}
      list.innerHTML="";
      data.forEach(row=>{ const card=document.createElement("article");card.className="card";const date=new Date(row.downloadedAt).toLocaleDateString("fr-FR");card.innerHTML=`<h2></h2><div class="meta">${fmt(row.size)} · enregistrée le ${date}</div><div class="actions"><button class="primary">Lire hors connexion</button><button class="danger">Supprimer</button><a class="btn ghost" href="/">KalanPro</a></div>`;card.querySelector("h2").textContent=row.title;const [playBtn,delBtn]=card.querySelectorAll("button");playBtn.addEventListener("click",()=>play(row));delBtn.addEventListener("click",()=>void remove(row));list.appendChild(card); });
    }catch{ list.innerHTML='<div class="empty">Le stockage hors connexion est indisponible sur ce navigateur.</div>'; }
  }
  void render();
})();
