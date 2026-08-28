"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Mic, MicOff, Video, VideoOff, PhoneOff, PlayCircle, StopCircle, Users, Loader2, ShieldCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";

interface RoomInfo {
  id: number; room_key: string; title: string; session_number: number; scheduled_at: string;
  planned_duration_minutes: number; started_at: string | null; ended_at: string | null;
  completed: boolean; is_organizer: boolean; user: { id: number; name: string };
}
interface Person { user_id: number; name: string; role: string }
interface SignalMessage { id: number; sender_id: number; sender_name: string; kind: "offer" | "answer" | "ice"; payload: any }
interface RemoteFeed { userId: number; name: string; stream: MediaStream }

export default function LiveSessionPage({ params }: { params: { id: string } }) {
  const { ready } = useAuthGuard();
  const router = useRouter();
  const sessionId = Number(params.id);
  const [room, setRoom] = useState<RoomInfo | null>(null);
  const [error, setError] = useState("");
  const [joining, setJoining] = useState(false);
  const [attendanceId, setAttendanceId] = useState<number | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [remoteFeeds, setRemoteFeeds] = useState<RemoteFeed[]>([]);
  const [micOn, setMicOn] = useState(true);
  const [cameraOn, setCameraOn] = useState(true);
  const [actionBusy, setActionBusy] = useState(false);
  const localVideoRef = useRef<HTMLVideoElement | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const peersRef = useRef<Map<number, RTCPeerConnection>>(new Map());
  const peerNamesRef = useRef<Map<number, string>>(new Map());
  const pendingIceRef = useRef<Map<number, RTCIceCandidateInit[]>>(new Map());
  const lastSignalIdRef = useRef(0);

  useEffect(() => {
    if (!ready || !Number.isFinite(sessionId)) return;
    let cancelled = false;
    const loadRoom = async () => {
      try {
        const data = await api.get<RoomInfo>(`/sessions/${sessionId}/room/`);
        if (!cancelled) { setRoom(data); setError(""); }
      } catch (e) {
        if (!cancelled) setError(e instanceof ApiError ? e.message : "Salle introuvable.");
      }
    };
    loadRoom();
    const timer = window.setInterval(() => {
      if (!attendanceId) loadRoom();
    }, 5000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [ready, sessionId, attendanceId]);

  const sendSignal = useCallback(async (recipientId: number, kind: string, payload: any) => {
    await api.post(`/sessions/${sessionId}/signal/`, { recipient_id: recipientId, kind, payload });
  }, [sessionId]);

  const ensurePeer = useCallback((peerId: number, name: string) => {
    const existing = peersRef.current.get(peerId);
    if (existing) return existing;
    const stunUrl = process.env.NEXT_PUBLIC_RTC_STUN_URL || "stun:stun.l.google.com:19302";
    const turnUrl = process.env.NEXT_PUBLIC_RTC_TURN_URL || "";
    const iceServers: RTCIceServer[] = [];
    if (stunUrl) iceServers.push({ urls: stunUrl });
    if (turnUrl) {
      iceServers.push({
        urls: turnUrl,
        username: process.env.NEXT_PUBLIC_RTC_TURN_USERNAME || undefined,
        credential: process.env.NEXT_PUBLIC_RTC_TURN_CREDENTIAL || undefined,
      });
    }
    const pc = new RTCPeerConnection({ iceServers });
    peersRef.current.set(peerId, pc);
    peerNamesRef.current.set(peerId, name);
    localStreamRef.current?.getTracks().forEach((track) => pc.addTrack(track, localStreamRef.current!));
    pc.onicecandidate = (event) => { if (event.candidate) sendSignal(peerId, "ice", event.candidate.toJSON()).catch(() => {}); };
    pc.ontrack = (event) => {
      const stream = event.streams[0] || new MediaStream([event.track]);
      setRemoteFeeds((prev) => [...prev.filter((f) => f.userId !== peerId), { userId: peerId, name, stream }]);
    };
    pc.onconnectionstatechange = () => {
      if (["failed", "closed", "disconnected"].includes(pc.connectionState)) {
        setRemoteFeeds((prev) => prev.filter((f) => f.userId !== peerId));
      }
    };
    return pc;
  }, [sendSignal]);

  const flushIce = useCallback(async (peerId: number, pc: RTCPeerConnection) => {
    const pending = pendingIceRef.current.get(peerId) || [];
    for (const candidate of pending) { try { await pc.addIceCandidate(candidate); } catch {} }
    pendingIceRef.current.delete(peerId);
  }, []);

  const handleSignal = useCallback(async (message: SignalMessage) => {
    const pc = ensurePeer(message.sender_id, message.sender_name);
    if (message.kind === "offer") {
      await pc.setRemoteDescription(new RTCSessionDescription(message.payload));
      await flushIce(message.sender_id, pc);
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      await sendSignal(message.sender_id, "answer", answer);
    } else if (message.kind === "answer") {
      await pc.setRemoteDescription(new RTCSessionDescription(message.payload));
      await flushIce(message.sender_id, pc);
    } else if (message.kind === "ice") {
      if (pc.remoteDescription) await pc.addIceCandidate(message.payload);
      else pendingIceRef.current.set(message.sender_id, [...(pendingIceRef.current.get(message.sender_id) || []), message.payload]);
    }
  }, [ensurePeer, flushIce, sendSignal]);

  async function createOffer(peerId: number, name: string) {
    const pc = ensurePeer(peerId, name);
    if (pc.signalingState !== "stable") return;
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    await sendSignal(peerId, "offer", offer);
  }

  async function enterRoom() {
    if (!room) return;
    setJoining(true); setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      localStreamRef.current = stream;
      if (localVideoRef.current) localVideoRef.current.srcObject = stream;
      const attendance = await api.post<{ id: number }>(`/sessions/${sessionId}/join/`);
      setAttendanceId(attendance.id);
    } catch (e) {
      localStreamRef.current?.getTracks().forEach((t) => t.stop()); localStreamRef.current = null;
      setError(e instanceof ApiError ? e.message : "Impossible d'accéder à la caméra/micro. Autorisez-les dans le navigateur.");
    } finally { setJoining(false); }
  }

  useEffect(() => {
    if (!attendanceId || !room) return;
    let cancelled = false;
    async function tick() {
      try {
        await api.post(`/sessions/${sessionId}/heartbeat/`, { attendance_id: attendanceId });
        const active = await api.get<Person[]>(`/sessions/${sessionId}/presence/`);
        if (cancelled) return;
        setPeople(active);
        for (const person of active) {
          if (person.user_id !== room!.user.id && room!.user.id < person.user_id && !peersRef.current.has(person.user_id)) {
            createOffer(person.user_id, person.name).catch(() => {});
          }
        }
      } catch {}
    }
    async function pollSignals() {
      try {
        const messages = await api.get<SignalMessage[]>(`/sessions/${sessionId}/signal/?after=${lastSignalIdRef.current}`);
        for (const message of messages) {
          lastSignalIdRef.current = Math.max(lastSignalIdRef.current, message.id);
          await handleSignal(message);
        }
      } catch {}
    }
    tick(); pollSignals();
    const heartbeatTimer = window.setInterval(tick, 5000);
    const signalTimer = window.setInterval(pollSignals, 1000);
    return () => { cancelled = true; window.clearInterval(heartbeatTimer); window.clearInterval(signalTimer); };
  }, [attendanceId, room, sessionId, handleSignal]);

  async function startSession() {
    setActionBusy(true);
    try { await api.post(`/sessions/${sessionId}/start/`); setRoom(await api.get<RoomInfo>(`/sessions/${sessionId}/room/`)); }
    finally { setActionBusy(false); }
  }
  async function leaveRoom(ended = false) {
    if (attendanceId) await api.post(`/sessions/${sessionId}/leave/`, { attendance_id: attendanceId }).catch(() => {});
    localStreamRef.current?.getTracks().forEach((t) => t.stop());
    peersRef.current.forEach((pc) => pc.close()); peersRef.current.clear();
    setAttendanceId(null); setRemoteFeeds([]);
    if (ended) router.push("/dashboard/instructor/formations");
    else router.back();
  }
  async function endSession() {
    if (!confirm("Terminer cette séance pour tous les participants ?")) return;
    setActionBusy(true);
    try { await api.post(`/sessions/${sessionId}/end/`); await leaveRoom(true); }
    finally { setActionBusy(false); }
  }
  function toggleMic() { const next = !micOn; localStreamRef.current?.getAudioTracks().forEach((t) => { t.enabled = next; }); setMicOn(next); }
  function toggleCamera() { const next = !cameraOn; localStreamRef.current?.getVideoTracks().forEach((t) => { t.enabled = next; }); setCameraOn(next); }

  if (!ready || (!room && !error)) return <GuardScreen />;
  if (error && !room) return <div className="container-app py-20 text-center text-red-600">{error}</div>;
  if (!room) return null;

  return <div className="min-h-screen bg-gray-950 text-white">
    <div className="mx-auto max-w-7xl px-4 py-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-brand-300">Salle LearnEas · Séance {room.session_number}</p><h1 className="text-xl font-bold">{room.title}</h1><p className="text-xs text-gray-400">{people.length} participant(s) en ligne · {room.planned_duration_minutes} min prévues</p></div><div className="flex gap-2">{room.is_organizer && !room.started_at && !room.completed && <button onClick={startSession} disabled={actionBusy} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold"><PlayCircle size={16} className="mr-1 inline" /> Démarrer</button>}{room.is_organizer && room.started_at && !room.completed && <button onClick={endSession} disabled={actionBusy} className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold"><StopCircle size={16} className="mr-1 inline" /> Terminer</button>}</div></div>

      {!attendanceId ? <div className="mx-auto mt-16 max-w-lg rounded-2xl border border-white/10 bg-white/5 p-8 text-center"><ShieldCheck size={42} className="mx-auto mb-4 text-brand-300" /><h2 className="text-xl font-bold">Prêt à rejoindre la séance ?</h2><p className="mt-2 text-sm text-gray-400">Votre présence et votre temps de connexion seront enregistrés pour le suivi de la formation.</p>{room.completed ? <p className="mt-5 text-sm text-gray-400">Cette séance est terminée.</p> : !room.is_organizer && !room.started_at ? <div className="mt-5 rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-sm text-gray-300">La séance n'a pas encore été démarrée par l'organisateur.</p><p className="mt-1 text-xs text-gray-500">Cette page se met à jour automatiquement.</p></div> : <button onClick={enterRoom} disabled={joining} className="mt-6 rounded-xl bg-brand-600 px-6 py-3 font-semibold">{joining ? <Loader2 className="mr-2 inline animate-spin" size={18} /> : <Video className="mr-2 inline" size={18} />}Entrer dans la salle</button>}{error && <p className="mt-3 text-sm text-red-300">{error}</p>}</div> : <>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div className="relative aspect-video overflow-hidden rounded-2xl bg-gray-900"><video ref={localVideoRef} autoPlay muted playsInline className="h-full w-full object-cover" /><span className="absolute bottom-3 left-3 rounded bg-black/50 px-2 py-1 text-xs">Vous · {room.is_organizer ? "Organisateur" : "Participant"}</span></div>
          {remoteFeeds.map((feed) => <RemoteVideo key={feed.userId} feed={feed} />)}
          {remoteFeeds.length === 0 && <div className="grid aspect-video place-items-center rounded-2xl border border-dashed border-white/10 bg-white/5 text-sm text-gray-500"><Users size={28} className="mb-2" />En attente des autres participants...</div>}
        </div>
        <div className="fixed bottom-6 left-1/2 z-20 flex -translate-x-1/2 items-center gap-2 rounded-2xl border border-white/10 bg-gray-900/95 p-2 shadow-2xl">
          <button onClick={toggleMic} className="rounded-xl p-3 hover:bg-white/10" title="Micro">{micOn ? <Mic /> : <MicOff />}</button><button onClick={toggleCamera} className="rounded-xl p-3 hover:bg-white/10" title="Caméra">{cameraOn ? <Video /> : <VideoOff />}</button><button onClick={() => leaveRoom(false)} className="rounded-xl bg-red-600 p-3" title="Quitter"><PhoneOff /></button>
        </div>
      </>}
    </div>
  </div>;
}

function RemoteVideo({ feed }: { feed: RemoteFeed }) {
  const ref = useRef<HTMLVideoElement | null>(null);
  useEffect(() => { if (ref.current) ref.current.srcObject = feed.stream; }, [feed.stream]);
  return <div className="relative aspect-video overflow-hidden rounded-2xl bg-gray-900"><video ref={ref} autoPlay playsInline className="h-full w-full object-cover" /><span className="absolute bottom-3 left-3 rounded bg-black/50 px-2 py-1 text-xs">{feed.name}</span></div>;
}
