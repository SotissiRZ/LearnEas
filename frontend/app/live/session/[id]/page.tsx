"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Code2,
  Copy,
  Download,
  FileText,
  Hand,
  Loader2,
  Maximize2,
  MessageSquare,
  Mic,
  MicOff,
  Monitor,
  PanelRightClose,
  PanelRightOpen,
  ChevronUp,
  ChevronDown,
  ChevronsLeft,
  ChevronsRight,
  Minus,
  Plus,
  PenLine,
  Trash2,
  PhoneOff,
  Play,
  PlayCircle,
  ScreenShare,
  ScreenShareOff,
  Settings,
  ShieldCheck,
  StopCircle,
  Upload,
  UserPlus,
  Users,
  Video,
  VideoOff,
} from "lucide-react";
import { api, apiDownload, apiUploadWithProgress, ApiError } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";

interface RoomInfo {
  id: number;
  room_key: string;
  title: string;
  session_number: number;
  scheduled_at: string;
  planned_duration_minutes: number;
  started_at: string | null;
  ended_at: string | null;
  completed: boolean;
  is_organizer: boolean;
  is_guest: boolean;
  organizer: { id: number; name: string; avatar: string | null };
  user: { id: number; name: string; avatar: string | null };
}

interface Person {
  user_id: number;
  name: string;
  role: string;
  hand_raised: boolean;
  avatar: string | null;
}

interface SignalMessage {
  id: number;
  sender_id: number;
  sender_name: string;
  kind: "offer" | "answer" | "ice" | "chat" | "control" | "code" | "whiteboard";
  payload: any;
}

interface RemoteFeed {
  userId: number;
  name: string;
  stream: MediaStream;
}

interface ChatMessage {
  id: string;
  senderId: number;
  senderName: string;
  text: string;
  at: string;
  mine: boolean;
}

interface RoomFile {
  id: number;
  name: string;
  content_type: string;
  size: number;
  uploaded_at: string;
  uploader_id: number;
  uploader_name: string;
  download_path: string;
}

interface MediaChoice {
  deviceId: string;
  label: string;
}

interface SessionInvite {
  id: number;
  email: string;
  status: "pending_account" | "account_exists" | "accepted" | "revoked";
  created_at: string;
  accepted_at: string | null;
  user_id: number | null;
  dev_join_url?: string;
}

type SidebarTab = "participants" | "chat" | "files";
type WorkspaceMode = "video" | "code" | "whiteboard";
type ModerationAction = "mute" | "camera_off" | "remove";
type CodeLanguage = "javascript" | "html" | "css" | "python" | "java" | "c" | "cpp" | "text";
type CodeTheme = "midnight" | "dracula" | "light";
interface WhiteboardPoint { x: number; y: number }
interface WhiteboardStroke { id: string; color: string; width: number; points: WhiteboardPoint[] }

export default function LiveSessionPage() {
  const params = useParams<{ id: string }>();
  const { ready } = useAuthGuard();
  const router = useRouter();
  const sessionId = Number(params.id);

  const [room, setRoom] = useState<RoomInfo | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [joining, setJoining] = useState(false);
  const [attendanceId, setAttendanceId] = useState<number | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [remoteFeeds, setRemoteFeeds] = useState<RemoteFeed[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [files, setFiles] = useState<RoomFile[]>([]);
  const [invites, setInvites] = useState<SessionInvite[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteBusy, setInviteBusy] = useState(false);
  const [fileProgress, setFileProgress] = useState<number | null>(null);
  const [fileBusy, setFileBusy] = useState(false);
  const [micOn, setMicOn] = useState(true);
  const [cameraOn, setCameraOn] = useState(true);
  const [screenSharing, setScreenSharing] = useState(false);
  const [recording, setRecording] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [sidebarTab, setSidebarTab] = useState<SidebarTab>("participants");
  const [clockNow, setClockNow] = useState(Date.now());
  const [devicePanelOpen, setDevicePanelOpen] = useState(false);
  const [audioInputs, setAudioInputs] = useState<MediaChoice[]>([]);
  const [videoInputs, setVideoInputs] = useState<MediaChoice[]>([]);
  const [selectedAudioInput, setSelectedAudioInput] = useState("");
  const [selectedVideoInput, setSelectedVideoInput] = useState("");
  const [fullscreen, setFullscreen] = useState(false);
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("video");
  const [codeLanguage, setCodeLanguage] = useState<CodeLanguage>("javascript");
  const [codeFileName, setCodeFileName] = useState("main.js");
  const [codeText, setCodeText] = useState(`// Atelier LearnEas\nfunction bienvenue(nom) {\n  return \`Bonjour \${nom} !\`;\n}\n\nconsole.log(bienvenue("LearnEas"));`);
  const [codeOutput, setCodeOutput] = useState("");
  const [codeRunning, setCodeRunning] = useState(false);
  const [metricsCollapsed, setMetricsCollapsed] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [controlsCompact, setControlsCompact] = useState(true);
  const [whiteboardStrokes, setWhiteboardStrokes] = useState<WhiteboardStroke[]>([]);

  const stageRef = useRef<HTMLDivElement | null>(null);
  const localVideoRef = useRef<HTMLVideoElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const localStreamRef = useRef<MediaStream | null>(null);
  const cameraTrackRef = useRef<MediaStreamTrack | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const peersRef = useRef<Map<number, RTCPeerConnection>>(new Map());
  const pendingIceRef = useRef<Map<number, RTCIceCandidateInit[]>>(new Map());
  const lastSignalIdRef = useRef(0);
  const attendanceIdRef = useRef<number | null>(null);
  const remoteVideoElementsRef = useRef<Map<number, HTMLVideoElement>>(new Map());
  const codeRunnerRef = useRef<HTMLIFrameElement | null>(null);
  const skipCodeBroadcastRef = useRef(false);
  const codeRunNonceRef = useRef(0);
  const pyodideRef = useRef<any>(null);
  const pyodideLoadPromiseRef = useRef<Promise<any> | null>(null);
  const whiteboardBroadcastTimerRef = useRef<number | null>(null);
  const whiteboardRecipientsRef = useRef<Set<number>>(new Set());

  const recorderRef = useRef<MediaRecorder | null>(null);
  const recordingChunksRef = useRef<Blob[]>([]);
  const recordingStreamRef = useRef<MediaStream | null>(null);
  const recordingAnimationRef = useRef<number | null>(null);
  const recordingAudioContextRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    attendanceIdRef.current = attendanceId;
  }, [attendanceId]);

  useEffect(() => {
    if (!ready || !Number.isFinite(sessionId)) return;
    let cancelled = false;

    const loadRoom = async () => {
      try {
        const data = await api.get<RoomInfo>(`/sessions/${sessionId}/room/`);
        if (!cancelled) {
          setRoom(data);
          setError("");
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof ApiError ? e.message : "Salle introuvable.");
        }
      }
    };

    loadRoom();
    const timer = window.setInterval(() => {
      if (!attendanceIdRef.current) loadRoom();
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [ready, sessionId]);

  useEffect(() => {
    const timer = window.setInterval(() => setClockNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const previousHtmlOverflow = document.documentElement.style.overflow;
    const previousBodyOverflow = document.body.style.overflow;
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";
    return () => {
      document.documentElement.style.overflow = previousHtmlOverflow;
      document.body.style.overflow = previousBodyOverflow;
    };
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const onFullscreenChange = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);

  useEffect(() => {
    return () => {
      if (recordingAnimationRef.current !== null) {
        window.cancelAnimationFrame(recordingAnimationRef.current);
      }
      if (whiteboardBroadcastTimerRef.current !== null) {
        window.clearTimeout(whiteboardBroadcastTimerRef.current);
      }
      if (recorderRef.current?.state === "recording") {
        recorderRef.current.stop();
      }
      recordingAudioContextRef.current?.close().catch(() => {});
      recordingStreamRef.current?.getTracks().forEach((track) => track.stop());
      localStreamRef.current?.getTracks().forEach((track) => track.stop());
      screenStreamRef.current?.getTracks().forEach((track) => track.stop());
      peersRef.current.forEach((pc) => pc.close());
      peersRef.current.clear();
    };
  }, []);

  const participantsCount = people.length || (attendanceId ? 1 : 0);
  const raisedHandsCount = people.filter((person) => person.hand_raised).length;
  const myHandRaised = Boolean(people.find((person) => person.user_id === room?.user.id)?.hand_raised);

  const sendSignal = useCallback(
    async (recipientId: number, kind: SignalMessage["kind"], payload: any) => {
      await api.post(`/sessions/${sessionId}/signal/`, { recipient_id: recipientId, kind, payload });
    },
    [sessionId]
  );

  const updateWhiteboard = useCallback((strokes: WhiteboardStroke[]) => {
    const bounded = strokes.slice(-120).map((stroke) => ({
      ...stroke,
      points: stroke.points.slice(-600),
    }));
    setWhiteboardStrokes(bounded);
    if (!attendanceId || !room) return;
    if (whiteboardBroadcastTimerRef.current !== null) {
      window.clearTimeout(whiteboardBroadcastTimerRef.current);
    }
    const recipients = people.filter((person) => person.user_id !== room.user.id);
    whiteboardBroadcastTimerRef.current = window.setTimeout(() => {
      recipients.forEach((person) => {
        sendSignal(person.user_id, "whiteboard", {
          strokes: bounded,
          sent_at: new Date().toISOString(),
        }).catch(() => {});
      });
    }, 90);
  }, [attendanceId, room, people, sendSignal]);

  useEffect(() => {
    if (!attendanceId || !room) return;
    const activeIds = new Set(people.map((person) => person.user_id));
    for (const known of Array.from(whiteboardRecipientsRef.current)) {
      if (!activeIds.has(known)) whiteboardRecipientsRef.current.delete(known);
    }
    for (const person of people) {
      if (person.user_id === room.user.id || whiteboardRecipientsRef.current.has(person.user_id)) continue;
      whiteboardRecipientsRef.current.add(person.user_id);
      sendSignal(person.user_id, "whiteboard", { strokes: whiteboardStrokes, sent_at: new Date().toISOString() }).catch(() => {
        whiteboardRecipientsRef.current.delete(person.user_id);
      });
    }
  }, [attendanceId, room, people, sendSignal, whiteboardStrokes]);

  useEffect(() => {
    if (!attendanceId || !room) return;
    if (skipCodeBroadcastRef.current) {
      skipCodeBroadcastRef.current = false;
      return;
    }
    const activeRoom = room;
    const recipients = people.filter((person) => person.user_id !== activeRoom.user.id);
    const timer = window.setTimeout(() => {
      recipients.forEach((person) => {
        sendSignal(person.user_id, "code", {
          language: codeLanguage,
          file_name: codeFileName,
          text: codeText,
          sent_at: new Date().toISOString(),
        }).catch(() => {});
      });
    }, 450);
    return () => window.clearTimeout(timer);
  }, [attendanceId, room, people, codeLanguage, codeFileName, codeText, sendSignal]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.data?.source !== "learneas-code-runner") return;
      if (event.data?.nonce !== codeRunNonceRef.current) return;
      setCodeOutput(String(event.data?.output || ""));
      setCodeRunning(false);
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  const syncLocalVideo = useCallback(() => {
    if (localVideoRef.current && localStreamRef.current) {
      localVideoRef.current.srcObject = localStreamRef.current;
    }
  }, []);

  const replaceTrackOnPeers = useCallback(async (kind: "audio" | "video", track: MediaStreamTrack | null) => {
    const updates = Array.from(peersRef.current.values()).map(async (pc) => {
      const sender = pc.getSenders().find((item) => item.track?.kind === kind);
      if (sender) {
        await sender.replaceTrack(track);
      } else if (track && localStreamRef.current) {
        pc.addTrack(track, localStreamRef.current);
      }
    });
    await Promise.allSettled(updates);
  }, []);

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => {
      if (prev.some((item) => item.id === message.id)) return prev;
      return [...prev, message];
    });
  }, []);

  const stopAllConferenceMedia = useCallback(() => {
    screenStreamRef.current?.getTracks().forEach((track) => track.stop());
    localStreamRef.current?.getTracks().forEach((track) => track.stop());
    peersRef.current.forEach((pc) => pc.close());
    peersRef.current.clear();
    remoteVideoElementsRef.current.clear();
    screenStreamRef.current = null;
    localStreamRef.current = null;
    cameraTrackRef.current = null;
  }, []);

  const handleForcedRemoval = useCallback(async () => {
    const activeAttendanceId = attendanceIdRef.current;
    if (activeAttendanceId) {
      await api.post(`/sessions/${sessionId}/leave/`, { attendance_id: activeAttendanceId }).catch(() => {});
    }
    stopAllConferenceMedia();
    setAttendanceId(null);
    setRemoteFeeds([]);
    setPeople([]);
    window.alert("L'organisateur vous a retiré de cette séance.");
    router.push("/formations");
  }, [router, sessionId, stopAllConferenceMedia]);

  const ensurePeer = useCallback(
    (peerId: number, name: string) => {
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

      localStreamRef.current?.getTracks().forEach((track) => {
        pc.addTrack(track, localStreamRef.current!);
      });

      pc.onicecandidate = (event) => {
        if (event.candidate) {
          sendSignal(peerId, "ice", event.candidate.toJSON()).catch(() => {});
        }
      };

      pc.ontrack = (event) => {
        const stream = event.streams[0] || new MediaStream([event.track]);
        setRemoteFeeds((prev) => [
          ...prev.filter((feed) => feed.userId !== peerId),
          { userId: peerId, name, stream },
        ]);
      };

      pc.onconnectionstatechange = () => {
        if (["failed", "closed", "disconnected"].includes(pc.connectionState)) {
          setRemoteFeeds((prev) => prev.filter((feed) => feed.userId !== peerId));
          remoteVideoElementsRef.current.delete(peerId);
          peersRef.current.delete(peerId);
        }
      };

      return pc;
    },
    [sendSignal]
  );

  const flushIce = useCallback(async (peerId: number, pc: RTCPeerConnection) => {
    const pending = pendingIceRef.current.get(peerId) || [];
    for (const candidate of pending) {
      try {
        await pc.addIceCandidate(candidate);
      } catch {
        // Candidate devenu obsolète.
      }
    }
    pendingIceRef.current.delete(peerId);
  }, []);

  const handleSignal = useCallback(
    async (message: SignalMessage) => {
      if (message.kind === "chat") {
        const text = String(message.payload?.text || "").trim();
        if (!text) return;
        addMessage({
          id: `remote-${message.id}`,
          senderId: message.sender_id,
          senderName: message.sender_name,
          text,
          at: String(message.payload?.sent_at || new Date().toISOString()),
          mine: false,
        });
        return;
      }

      if (message.kind === "code") {
        skipCodeBroadcastRef.current = true;
        const nextLanguage = String(message.payload?.language || "javascript") as CodeLanguage;
        setCodeLanguage(nextLanguage);
        setCodeFileName(String(message.payload?.file_name || "main.js"));
        setCodeText(String(message.payload?.text || ""));
        setWorkspaceMode("code");
        setNotice(`${message.sender_name} partage l’éditeur de code.`);
        return;
      }

      if (message.kind === "whiteboard") {
        const strokes = Array.isArray(message.payload?.strokes) ? message.payload.strokes : [];
        setWhiteboardStrokes(strokes.slice(-120));
        setWorkspaceMode("whiteboard");
        return;
      }

      if (message.kind === "control") {
        const action = String(message.payload?.action || "") as ModerationAction;
        if (action === "mute") {
          localStreamRef.current?.getAudioTracks().forEach((track) => {
            track.enabled = false;
          });
          setMicOn(false);
          setNotice("L'organisateur a désactivé votre microphone.");
        } else if (action === "camera_off") {
          cameraTrackRef.current && (cameraTrackRef.current.enabled = false);
          if (!screenSharing) {
            localStreamRef.current?.getVideoTracks().forEach((track) => {
              track.enabled = false;
            });
          }
          setCameraOn(false);
          setNotice("L'organisateur a désactivé votre caméra.");
        } else if (action === "remove") {
          await handleForcedRemoval();
        }
        return;
      }

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
        if (pc.remoteDescription) {
          await pc.addIceCandidate(message.payload);
        } else {
          pendingIceRef.current.set(message.sender_id, [
            ...(pendingIceRef.current.get(message.sender_id) || []),
            message.payload,
          ]);
        }
      }
    },
    [addMessage, ensurePeer, flushIce, handleForcedRemoval, screenSharing, sendSignal]
  );

  const createOffer = useCallback(
    async (peerId: number, name: string) => {
      const pc = ensurePeer(peerId, name);
      if (pc.signalingState !== "stable") return;
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await sendSignal(peerId, "offer", offer);
    },
    [ensurePeer, sendSignal]
  );

  const refreshDevices = useCallback(async () => {
    if (!navigator.mediaDevices?.enumerateDevices) return;
    const devices = await navigator.mediaDevices.enumerateDevices();
    let micIndex = 0;
    let camIndex = 0;
    const microphones = devices
      .filter((device) => device.kind === "audioinput")
      .map((device) => ({
        deviceId: device.deviceId,
        label: device.label || `Microphone ${++micIndex}`,
      }));
    const cameras = devices
      .filter((device) => device.kind === "videoinput")
      .map((device) => ({
        deviceId: device.deviceId,
        label: device.label || `Caméra ${++camIndex}`,
      }));
    setAudioInputs(microphones);
    setVideoInputs(cameras);
    const currentAudio = localStreamRef.current?.getAudioTracks()[0]?.getSettings().deviceId;
    const currentVideo = cameraTrackRef.current?.getSettings().deviceId;
    if (currentAudio) setSelectedAudioInput(currentAudio);
    if (currentVideo) setSelectedVideoInput(currentVideo);
  }, []);

  async function enterRoom() {
    if (!room) return;
    setJoining(true);
    setError("");
    setNotice("");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
        audio: true,
      });
      localStreamRef.current = stream;
      cameraTrackRef.current = stream.getVideoTracks()[0] || null;
      if (cameraTrackRef.current) {
        cameraTrackRef.current.onended = () => setCameraOn(false);
        setCameraOn(cameraTrackRef.current.enabled);
      }
      setMicOn(stream.getAudioTracks().some((track) => track.enabled));
      syncLocalVideo();
      const attendance = await api.post<{ id: number }>(`/sessions/${sessionId}/join/`);
      setAttendanceId(attendance.id);
      attendanceIdRef.current = attendance.id;
      await refreshDevices();
    } catch (e) {
      localStreamRef.current?.getTracks().forEach((track) => track.stop());
      localStreamRef.current = null;
      cameraTrackRef.current = null;
      setError(
        e instanceof ApiError
          ? e.message
          : "Impossible d'accéder à la caméra/micro. Autorisez-les dans le navigateur."
      );
    } finally {
      setJoining(false);
    }
  }

  const loadFiles = useCallback(async () => {
    if (!attendanceIdRef.current) return;
    try {
      setFiles(await api.get<RoomFile[]>(`/sessions/${sessionId}/files/`));
    } catch {
      // Le rafraîchissement suivant réessaiera.
    }
  }, [sessionId]);

  useEffect(() => {
    if (!attendanceId || !room) return;
    const activeRoom = room;
    let cancelled = false;

    async function tick() {
      try {
        await api.post(`/sessions/${sessionId}/heartbeat/`, { attendance_id: attendanceId });
        const active = await api.get<Person[]>(`/sessions/${sessionId}/presence/`);
        if (cancelled) return;
        setPeople(active);
        for (const person of active) {
          if (
            person.user_id !== activeRoom.user.id &&
            activeRoom.user.id < person.user_id &&
            !peersRef.current.has(person.user_id)
          ) {
            createOffer(person.user_id, person.name).catch(() => {});
          }
        }
      } catch {
        // Une perte momentanée de réseau ne ferme pas la salle.
      }
    }

    async function pollSignals() {
      try {
        const incoming = await api.get<SignalMessage[]>(
          `/sessions/${sessionId}/signal/?after=${lastSignalIdRef.current}`
        );
        for (const message of incoming) {
          lastSignalIdRef.current = Math.max(lastSignalIdRef.current, message.id);
          await handleSignal(message);
        }
      } catch {
        // Le prochain poll réessaiera.
      }
    }

    tick();
    pollSignals();
    loadFiles();
    const heartbeatTimer = window.setInterval(tick, 5000);
    const signalTimer = window.setInterval(pollSignals, 1000);
    const filesTimer = window.setInterval(loadFiles, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(heartbeatTimer);
      window.clearInterval(signalTimer);
      window.clearInterval(filesTimer);
    };
  }, [attendanceId, room, sessionId, handleSignal, createOffer, loadFiles]);

  async function startSession() {
    setActionBusy(true);
    try {
      await api.post(`/sessions/${sessionId}/start/`);
      setRoom(await api.get<RoomInfo>(`/sessions/${sessionId}/room/`));
      setNotice("Séance démarrée.");
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Impossible de démarrer la séance.");
    } finally {
      setActionBusy(false);
    }
  }

  async function leaveRoom(ended = false) {
    if (recording) stopRecording();
    const activeAttendanceId = attendanceIdRef.current;
    if (activeAttendanceId) {
      await api.post(`/sessions/${sessionId}/leave/`, { attendance_id: activeAttendanceId }).catch(() => {});
    }
    stopAllConferenceMedia();
    attendanceIdRef.current = null;
    setAttendanceId(null);
    setRemoteFeeds([]);
    setPeople([]);
    setMessages([]);
    setFiles([]);
    whiteboardRecipientsRef.current.clear();
    setWhiteboardStrokes([]);
    setScreenSharing(false);
    if (ended) router.push("/dashboard/instructor/formations");
    else router.back();
  }

  async function endSession() {
    if (!confirm("Terminer cette séance pour tous les participants ?")) return;
    setActionBusy(true);
    try {
      await api.post(`/sessions/${sessionId}/end/`);
      await leaveRoom(true);
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Impossible de terminer la séance.");
    } finally {
      setActionBusy(false);
    }
  }

  function toggleMic() {
    const next = !micOn;
    localStreamRef.current?.getAudioTracks().forEach((track) => {
      track.enabled = next;
    });
    setMicOn(next);
  }

  async function toggleCamera() {
    if (screenSharing) {
      setNotice("Arrêtez le partage d'écran avant de modifier la caméra.");
      return;
    }
    let track = cameraTrackRef.current;
    if (!track || track.readyState === "ended") {
      try {
        const constraints: MediaTrackConstraints = selectedVideoInput
          ? { deviceId: { exact: selectedVideoInput }, width: { ideal: 1280 }, height: { ideal: 720 } }
          : { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" };
        const stream = await navigator.mediaDevices.getUserMedia({ video: constraints });
        track = stream.getVideoTracks()[0] || null;
        if (!track) throw new Error("Caméra indisponible");
        cameraTrackRef.current = track;
        track.onended = () => setCameraOn(false);
        if (!localStreamRef.current) localStreamRef.current = new MediaStream();
        localStreamRef.current.getVideoTracks().forEach((item) => localStreamRef.current?.removeTrack(item));
        localStreamRef.current.addTrack(track);
        await replaceTrackOnPeers("video", track);
        setCameraOn(true);
        syncLocalVideo();
        await localVideoRef.current?.play().catch(() => {});
        return;
      } catch {
        setCameraOn(false);
        setNotice("Impossible d'activer la caméra. Vérifiez les permissions du navigateur.");
        return;
      }
    }
    const next = !cameraOn;
    track.enabled = next;
    localStreamRef.current?.getVideoTracks().forEach((item) => {
      if (item.id === track?.id) item.enabled = next;
    });
    setCameraOn(next);
    if (next) {
      syncLocalVideo();
      await localVideoRef.current?.play().catch(() => {});
    }
  }

  async function switchAudioDevice(deviceId: string) {
    if (!deviceId || recording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { deviceId: { exact: deviceId } } });
      const nextTrack = stream.getAudioTracks()[0];
      if (!nextTrack || !localStreamRef.current) return;
      const previous = localStreamRef.current.getAudioTracks()[0];
      if (previous) {
        localStreamRef.current.removeTrack(previous);
        previous.stop();
      }
      nextTrack.enabled = micOn;
      localStreamRef.current.addTrack(nextTrack);
      await replaceTrackOnPeers("audio", nextTrack);
      setSelectedAudioInput(deviceId);
      await refreshDevices();
    } catch {
      setNotice("Impossible de changer de microphone.");
    }
  }

  async function switchVideoDevice(deviceId: string) {
    if (!deviceId || recording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      const nextTrack = stream.getVideoTracks()[0];
      if (!nextTrack || !localStreamRef.current) return;
      const previousCamera = cameraTrackRef.current;
      nextTrack.enabled = cameraOn;
      nextTrack.onended = () => setCameraOn(false);
      cameraTrackRef.current = nextTrack;
      setSelectedVideoInput(deviceId);

      if (!screenSharing) {
        const currentVideo = localStreamRef.current.getVideoTracks()[0];
        if (currentVideo) localStreamRef.current.removeTrack(currentVideo);
        localStreamRef.current.addTrack(nextTrack);
        await replaceTrackOnPeers("video", nextTrack);
        syncLocalVideo();
      }
      if (previousCamera && previousCamera.id !== nextTrack.id) previousCamera.stop();
      await refreshDevices();
    } catch {
      setNotice("Impossible de changer de caméra.");
    }
  }

  async function startScreenShare() {
    if (!attendanceId || screenSharing || !localStreamRef.current || recording) return;
    try {
      const displayStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
      const displayTrack = displayStream.getVideoTracks()[0];
      if (!displayTrack) return;
      displayTrack.onended = () => {
        stopScreenShare().catch(() => {});
      };

      const currentTrack = localStreamRef.current.getVideoTracks()[0] || null;
      if (currentTrack && currentTrack.id !== displayTrack.id) {
        localStreamRef.current.removeTrack(currentTrack);
      }
      localStreamRef.current.addTrack(displayTrack);
      await replaceTrackOnPeers("video", displayTrack);
      screenStreamRef.current = displayStream;
      setScreenSharing(true);
      syncLocalVideo();
    } catch {
      setNotice("Le partage d'écran a été annulé ou n'est pas disponible dans ce navigateur.");
    }
  }

  async function stopScreenShare() {
    if (!screenSharing || !localStreamRef.current) return;
    const screenTrack = localStreamRef.current.getVideoTracks()[0] || null;
    if (screenTrack && screenTrack !== cameraTrackRef.current) {
      localStreamRef.current.removeTrack(screenTrack);
    }

    const cameraTrack = cameraTrackRef.current;
    if (cameraTrack && cameraTrack.readyState !== "ended") {
      if (!localStreamRef.current.getVideoTracks().some((track) => track.id === cameraTrack.id)) {
        localStreamRef.current.addTrack(cameraTrack);
      }
      cameraTrack.enabled = cameraOn;
      await replaceTrackOnPeers("video", cameraTrack);
    } else {
      await replaceTrackOnPeers("video", null);
      setCameraOn(false);
    }

    screenStreamRef.current?.getTracks().forEach((track) => track.stop());
    screenStreamRef.current = null;
    setScreenSharing(false);
    syncLocalVideo();
  }

  async function toggleHand() {
    if (!attendanceId) return;
    const raised = !myHandRaised;
    setPeople((prev) =>
      prev.map((person) => (person.user_id === room?.user.id ? { ...person, hand_raised: raised } : person))
    );
    try {
      await api.post(`/sessions/${sessionId}/hand/`, { attendance_id: attendanceId, raised });
    } catch {
      setPeople((prev) =>
        prev.map((person) => (person.user_id === room?.user.id ? { ...person, hand_raised: !raised } : person))
      );
    }
  }

  async function sendChatMessage() {
    const text = chatInput.trim();
    if (!text || !room) return;
    const message: ChatMessage = {
      id: `local-${Date.now()}`,
      senderId: room.user.id,
      senderName: room.user.name,
      text,
      at: new Date().toISOString(),
      mine: true,
    };
    addMessage(message);
    setChatInput("");
    setSidebarTab("chat");
    setChatBusy(true);
    try {
      const recipients = people.filter((person) => person.user_id !== room.user.id);
      await Promise.allSettled(
        recipients.map((person) => sendSignal(person.user_id, "chat", { text, sent_at: message.at }))
      );
    } finally {
      setChatBusy(false);
    }
  }

  async function moderate(userId: number, action: ModerationAction) {
    if (!room?.is_organizer || userId === room.user.id) return;
    const label = action === "mute" ? "couper le microphone" : action === "camera_off" ? "couper la caméra" : "retirer ce participant";
    if (action === "remove" && !confirm(`Voulez-vous vraiment ${label} ?`)) return;
    try {
      await sendSignal(userId, "control", { action });
      setNotice(`Commande envoyée : ${label}.`);
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "La commande de modération a échoué.");
    }
  }

  async function uploadRoomFile(file: File) {
    if (!file || fileBusy) return;
    const formData = new FormData();
    formData.append("file", file);
    setFileBusy(true);
    setFileProgress(0);
    setSidebarTab("files");
    try {
      await apiUploadWithProgress<RoomFile>(
        `/sessions/${sessionId}/files/`,
        formData,
        (percent) => setFileProgress(percent)
      );
      await loadFiles();
      setNotice(`Fichier « ${file.name} » partagé.`);
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Impossible de partager ce fichier.");
    } finally {
      setFileBusy(false);
      setFileProgress(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function downloadRoomFile(item: RoomFile) {
    try {
      await apiDownload(item.download_path, item.name);
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Impossible de télécharger ce fichier.");
    }
  }

  const loadInvites = useCallback(async () => {
    if (!room?.is_organizer) return;
    try {
      const rows = await api.get<SessionInvite[]>(`/sessions/${sessionId}/invites/`);
      setInvites(rows);
    } catch {
      // Les invitations ne doivent pas interrompre la réunion en cas d'erreur réseau transitoire.
    }
  }, [room?.is_organizer, sessionId]);

  useEffect(() => {
    if (ready && room?.is_organizer) loadInvites();
  }, [ready, room?.is_organizer, loadInvites]);

  useEffect(() => {
    if (attendanceId && room?.is_organizer) loadInvites();
  }, [attendanceId, people.length, room?.is_organizer, loadInvites]);

  async function inviteGuestByEmail() {
    const email = inviteEmail.trim().toLowerCase();
    if (!email) {
      setNotice("Saisissez l'adresse email de l'apprenant à inviter.");
      return;
    }
    setInviteBusy(true);
    try {
      const created = await api.post<SessionInvite>(`/sessions/${sessionId}/invites/`, { email });
      setInvites((current) => [created, ...current.filter((item) => item.id !== created.id && item.email !== created.email)]);
      setInviteEmail("");
      setNotice(`Invitation envoyée à ${created.email}.`);
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Impossible d'envoyer l'invitation.");
    } finally {
      setInviteBusy(false);
    }
  }

  async function revokeInvite(inviteId: number) {
    try {
      const updated = await api.post<SessionInvite>(`/sessions/${sessionId}/invites/${inviteId}/revoke/`, {});
      setInvites((current) => current.map((item) => item.id === updated.id ? updated : item));
      setNotice("Invitation révoquée.");
    } catch (e) {
      setNotice(e instanceof ApiError ? e.message : "Impossible de révoquer l'invitation.");
    }
  }

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      const input = document.createElement("input");
      input.value = window.location.href;
      input.style.position = "fixed";
      input.style.opacity = "0";
      document.body.appendChild(input);
      input.select();
      const ok = document.execCommand("copy");
      input.remove();
      setCopied(ok);
      if (!ok) setNotice("Impossible de copier automatiquement le lien.");
      else window.setTimeout(() => setCopied(false), 1800);
    }
  }

  async function toggleFullscreen() {
    try {
      if (!document.fullscreenElement) {
        await stageRef.current?.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch {
      setNotice("Le mode plein écran n'est pas disponible.");
    }
  }

  function chooseRecordingMimeType() {
    const candidates = [
      "video/webm;codecs=vp9,opus",
      "video/webm;codecs=vp8,opus",
      "video/webm",
    ];
    return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
  }

  async function startRecording() {
    if (!room?.is_organizer || recording || !localStreamRef.current) return;
    if (typeof MediaRecorder === "undefined") {
      setNotice("L'enregistrement n'est pas pris en charge par ce navigateur.");
      return;
    }

    try {
      const canvas = document.createElement("canvas");
      canvas.width = 1280;
      canvas.height = 720;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("Canvas indisponible");

      const canvasStream = canvas.captureStream(30);
      const audioContext = new AudioContext();
      const audioDestination = audioContext.createMediaStreamDestination();
      const audioSources: MediaStream[] = [localStreamRef.current, ...remoteFeeds.map((feed) => feed.stream)];
      for (const sourceStream of audioSources) {
        if (sourceStream.getAudioTracks().length === 0) continue;
        try {
          audioContext.createMediaStreamSource(sourceStream).connect(audioDestination);
        } catch {
          // Flux audio non compatible : on continue avec les autres.
        }
      }
      audioDestination.stream.getAudioTracks().forEach((track) => canvasStream.addTrack(track));

      const draw = () => {
        context.fillStyle = "#030712";
        context.fillRect(0, 0, canvas.width, canvas.height);
        const videoElements = [
          localVideoRef.current,
          ...Array.from(remoteVideoElementsRef.current.values()),
        ].filter((video): video is HTMLVideoElement => Boolean(video && video.readyState >= 2));

        if (videoElements.length === 0) {
          context.fillStyle = "#ffffff";
          context.font = "32px sans-serif";
          context.textAlign = "center";
          context.fillText("LearnEas · séance en direct", canvas.width / 2, canvas.height / 2);
        } else {
          const columns = Math.ceil(Math.sqrt(videoElements.length));
          const rows = Math.ceil(videoElements.length / columns);
          const tileWidth = canvas.width / columns;
          const tileHeight = canvas.height / rows;
          videoElements.forEach((video, index) => {
            const col = index % columns;
            const row = Math.floor(index / columns);
            context.drawImage(video, col * tileWidth, row * tileHeight, tileWidth, tileHeight);
          });
        }
        recordingAnimationRef.current = window.requestAnimationFrame(draw);
      };
      draw();

      const mimeType = chooseRecordingMimeType();
      const recorder = new MediaRecorder(canvasStream, mimeType ? { mimeType } : undefined);
      recordingChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordingChunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        if (recordingAnimationRef.current !== null) {
          window.cancelAnimationFrame(recordingAnimationRef.current);
          recordingAnimationRef.current = null;
        }
        const blob = new Blob(recordingChunksRef.current, { type: recorder.mimeType || "video/webm" });
        if (blob.size > 0) {
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = url;
          anchor.download = `learneas-session-${sessionId}-${new Date().toISOString().replace(/[:.]/g, "-")}.webm`;
          document.body.appendChild(anchor);
          anchor.click();
          anchor.remove();
          URL.revokeObjectURL(url);
        }
        recordingChunksRef.current = [];
        recordingStreamRef.current?.getTracks().forEach((track) => track.stop());
        recordingStreamRef.current = null;
        recordingAudioContextRef.current?.close().catch(() => {});
        recordingAudioContextRef.current = null;
        recorderRef.current = null;
        setRecording(false);
      };

      recorderRef.current = recorder;
      recordingStreamRef.current = canvasStream;
      recordingAudioContextRef.current = audioContext;
      recorder.start(1000);
      setRecording(true);
      setNotice("Enregistrement local démarré. Le fichier sera téléchargé à l'arrêt.");
    } catch {
      setNotice("Impossible de démarrer l'enregistrement dans ce navigateur.");
    }
  }

  function stopRecording() {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
  }

  function updateCodeLanguage(language: CodeLanguage) {
    setCodeLanguage(language);
    const extensions: Record<CodeLanguage, string> = {
      javascript: "js", html: "html", css: "css", python: "py", java: "java", c: "c", cpp: "cpp", text: "txt",
    };
    const base = codeFileName.replace(/\.[^.]+$/, "") || "main";
    setCodeFileName(`${base}.${extensions[language]}`);
    setCodeOutput("");
  }

  function copyCode() {
    navigator.clipboard.writeText(codeText)
      .then(() => setNotice("Code copié dans le presse-papiers."))
      .catch(() => {
        const area = document.createElement("textarea");
        area.value = codeText;
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.select();
        const ok = document.execCommand("copy");
        area.remove();
        setNotice(ok ? "Code copié dans le presse-papiers." : "Copie automatique indisponible.");
      });
  }

  function downloadCode() {
    const blob = new Blob([codeText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = codeFileName || "code.txt";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  async function ensurePyodide() {
    if (pyodideRef.current) return pyodideRef.current;
    if (pyodideLoadPromiseRef.current) return pyodideLoadPromiseRef.current;

    pyodideLoadPromiseRef.current = new Promise<any>((resolve, reject) => {
      const w = window as any;
      const boot = async () => {
        try {
          const instance = await w.loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/",
          });
          pyodideRef.current = instance;
          resolve(instance);
        } catch (error) {
          pyodideLoadPromiseRef.current = null;
          reject(error);
        }
      };

      if (typeof w.loadPyodide === "function") {
        boot();
        return;
      }

      const existing = document.querySelector<HTMLScriptElement>('script[data-learneas-pyodide="true"]');
      if (existing) {
        existing.addEventListener("load", boot, { once: true });
        existing.addEventListener("error", () => reject(new Error("Chargement de Pyodide impossible.")), { once: true });
        return;
      }

      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js";
      script.async = true;
      script.dataset.learneasPyodide = "true";
      script.onload = boot;
      script.onerror = () => {
        pyodideLoadPromiseRef.current = null;
        reject(new Error("Chargement de Pyodide impossible."));
      };
      document.head.appendChild(script);
    });

    return pyodideLoadPromiseRef.current;
  }

  async function runCode() {
    if (codeRunning) return;
    setCodeRunning(true);
    setCodeOutput("");
    const nonce = ++codeRunNonceRef.current;

    if (codeLanguage === "html") {
      setCodeOutput("Aperçu HTML actualisé dans le panneau de résultat.");
      setCodeRunning(false);
      return;
    }

    if (codeLanguage === "css") {
      setCodeOutput("Aperçu CSS actualisé dans le panneau de résultat.");
      setCodeRunning(false);
      return;
    }

    if (codeLanguage === "python") {
      try {
        setCodeOutput("Chargement du moteur Python…");
        const pyodide = await ensurePyodide();
        let captured = "";
        pyodide.setStdout({ batched: (text: string) => { captured += `${text}\n`; } });
        pyodide.setStderr({ batched: (text: string) => { captured += `Erreur: ${text}\n`; } });
        const result = await pyodide.runPythonAsync(codeText);
        if (result !== undefined && result !== null && String(result) !== "None") {
          captured += `${String(result)}\n`;
        }
        setCodeOutput(captured.trim() || "Exécution Python terminée sans sortie.");
      } catch (error) {
        setCodeOutput(`Erreur Python: ${error instanceof Error ? error.message : String(error)}`);
      } finally {
        setCodeRunning(false);
      }
      return;
    }

    if (codeLanguage !== "javascript") {
      setCodeOutput(`L'exécution locale n'est pas disponible pour ${codeLanguage}. Utilisez JavaScript, Python, HTML ou CSS.`);
      setCodeRunning(false);
      return;
    }

    const escaped = JSON.stringify(codeText);
    const srcDoc = `<!doctype html><html><body><script>
      const out=[];
      const fmt=(v)=>typeof v==='string'?v:JSON.stringify(v);
      console.log=(...a)=>out.push(a.map(fmt).join(' '));
      console.error=(...a)=>out.push('Erreur: '+a.map(fmt).join(' '));
      try { (0,eval)(${escaped}); } catch(e) { out.push('Erreur: '+(e && e.stack ? e.stack : e)); }
      parent.postMessage({source:'learneas-code-runner',nonce:${nonce},output:out.join('\\n') || 'Exécution terminée sans sortie console.'}, '*');
    <\/script></body></html>`;
    if (codeRunnerRef.current) codeRunnerRef.current.srcdoc = srcDoc;
  }


  const elapsedLabel = useMemo(() => {
    const anchor = room?.started_at || room?.scheduled_at;
    if (!anchor) return "00:00";
    const end = room?.completed && room?.ended_at ? new Date(room.ended_at).getTime() : clockNow;
    const start = new Date(anchor).getTime();
    const diff = Math.max(Math.floor((end - start) / 1000), 0);
    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    const seconds = diff % 60;
    if (hours > 0) {
      return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    }
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }, [room?.started_at, room?.scheduled_at, room?.completed, room?.ended_at, clockNow]);

  if (!ready || (!room && !error)) return <GuardScreen />;
  if (error && !room) {
    return <div className="container-app py-20 text-center text-red-600">{error}</div>;
  }
  if (!room) return null;

  return (
    <div className="fixed inset-0 z-[100] h-[100dvh] overflow-hidden bg-gray-950 text-white">
      <div className="mx-auto flex h-full max-w-[1820px] flex-col px-2.5 py-2.5 sm:px-4">
        <div className="mb-2 shrink-0 flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2.5">
            {room.organizer.avatar ? <img src={room.organizer.avatar} alt="" className="h-8 w-8 shrink-0 rounded-full object-cover ring-1 ring-white/10" /> : <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-500/15 text-[11px] font-bold text-brand-200">{room.organizer.name.charAt(0).toUpperCase()}</span>}
            <div className="min-w-0">
              <p className="text-[9px] font-semibold uppercase tracking-[0.16em] text-brand-300">Salle LearnEas · Séance {room.session_number} · {room.organizer.name}</p>
              <h1 className="truncate text-base font-bold sm:text-lg">{room.title}</h1>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1 overflow-x-auto">
            <button type="button" onClick={() => setMetricsCollapsed((value) => !value)} className="toolbar-secondary !px-2 !py-1.5 !text-[10px]">
              {metricsCollapsed ? <ChevronDown size={13} /> : <ChevronUp size={13} />} Indicateurs
            </button>
            <button type="button" onClick={() => setSidebarCollapsed((value) => !value)} className="toolbar-secondary !px-2 !py-1.5 !text-[10px]">
              {sidebarCollapsed ? <PanelRightOpen size={13} /> : <PanelRightClose size={13} />} Panneau
            </button>
            <button
              type="button"
              onClick={() => {
                const next = !focusMode;
                setFocusMode(next);
                setMetricsCollapsed(next);
                setSidebarCollapsed(next);
              }}
              className={focusMode ? "toolbar-success !px-2 !py-1.5 !text-[10px]" : "toolbar-secondary !px-2 !py-1.5 !text-[10px]"}
            >
              <Maximize2 size={13} /> Focus
            </button>
            <button type="button" onClick={copyLink} className="toolbar-secondary !px-2 !py-1.5 !text-[10px]">
              <Copy size={13} /> {copied ? "Copié" : "Lien"}
            </button>
            {room.is_organizer && attendanceId && (
              <button
                type="button"
                onClick={recording ? stopRecording : startRecording}
                className={recording ? "toolbar-danger !px-2 !py-1.5 !text-[10px]" : "toolbar-secondary !px-2 !py-1.5 !text-[10px]"}
              >
                <span className={`h-2 w-2 rounded-full ${recording ? "animate-pulse bg-white" : "bg-red-500"}`} />
                {recording ? "Stop rec" : "Enregistrer"}
              </button>
            )}
            {room.is_organizer && !room.started_at && !room.completed && (
              <button type="button" onClick={startSession} disabled={actionBusy} className="toolbar-success !px-2 !py-1.5 !text-[10px]">
                <PlayCircle size={13} /> Démarrer
              </button>
            )}
            {room.is_organizer && room.started_at && !room.completed && (
              <button type="button" onClick={endSession} disabled={actionBusy} className="toolbar-danger !px-2 !py-1.5 !text-[10px]">
                <StopCircle size={13} /> Terminer
              </button>
            )}
          </div>
        </div>

        {notice && (
          <div className="mb-2.5 flex items-start justify-between gap-2 rounded-2xl border border-brand-400/20 bg-brand-400/10 px-3 py-2 text-[11px] text-brand-100 sm:text-xs">
            <span>{notice}</span>
            <button onClick={() => setNotice("")} className="text-xs font-semibold text-white/70 hover:text-white">Fermer</button>
          </div>
        )}

        {!metricsCollapsed && (
          <div className="mb-2 shrink-0 grid grid-cols-5 gap-1.5">
            <InfoCard icon={<Users size={13} />} label="Participants" value={`${participantsCount}`} />
            <InfoCard icon={<Hand size={13} />} label="Mains" value={`${raisedHandsCount}`} />
            <InfoCard icon={<StopCircle size={13} />} label="Live" value={elapsedLabel} />
            <InfoCard icon={<Monitor size={13} />} label="Planifié" value={`${room.planned_duration_minutes} min`} />
            <InfoCard icon={<FileText size={13} />} label="Fichiers" value={`${files.length}`} />
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto pb-16 xl:overflow-hidden">
        {!attendanceId ? (
          <div className="mx-auto mt-8 max-w-md rounded-3xl border border-white/10 bg-white/5 p-5 text-center shadow-2xl">
            <ShieldCheck size={34} className="mx-auto mb-3 text-brand-300" />
            <h2 className="text-lg font-bold">Prêt à rejoindre la séance ?</h2>
            <p className="mt-2 text-xs text-gray-400 sm:text-sm">
              Votre présence et votre temps de connexion seront enregistrés pour le suivi de la formation.
            </p>
            {room.completed ? (
              <p className="mt-4 text-xs text-gray-400 sm:text-sm">Cette séance est terminée.</p>
            ) : !room.is_organizer && !room.started_at ? (
              <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-3">
                <p className="text-xs text-gray-300 sm:text-sm">La séance n&apos;a pas encore été démarrée par l&apos;organisateur.</p>
                <p className="mt-1 text-xs text-gray-500">Cette page se met à jour automatiquement.</p>
              </div>
            ) : (
              <button onClick={enterRoom} disabled={joining} className="mt-5 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700">
                {joining ? <Loader2 className="mr-2 inline animate-spin" size={18} /> : <Video className="mr-2 inline" size={18} />}
                Entrer dans la salle
              </button>
            )}
            {room.is_organizer && (
              <div className="mx-auto mt-4 max-w-sm border-t border-white/10 pt-4 text-left">
                <p className="mb-2 text-[11px] font-semibold text-gray-300">Inviter un apprenant par email</p>
                <div className="flex gap-2">
                  <input type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="email@exemple.com" className="min-w-0 flex-1 rounded-lg border border-white/10 bg-gray-950 px-3 py-2 text-xs text-white outline-none focus:border-brand-400" />
                  <button onClick={inviteGuestByEmail} disabled={inviteBusy || !inviteEmail.trim()} className="rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">
                    {inviteBusy ? <Loader2 size={13} className="animate-spin" /> : "Inviter"}
                  </button>
                </div>
              </div>
            )}
            {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
          </div>
        ) : (
          <>
            <div className={sidebarCollapsed ? "grid h-full min-h-0 grid-cols-1 gap-2" : "grid h-full min-h-0 gap-2 xl:grid-cols-[minmax(0,1fr)_300px]"}>
              <div ref={stageRef} className="h-full min-h-0 rounded-3xl bg-gray-950">
                {workspaceMode === "code" ? (
                  <CodeWorkspace
                    language={codeLanguage}
                    fileName={codeFileName}
                    code={codeText}
                    output={codeOutput}
                    running={codeRunning}
                    runnerRef={codeRunnerRef}
                    onLanguageChange={updateCodeLanguage}
                    onFileNameChange={setCodeFileName}
                    onCodeChange={setCodeText}
                    onRun={runCode}
                    onCopy={copyCode}
                    onDownload={downloadCode}
                    onBackToVideo={() => setWorkspaceMode("video")}
                  />
                ) : workspaceMode === "whiteboard" ? (
                  <WhiteboardWorkspace
                    strokes={whiteboardStrokes}
                    onChange={updateWhiteboard}
                    onBackToVideo={() => setWorkspaceMode("video")}
                  />
                ) : (
                  <div className="flex h-full min-h-0 flex-col rounded-3xl border border-white/10 bg-white/5 p-2.5">
                    <div className="mb-2.5 flex shrink-0 flex-wrap items-center justify-between gap-2.5">
                      <div>
                        <h2 className="text-sm font-semibold">Scène de la session</h2>
                        <p className="text-[11px] text-gray-400 sm:text-xs">
                          {screenSharing ? "Votre écran est visible par les participants." : "Vue vidéo de la séance en temps réel."}
                        </p>
                      </div>
                      <button onClick={toggleFullscreen} className="toolbar-secondary !px-2 !py-1.5 !text-[10px]">
                        <Maximize2 size={15} /> {fullscreen ? "Quitter le plein écran" : "Plein écran"}
                      </button>
                    </div>

                    <div className={remoteFeeds.length === 0 ? "grid min-h-0 flex-1 grid-cols-1 gap-2.5 overflow-y-auto lg:grid-cols-[minmax(230px,340px)_minmax(0,1fr)]" : "grid min-h-0 flex-1 grid-cols-1 gap-2.5 overflow-y-auto lg:grid-cols-2 2xl:grid-cols-3"}>
                      <VideoTile
                        title="Vous"
                        subtitle={screenSharing ? "Partage d'écran" : room.is_organizer ? "Organisateur" : "Participant"}
                        videoRef={localVideoRef}
                        muted
                        footer={screenSharing ? "Écran partagé" : cameraOn ? "Caméra active" : "Caméra coupée"}
                        handRaised={myHandRaised}
                        avatar={room.user.avatar}
                        videoEnabled={screenSharing || cameraOn}
                      />
                      {remoteFeeds.map((feed) => (
                        <RemoteVideo
                          key={feed.userId}
                          feed={feed}
                          handRaised={Boolean(people.find((person) => person.user_id === feed.userId)?.hand_raised)}
                          avatar={people.find((person) => person.user_id === feed.userId)?.avatar || null}
                          onElement={(element) => {
                            if (element) remoteVideoElementsRef.current.set(feed.userId, element);
                            else remoteVideoElementsRef.current.delete(feed.userId);
                          }}
                        />
                      ))}
                      {remoteFeeds.length === 0 && (
                        <div className="grid min-h-[160px] place-items-center rounded-3xl border border-dashed border-white/10 bg-gray-900/80 p-4 text-center text-[11px] text-gray-500 sm:text-xs">
                          <div>
                            <Users size={28} className="mx-auto mb-2" />
                            <p className="font-medium text-gray-300">En attente des autres participants...</p>
                            <p className="mt-1 text-xs text-gray-500">Les flux distants apparaîtront ici automatiquement.</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {!sidebarCollapsed && (
              <aside className="flex h-full min-h-0 flex-col overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-2.5">
                <div className="mb-2.5 grid grid-cols-3 gap-1 rounded-2xl bg-black/20 p-1">
                  <SidebarButton active={sidebarTab === "participants"} onClick={() => setSidebarTab("participants")}>Participants</SidebarButton>
                  <SidebarButton active={sidebarTab === "chat"} onClick={() => setSidebarTab("chat")}>Chat</SidebarButton>
                  <SidebarButton active={sidebarTab === "files"} onClick={() => setSidebarTab("files")}>Fichiers</SidebarButton>
                </div>

                {sidebarTab === "participants" && (
                  <div className="min-h-0 flex-1 overflow-y-auto pr-1">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="font-semibold">Présences actives</h3>
                      <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-gray-300">{participantsCount} en ligne</span>
                    </div>
                    {room.is_organizer && (
                      <div className="mb-3 rounded-2xl border border-brand-400/20 bg-brand-400/5 p-2.5">
                        <div className="mb-2 flex items-center gap-2">
                          <UserPlus size={14} className="text-brand-300" />
                          <p className="text-xs font-semibold text-white">Inviter un apprenant non inscrit</p>
                        </div>
                        <div className="flex gap-1.5">
                          <input
                            type="email"
                            value={inviteEmail}
                            onChange={(event) => setInviteEmail(event.target.value)}
                            onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); inviteGuestByEmail(); } }}
                            placeholder="email@exemple.com"
                            className="min-w-0 flex-1 rounded-lg border border-white/10 bg-gray-950 px-2.5 py-1.5 text-[11px] text-white outline-none placeholder:text-gray-600 focus:border-brand-400"
                          />
                          <button
                            onClick={inviteGuestByEmail}
                            disabled={inviteBusy || !inviteEmail.trim()}
                            className="rounded-lg bg-brand-600 px-2.5 py-1.5 text-[10px] font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
                          >
                            {inviteBusy ? <Loader2 size={12} className="animate-spin" /> : "Inviter"}
                          </button>
                        </div>
                        {invites.length > 0 && (
                          <div className="mt-2 max-h-28 space-y-1 overflow-y-auto">
                            {invites.slice(0, 8).map((invite) => (
                              <div key={invite.id} className="flex items-center justify-between gap-2 rounded-lg bg-black/20 px-2 py-1.5">
                                <div className="min-w-0">
                                  <p className="truncate text-[10px] font-medium text-gray-200">{invite.email}</p>
                                  <p className="text-[9px] text-gray-500">{inviteStatusLabel(invite.status)}</p>
                                </div>
                                {invite.status !== "revoked" && (
                                  <button onClick={() => revokeInvite(invite.id)} className="shrink-0 text-[9px] font-semibold text-red-300 hover:text-red-200">Révoquer</button>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                    <div className="space-y-2">
                      {people.map((person) => (
                        <div key={person.user_id} className={`rounded-2xl border px-2.5 py-2 ${person.hand_raised ? "border-amber-400/40 bg-amber-400/10" : "border-white/10 bg-black/20"}`}>
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex min-w-0 items-center gap-2">
                              {person.avatar ? <img src={person.avatar} alt="" className="h-8 w-8 shrink-0 rounded-full object-cover" /> : <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-500/15 text-[11px] font-bold text-brand-200">{person.name.charAt(0).toUpperCase()}</span>}
                              <div className="min-w-0">
                                <div className="flex items-center gap-2"><p className="truncate text-xs font-medium text-white">{person.name}</p>{person.hand_raised && <Hand size={13} className="shrink-0 text-amber-300" />}</div>
                                <p className="text-[10px] text-gray-400">{person.role === "organizer" ? "Organisateur" : person.role === "admin" ? "Administrateur" : person.role === "guest" ? "Invité" : "Participant"}</p>
                              </div>
                            </div>
                            <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-400" />
                          </div>
                          {room.is_organizer && person.user_id !== room.user.id && (
                            <div className="mt-2 flex flex-wrap gap-1 border-t border-white/10 pt-2">
                              <MiniAction onClick={() => moderate(person.user_id, "mute")}>Couper micro</MiniAction>
                              <MiniAction onClick={() => moderate(person.user_id, "camera_off")}>Couper caméra</MiniAction>
                              <MiniAction danger onClick={() => moderate(person.user_id, "remove")}>Retirer</MiniAction>
                            </div>
                          )}
                        </div>
                      ))}
                      {people.length === 0 && <EmptyPanel>Les participants actifs apparaîtront ici.</EmptyPanel>}
                    </div>
                  </div>
                )}

                {sidebarTab === "chat" && (
                  <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="font-semibold">Messagerie de séance</h3>
                      <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-gray-300">{messages.length}</span>
                    </div>
                    <div className="flex-1 space-y-2.5 overflow-y-auto rounded-2xl border border-white/10 bg-black/20 p-2.5">
                      {messages.length === 0 ? (
                        <div className="grid min-h-[210px] place-items-center text-center text-xs text-gray-500 sm:text-sm">
                          <div>
                            <MessageSquare className="mx-auto mb-2" size={24} />
                            <p>Aucun message pour le moment.</p>
                            <p className="mt-1 text-xs text-gray-600">Posez une question ou partagez une information.</p>
                          </div>
                        </div>
                      ) : (
                        messages.map((message) => (
                          <div key={message.id} className={`max-w-[92%] rounded-2xl px-2.5 py-2 text-[11px] sm:text-xs ${message.mine ? "ml-auto bg-brand-600 text-white" : "bg-white/10 text-gray-100"}`}>
                            <div className="mb-1 flex items-center justify-between gap-4 text-[11px] opacity-80">
                              <span className="font-semibold">{message.mine ? "Vous" : message.senderName}</span>
                              <span>{new Date(message.at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}</span>
                            </div>
                            <p className="whitespace-pre-wrap leading-[18px]">{message.text}</p>
                          </div>
                        ))
                      )}
                      <div ref={chatEndRef} />
                    </div>
                    <div className="mt-2.5 rounded-2xl border border-white/10 bg-black/20 p-2">
                      <textarea
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            sendChatMessage();
                          }
                        }}
                        rows={2}
                        maxLength={2000}
                        placeholder="Écrire un message aux participants..."
                        className="w-full rounded-xl border border-white/10 bg-white/5 px-2.5 py-1.5 text-[11px] text-white placeholder:text-gray-500 focus:border-brand-400 focus:outline-none sm:text-xs"
                      />
                      <div className="mt-3 flex items-center justify-between gap-2">
                        <span className="text-[11px] text-gray-500">{chatInput.length}/2000</span>
                        <button onClick={sendChatMessage} disabled={chatBusy || !chatInput.trim()} className="rounded-xl bg-brand-600 px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60 sm:text-xs">
                          {chatBusy ? <Loader2 className="mr-2 inline animate-spin" size={16} /> : null}Envoyer
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {sidebarTab === "files" && (
                  <div className="min-h-0 flex-1 overflow-y-auto pr-1">
                    <div className="mb-3 flex items-center justify-between gap-2.5">
                      <div>
                        <h3 className="font-semibold">Fichiers de la séance</h3>
                        <p className="text-xs text-gray-500">20 Mo maximum par fichier.</p>
                      </div>
                      <button onClick={() => fileInputRef.current?.click()} disabled={fileBusy} className="toolbar-secondary !px-2 !py-1.5 !text-[10px]">
                        {fileBusy ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />} Partager
                      </button>
                      <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        onChange={(event) => {
                          const file = event.target.files?.[0];
                          if (file) uploadRoomFile(file);
                        }}
                      />
                    </div>
                    {fileProgress !== null && (
                      <div className="mb-3 rounded-2xl border border-brand-400/20 bg-brand-400/10 p-2.5">
                        <div className="mb-2 flex items-center justify-between text-xs text-brand-100"><span>Envoi en cours</span><span>{fileProgress}%</span></div>
                        <div className="h-2 overflow-hidden rounded-full bg-black/30"><div className="h-full rounded-full bg-brand-400 transition-all" style={{ width: `${fileProgress}%` }} /></div>
                      </div>
                    )}
                    <div className="space-y-2">
                      {files.map((item) => (
                        <div key={item.id} className="rounded-2xl border border-white/10 bg-black/20 p-2.5">
                          <div className="flex items-start gap-3">
                            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white/10 text-brand-200"><FileText size={18} /></div>
                            <div className="min-w-0 flex-1">
                              <p className="break-words text-xs font-semibold text-white sm:text-sm">{item.name}</p>
                              <p className="mt-1 text-xs text-gray-500">{formatBytes(item.size)} · {item.uploader_name}</p>
                              <p className="mt-1 text-[11px] text-gray-600">{new Date(item.uploaded_at).toLocaleString("fr-FR")}</p>
                            </div>
                          </div>
                          <button onClick={() => downloadRoomFile(item)} className="mt-2.5 inline-flex items-center gap-1.5 text-[11px] font-semibold text-brand-200 hover:text-white"><Download size={14} /> Télécharger</button>
                        </div>
                      ))}
                      {files.length === 0 && <EmptyPanel>Aucun fichier partagé dans cette séance.</EmptyPanel>}
                    </div>
                  </div>
                )}
              </aside>
              )}
            </div>

            {devicePanelOpen && (
              <div className="fixed bottom-20 left-1/2 z-30 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 rounded-3xl border border-white/10 bg-gray-900/95 p-3.5 shadow-2xl backdrop-blur">
                <div className="mb-3 flex items-center justify-between">
                  <div><h3 className="font-semibold">Périphériques audio et vidéo</h3><p className="text-xs text-gray-400">Le changement est appliqué sans quitter la salle.</p></div>
                  <button onClick={() => setDevicePanelOpen(false)} className="text-xs font-semibold text-gray-400 hover:text-white">Fermer</button>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="text-xs font-semibold text-gray-300">Microphone
                    <select value={selectedAudioInput} onChange={(e) => switchAudioDevice(e.target.value)} disabled={recording} className="mt-1.5 w-full rounded-xl border border-white/10 bg-gray-950 px-2.5 py-1.5 text-[11px] text-white sm:text-xs">
                      {audioInputs.map((device) => <option key={device.deviceId} value={device.deviceId}>{device.label}</option>)}
                    </select>
                  </label>
                  <label className="text-xs font-semibold text-gray-300">Caméra
                    <select value={selectedVideoInput} onChange={(e) => switchVideoDevice(e.target.value)} disabled={recording} className="mt-1.5 w-full rounded-xl border border-white/10 bg-gray-950 px-2.5 py-1.5 text-[11px] text-white sm:text-xs">
                      {videoInputs.map((device) => <option key={device.deviceId} value={device.deviceId}>{device.label}</option>)}
                    </select>
                  </label>
                </div>
                {recording && <p className="mt-3 text-xs text-amber-300">Arrêtez l'enregistrement avant de changer de périphérique.</p>}
              </div>
            )}

            <div className={`fixed bottom-2 left-1/2 z-20 flex max-w-[calc(100%-1rem)] -translate-x-1/2 flex-nowrap items-center justify-center gap-1 overflow-x-auto whitespace-nowrap rounded-2xl border border-white/10 bg-gray-900/95 shadow-2xl backdrop-blur pointer-events-auto ${controlsCompact ? "px-1.5 py-1" : "w-auto lg:min-w-[980px] max-w-[1600px] px-2.5 py-1.5"}`}>
              <button type="button" onClick={() => setControlsCompact((value) => !value)} className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white/10 text-gray-200 hover:bg-white/15" title={controlsCompact ? "Déployer les contrôles" : "Réduire les contrôles"}>{controlsCompact ? <ChevronsRight size={14} /> : <ChevronsLeft size={14} />}</button>
              <ControlButton compact={controlsCompact} active={micOn} onClick={toggleMic} label={micOn ? "Micro" : "Micro coupé"}>{micOn ? <Mic size={15} /> : <MicOff size={15} />}</ControlButton>
              <ControlButton compact={controlsCompact} active={cameraOn && !screenSharing} onClick={() => void toggleCamera()} disabled={screenSharing} label={screenSharing ? "Caméra verrouillée pendant le partage" : cameraOn ? "Caméra" : "Caméra coupée"}>{cameraOn ? <Video size={15} /> : <VideoOff size={15} />}</ControlButton>
              <ControlButton compact={controlsCompact} active={screenSharing} onClick={screenSharing ? () => stopScreenShare() : () => startScreenShare()} disabled={recording} label={screenSharing ? "Arrêter le partage" : "Partager l'écran"}>{screenSharing ? <ScreenShareOff size={15} /> : <ScreenShare size={15} />}</ControlButton>
              <ControlButton compact={controlsCompact} active={myHandRaised} onClick={toggleHand} label={myHandRaised ? "Baisser la main" : "Lever la main"}><Hand size={15} /></ControlButton>
              <ControlButton compact={controlsCompact} active={devicePanelOpen} onClick={() => { refreshDevices(); setDevicePanelOpen((value) => !value); }} label="Périphériques"><Settings size={15} /></ControlButton>
              <ControlButton compact={controlsCompact} active={workspaceMode === "code"} onClick={() => setWorkspaceMode(workspaceMode === "code" ? "video" : "code")} label={workspaceMode === "code" ? "Vidéo" : "Code"}><Code2 size={15} /></ControlButton>
              <ControlButton compact={controlsCompact} active={workspaceMode === "whiteboard"} onClick={() => setWorkspaceMode(workspaceMode === "whiteboard" ? "video" : "whiteboard")} label={workspaceMode === "whiteboard" ? "Vidéo" : "Tableau blanc"}><PenLine size={15} /></ControlButton>
              <ControlButton compact={controlsCompact} active={sidebarTab === "chat"} onClick={() => setSidebarTab(sidebarTab === "chat" ? "participants" : "chat")} label="Chat"><MessageSquare size={15} /></ControlButton>
              <button type="button" onClick={() => leaveRoom(false)} className={`inline-flex shrink-0 items-center rounded-xl bg-red-600 font-semibold text-white hover:bg-red-500 ${controlsCompact ? "h-8 w-8 justify-center p-0" : "gap-1.5 px-2.5 py-1.5 text-[11px]"}`} title="Quitter"><PhoneOff size={15} /> {!controlsCompact && <span>Quitter</span>}</button>
            </div>
          </>
        )}
        </div>
      </div>
    </div>
  );
}

function CodeWorkspace({
  language,
  fileName,
  code,
  output,
  running,
  runnerRef,
  onLanguageChange,
  onFileNameChange,
  onCodeChange,
  onRun,
  onCopy,
  onDownload,
  onBackToVideo,
}: {
  language: CodeLanguage;
  fileName: string;
  code: string;
  output: string;
  running: boolean;
  runnerRef: React.RefObject<HTMLIFrameElement>;
  onLanguageChange: (language: CodeLanguage) => void;
  onFileNameChange: (value: string) => void;
  onCodeChange: (value: string) => void;
  onRun: () => void;
  onCopy: () => void;
  onDownload: () => void;
  onBackToVideo: () => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const editorGridRef = useRef<HTMLDivElement | null>(null);
  const draggingRef = useRef(false);
  const [scrollTop, setScrollTop] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [consoleCollapsed, setConsoleCollapsed] = useState(false);
  const [consolePercent, setConsolePercent] = useState(30);
  const [theme, setTheme] = useState<CodeTheme>("midnight");
  const canRun = ["javascript", "python", "html", "css"].includes(language);
  const lineNumbers = useMemo(() => Array.from({ length: Math.max(code.split("\n").length, 1) }, (_, index) => index + 1), [code]);
  const palette = codeThemePalette(theme);
  const highlighted = useMemo(() => highlightCode(code, language, theme), [code, language, theme]);

  function handleEditorKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Tab") return;
    event.preventDefault();
    const element = event.currentTarget;
    const start = element.selectionStart;
    const end = element.selectionEnd;
    onCodeChange(`${code.slice(0, start)}  ${code.slice(end)}`);
    window.requestAnimationFrame(() => textareaRef.current?.setSelectionRange(start + 2, start + 2));
  }

  function resizeConsoleFromPointer(clientX: number) {
    const rect = editorGridRef.current?.getBoundingClientRect();
    if (!rect || rect.width <= 0) return;
    const percent = 100 - ((clientX - rect.left) / rect.width) * 100;
    setConsolePercent(Math.min(Math.max(percent, 18), 62));
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#0b1020]">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-1.5 border-b border-white/10 px-2.5 py-1.5">
        <div className="flex min-w-0 items-center gap-2">
          <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-brand-500/15 text-brand-200"><Code2 size={15} /></div>
          <div className="min-w-0"><h2 className="truncate text-xs font-semibold text-white">Éditeur partagé</h2><p className="text-[9px] text-gray-500">Coloration syntaxique et synchronisation en direct.</p></div>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <button type="button" onClick={onBackToVideo} className="toolbar-secondary !px-2 !py-1 !text-[10px]"><Video size={13} /> Vidéo</button>
          <button type="button" onClick={onCopy} className="toolbar-secondary !px-2 !py-1 !text-[10px]"><Copy size={13} /> Copier</button>
          <button type="button" onClick={onDownload} className="toolbar-secondary !px-2 !py-1 !text-[10px]"><Download size={13} /> Télécharger</button>
          <button type="button" onClick={() => setConsoleCollapsed((value) => !value)} className="toolbar-secondary !px-2 !py-1 !text-[10px]">{consoleCollapsed ? <PanelRightOpen size={12} /> : <PanelRightClose size={12} />} Console</button>
          <button type="button" onClick={onRun} disabled={running || !canRun} title={canRun ? "Exécuter le code" : "Exécution locale disponible pour JavaScript, Python, HTML et CSS"} className="toolbar-success !px-2 !py-1 !text-[10px] disabled:cursor-not-allowed disabled:opacity-45">{running ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />} {running ? "Exécution…" : "Exécuter"}</button>
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-1.5 border-b border-white/10 bg-black/15 px-2.5 py-1.5">
        <label className="flex items-center gap-1 text-[10px] text-gray-400">Langage<select value={language} onChange={(event) => onLanguageChange(event.target.value as CodeLanguage)} className="rounded-lg border border-white/10 bg-gray-950 px-2 py-1 text-[11px] text-white outline-none focus:border-brand-400"><option value="javascript">JavaScript</option><option value="html">HTML</option><option value="css">CSS</option><option value="python">Python</option><option value="java">Java</option><option value="c">C</option><option value="cpp">C++</option><option value="text">Texte</option></select></label>
        <label className="flex items-center gap-1 text-[10px] text-gray-400">Thème<select value={theme} onChange={(event) => setTheme(event.target.value as CodeTheme)} className="rounded-lg border border-white/10 bg-gray-950 px-2 py-1 text-[11px] text-white outline-none focus:border-brand-400"><option value="midnight">Midnight</option><option value="dracula">Dracula</option><option value="light">Clair</option></select></label>
        <label className="flex min-w-0 flex-1 items-center gap-1 text-[10px] text-gray-400">Fichier<input value={fileName} onChange={(event) => onFileNameChange(event.target.value.slice(0, 80))} className="min-w-[110px] max-w-xs flex-1 rounded-lg border border-white/10 bg-gray-950 px-2 py-1 font-mono text-[11px] text-white outline-none focus:border-brand-400" /></label>
        <span className="rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-300">Live</span>
      </div>

      <div ref={editorGridRef} className="grid min-h-0 flex-1" style={{ gridTemplateColumns: consoleCollapsed ? "minmax(0,1fr)" : `minmax(0, ${100 - consolePercent}fr) 5px minmax(190px, ${consolePercent}fr)` }}>
        <div className="relative min-h-0 overflow-hidden border-r border-white/10 font-mono text-[12px] leading-5" style={{ background: palette.background }}>
          <div className="absolute inset-y-0 left-0 z-20 w-10 overflow-hidden border-r border-white/10 bg-black/15 text-right" style={{ color: palette.lineNumber }} aria-hidden="true"><div style={{ transform: `translateY(-${scrollTop}px)` }} className="py-2.5 pr-2">{lineNumbers.map((line) => <div key={line} className="h-5 select-none">{line}</div>)}</div></div>
          <pre aria-hidden="true" className="pointer-events-none absolute inset-0 m-0 overflow-hidden whitespace-pre py-2.5 pl-12 pr-3 font-mono text-[12px] leading-5" style={{ color: palette.text }}><code style={{ display: "block", transform: `translate(${-scrollLeft}px, ${-scrollTop}px)` }} dangerouslySetInnerHTML={{ __html: highlighted }} /></pre>
          <textarea ref={textareaRef} value={code} onChange={(event) => onCodeChange(event.target.value.slice(0, 100000))} maxLength={100000} onKeyDown={handleEditorKeyDown} onScroll={(event) => { setScrollTop(event.currentTarget.scrollTop); setScrollLeft(event.currentTarget.scrollLeft); }} spellCheck={false} autoCapitalize="off" autoCorrect="off" className="absolute inset-0 z-10 h-full w-full resize-none overflow-auto bg-transparent py-2.5 pl-12 pr-3 font-mono text-[12px] leading-5 text-transparent outline-none selection:bg-brand-500/25" style={{ caretColor: theme === "light" ? "#0f172a" : "#ffffff" }} aria-label="Éditeur de code LearnEas" />
        </div>

        {!consoleCollapsed && <>
          <div role="separator" aria-label="Redimensionner la console" aria-orientation="vertical" className="cursor-col-resize bg-white/5 transition hover:bg-brand-500/50" onPointerDown={(event) => { draggingRef.current = true; event.currentTarget.setPointerCapture(event.pointerId); }} onPointerMove={(event) => { if (draggingRef.current) resizeConsoleFromPointer(event.clientX); }} onPointerUp={(event) => { draggingRef.current = false; event.currentTarget.releasePointerCapture(event.pointerId); }} onPointerCancel={() => { draggingRef.current = false; }} />
          <div className="flex min-h-0 flex-col bg-[#0a0f1b]">
            <div className="flex shrink-0 items-center justify-between border-b border-white/10 px-2.5 py-1.5"><p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Résultat / Console</p><div className="flex items-center gap-1"><button type="button" onClick={() => setConsolePercent((value) => Math.max(value - 10, 18))} className="rounded-md bg-white/5 p-1 text-gray-300 hover:bg-white/10" title="Réduire la console"><Minus size={11} /></button><button type="button" onClick={() => setConsolePercent((value) => Math.min(value + 10, 62))} className="rounded-md bg-white/5 p-1 text-gray-300 hover:bg-white/10" title="Agrandir la console"><Plus size={11} /></button></div></div>
            {language === "html" ? <iframe title="Aperçu HTML" sandbox="allow-scripts" srcDoc={code} className="min-h-0 flex-1 bg-white" /> : language === "css" ? <iframe title="Aperçu CSS" sandbox="allow-scripts" srcDoc={`<!doctype html><html><head><style>${code}</style></head><body><main class="demo"><h1>Aperçu CSS</h1><p>Modifiez les styles pour voir le résultat.</p><button>Exemple de bouton</button></main></body></html>`} className="min-h-0 flex-1 bg-white" /> : <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap break-words p-2.5 font-mono text-[11px] leading-[18px] text-gray-300">{output || (language === "python" ? "Cliquez sur Exécuter. Le moteur Python sera chargé au premier lancement." : language === "javascript" ? "Cliquez sur Exécuter pour afficher la console." : "Ce langage reste éditable et partageable, mais son exécution locale est désactivée.")}</pre>}
          </div>
        </>}
      </div>
      <iframe ref={runnerRef} title="Exécution JavaScript sécurisée" sandbox="allow-scripts" className="hidden" />
    </div>
  );
}

function WhiteboardWorkspace({ strokes, onChange, onBackToVideo }: { strokes: WhiteboardStroke[]; onChange: (strokes: WhiteboardStroke[]) => void; onBackToVideo: () => void; }) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const activeStrokeRef = useRef<string | null>(null);
  const strokesRef = useRef<WhiteboardStroke[]>(strokes);
  const [color, setColor] = useState("#10b981");
  const [width, setWidth] = useState(4);
  const colors = ["#10b981", "#60a5fa", "#f59e0b", "#f43f5e", "#e5e7eb", "#111827"];
  useEffect(() => { strokesRef.current = strokes; }, [strokes]);

  function pointFromEvent(event: React.PointerEvent<SVGSVGElement>): WhiteboardPoint | null {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect || rect.width <= 0 || rect.height <= 0) return null;
    return { x: Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1), y: Math.min(Math.max((event.clientY - rect.top) / rect.height, 0), 1) };
  }
  function beginStroke(event: React.PointerEvent<SVGSVGElement>) {
    if (event.button !== 0 && event.pointerType === "mouse") return;
    const point = pointFromEvent(event); if (!point) return;
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    activeStrokeRef.current = id; event.currentTarget.setPointerCapture(event.pointerId);
    const next = [...strokesRef.current, { id, color, width, points: [point] }].slice(-120);
    strokesRef.current = next;
    onChange(next);
  }
  function extendStroke(event: React.PointerEvent<SVGSVGElement>) {
    const id = activeStrokeRef.current; if (!id) return;
    const point = pointFromEvent(event); if (!point) return;
    const next = strokesRef.current.map((stroke) => { if (stroke.id !== id) return stroke; const last = stroke.points[stroke.points.length - 1]; if (last && Math.hypot(point.x - last.x, point.y - last.y) < 0.0015) return stroke; return { ...stroke, points: [...stroke.points, point].slice(-600) }; });
    strokesRef.current = next;
    onChange(next);
  }
  function endStroke(event: React.PointerEvent<SVGSVGElement>) { activeStrokeRef.current = null; if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId); }

  return <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#111827]">
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-white/10 px-2.5 py-1.5">
      <div className="flex items-center gap-2"><PenLine size={15} className="text-brand-300" /><div><p className="text-xs font-semibold text-white">Tableau blanc partagé</p><p className="text-[9px] text-gray-500">Dessinez ensemble en temps réel.</p></div></div>
      <div className="flex items-center gap-1.5">{colors.map((item) => <button type="button" key={item} onClick={() => setColor(item)} className={`h-5 w-5 rounded-full border ${color === item ? "border-white ring-2 ring-brand-400/60" : "border-white/20"}`} style={{ backgroundColor: item }} aria-label={`Couleur ${item}`} />)}<label className="ml-1 flex items-center gap-1 text-[9px] text-gray-400">Trait<input type="range" min="1" max="12" value={width} onChange={(event) => setWidth(Number(event.target.value))} className="w-20 accent-emerald-500" /></label><button type="button" onClick={() => { const next = strokesRef.current.slice(0, -1); strokesRef.current = next; onChange(next); }} disabled={strokes.length === 0} className="toolbar-secondary !px-2 !py-1 !text-[10px]">Annuler</button><button type="button" onClick={() => { strokesRef.current = []; onChange([]); }} disabled={strokes.length === 0} className="toolbar-danger !px-2 !py-1 !text-[10px]"><Trash2 size={12} /> Effacer</button><button type="button" onClick={onBackToVideo} className="toolbar-secondary !px-2 !py-1 !text-[10px]"><Video size={12} /> Vidéo</button></div>
    </div>
    <div className="min-h-0 flex-1 bg-white"><svg ref={svgRef} viewBox="0 0 1000 600" preserveAspectRatio="none" className="h-full w-full cursor-crosshair touch-none select-none bg-white" onPointerDown={beginStroke} onPointerMove={extendStroke} onPointerUp={endStroke} onPointerCancel={endStroke} onPointerLeave={(event) => { if (event.buttons === 0) activeStrokeRef.current = null; }}><rect width="1000" height="600" fill="#ffffff" />{strokes.map((stroke) => <polyline key={stroke.id} points={stroke.points.map((point) => `${point.x * 1000},${point.y * 600}`).join(" ")} fill="none" stroke={stroke.color} strokeWidth={stroke.width} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />)}</svg></div>
  </div>;
}

function codeThemePalette(theme: CodeTheme) {
  if (theme === "dracula") return { background: "#282a36", text: "#f8f8f2", lineNumber: "#6272a4", keyword: "#ff79c6", string: "#f1fa8c", number: "#bd93f9", comment: "#6272a4", function: "#50fa7b", tag: "#8be9fd" };
  if (theme === "light") return { background: "#f8fafc", text: "#0f172a", lineNumber: "#94a3b8", keyword: "#7c3aed", string: "#15803d", number: "#b45309", comment: "#64748b", function: "#0369a1", tag: "#be123c" };
  return { background: "#070b14", text: "#e5e7eb", lineNumber: "#4b5563", keyword: "#c084fc", string: "#86efac", number: "#fbbf24", comment: "#64748b", function: "#67e8f9", tag: "#fb7185" };
}
function escapeCode(value: string) { return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;"); }
function highlightCode(code: string, language: CodeLanguage, theme: CodeTheme) {
  const palette = codeThemePalette(theme);
  const keywordMap: Record<CodeLanguage, Set<string>> = {
    javascript: new Set(["const","let","var","function","return","if","else","for","while","class","new","async","await","try","catch","throw","import","from","export","default","true","false","null","undefined","this","extends"]),
    python: new Set(["def","return","if","elif","else","for","while","class","import","from","as","try","except","finally","raise","with","lambda","True","False","None","and","or","not","in","is","async","await","yield"]),
    java: new Set(["public","private","protected","class","interface","static","final","void","int","long","double","float","boolean","new","return","if","else","for","while","try","catch","throw","throws","extends","implements","package","import","this","true","false","null"]),
    c: new Set(["int","char","float","double","void","struct","typedef","const","static","return","if","else","for","while","switch","case","break","continue","sizeof","include"]),
    cpp: new Set(["int","char","float","double","void","class","struct","namespace","using","public","private","protected","template","typename","auto","const","static","return","if","else","for","while","switch","case","break","continue","new","delete","true","false","nullptr"]),
    html: new Set(), css: new Set(), text: new Set(),
  };
  const keywords = keywordMap[language];
  const pattern = language === "python" ? /(\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|#[^\n]*|\b\d+(?:\.\d+)?\b|\b[A-Za-z_][A-Za-z0-9_]*\b)/g : language === "html" ? /(<!--[\s\S]*?-->|<\/?[A-Za-z][^>]*>|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')/g : language === "css" ? /(\/\*[\s\S]*?\*\/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|#[0-9A-Fa-f]{3,8}\b|\b\d+(?:\.\d+)?(?:px|rem|em|%|vh|vw|s|ms)?\b|[A-Za-z-]+(?=\s*:))/g : /(\/\*[\s\S]*?\*\/|\/\/[^\n]*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|\b\d+(?:\.\d+)?\b|\b[A-Za-z_][A-Za-z0-9_]*\b)/g;
  let result = ""; let last = 0;
  for (const match of code.matchAll(pattern)) { const index = match.index ?? 0; const token = match[0]; result += escapeCode(code.slice(last, index)); let color = palette.text; if ((language === "python" && token.startsWith("#")) || token.startsWith("//") || token.startsWith("/*") || token.startsWith("<!--")) color = palette.comment; else if (token.startsWith("\"") || token.startsWith("'") || token.startsWith("`")) color = palette.string; else if (/^\d/.test(token) || (language === "css" && token.startsWith("#"))) color = palette.number; else if (language === "html" && token.startsWith("<")) color = palette.tag; else if (language === "css" && /^[A-Za-z-]+$/.test(token)) color = palette.keyword; else if (keywords.has(token)) color = palette.keyword; else if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(token)) color = palette.function; result += `<span style="color:${color}">${escapeCode(token)}</span>`; last = index + token.length; }
  result += escapeCode(code.slice(last)); return result || " ";
}

function InfoCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.035] px-2 py-1.5">
      <div className="flex items-center gap-1.5 text-brand-200">
        <div className="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-white/10">{icon}</div>
        <div className="min-w-0"><p className="text-[8px] uppercase tracking-wide text-gray-500">{label}</p><p className="truncate text-[11px] font-semibold leading-tight text-white">{value}</p></div>
      </div>
    </div>
  );
}

function SidebarButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button type="button" onClick={onClick} className={`rounded-xl px-2 py-1 text-[10px] font-semibold transition sm:text-[11px] ${active ? "bg-white text-gray-950" : "text-gray-300 hover:bg-white/5"}`}>{children}</button>;
}

function MiniAction({ onClick, danger, children }: { onClick: () => void; danger?: boolean; children: React.ReactNode }) {
  return <button type="button" onClick={onClick} className={`rounded-lg px-1.5 py-1 text-[9px] font-semibold transition ${danger ? "bg-red-500/10 text-red-300 hover:bg-red-500/20" : "bg-white/10 text-gray-300 hover:bg-white/15"}`}>{children}</button>;
}

function EmptyPanel({ children }: { children: React.ReactNode }) {
  return <div className="rounded-2xl border border-dashed border-white/10 p-3 text-[11px] text-gray-400 sm:text-xs">{children}</div>;
}

function ControlButton({ active, label, onClick, disabled, children, compact = false }: { active: boolean; label: string; onClick: () => void; disabled?: boolean; children: React.ReactNode; compact?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} title={label} className={`inline-flex shrink-0 items-center justify-center rounded-xl font-medium transition ${compact ? "h-8 w-8 p-0" : "gap-1 px-2.5 py-1.5 text-[11px]"} ${active ? "bg-brand-600 text-white" : "bg-white/10 text-gray-200 hover:bg-white/15"} ${disabled ? "cursor-not-allowed opacity-50" : ""}`}>
      {children}{!compact && <span>{label}</span>}
    </button>
  );
}

function VideoTile({ title, subtitle, footer, videoRef, muted, handRaised, avatar, videoEnabled = true }: { title: string; subtitle: string; footer: string; videoRef: React.RefObject<HTMLVideoElement>; muted?: boolean; handRaised?: boolean; avatar?: string | null; videoEnabled?: boolean }) {
  const initial = title.trim().charAt(0).toUpperCase() || "U";
  return (
    <div className={`relative min-h-[170px] overflow-hidden rounded-2xl border bg-black ${handRaised ? "border-amber-400/60" : "border-white/10"}`}>
      <video ref={videoRef} autoPlay playsInline muted={muted} className={`h-full min-h-[170px] w-full object-cover transition-opacity ${videoEnabled ? "opacity-100" : "opacity-0"}`} />
      {!videoEnabled && (
        <div className="absolute inset-0 grid place-items-center bg-gradient-to-br from-gray-900 to-gray-950">
          <div className="text-center">
            {avatar ? <img src={avatar} alt="" className="mx-auto h-16 w-16 rounded-full object-cover ring-2 ring-white/10" /> : <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-brand-500/15 text-2xl font-bold text-brand-200 ring-2 ring-white/10">{initial}</div>}
            <p className="mt-2 text-xs font-semibold text-white">{title}</p>
            <p className="text-[10px] text-gray-500">Caméra désactivée</p>
          </div>
        </div>
      )}
      <div className="absolute left-2 top-2 flex max-w-[75%] items-center gap-2 rounded-full bg-black/60 py-1 pl-1 pr-2.5 backdrop-blur">
        {avatar ? <img src={avatar} alt="" className="h-6 w-6 rounded-full object-cover" /> : <span className="grid h-6 w-6 place-items-center rounded-full bg-brand-500/20 text-[10px] font-bold text-brand-200">{initial}</span>}
        <div className="min-w-0 leading-tight"><div className="flex items-center gap-1"><p className="truncate text-[10px] font-semibold text-white">{title}</p>{handRaised && <Hand size={11} className="shrink-0 text-amber-300" />}</div><p className="truncate text-[8px] text-gray-400">{subtitle}</p></div>
      </div>
      <span className="absolute right-2 top-2 rounded-full bg-black/60 px-2 py-1 text-[8px] text-gray-300 backdrop-blur">{footer}</span>
    </div>
  );
}

function RemoteVideo({ feed, handRaised, avatar, onElement }: { feed: RemoteFeed; handRaised: boolean; avatar?: string | null; onElement: (element: HTMLVideoElement | null) => void }) {
  const ref = useRef<HTMLVideoElement | null>(null);
  useEffect(() => {
    const element = ref.current;
    if (element) {
      element.srcObject = feed.stream;
      onElement(element);
    }
    return () => onElement(null);
  }, [feed.stream, onElement]);

  return <VideoTile title={feed.name} subtitle="Participant" footer="En direct" videoRef={ref} handRaised={handRaised} avatar={avatar} />;
}

function inviteStatusLabel(status: SessionInvite["status"]) {
  if (status === "accepted") return "A rejoint la séance";
  if (status === "account_exists") return "Compte LearnEas trouvé";
  if (status === "pending_account") return "En attente de création du compte";
  return "Invitation révoquée";
}

function formatBytes(value: number) {
  if (!Number.isFinite(value) || value <= 0) return "0 o";
  const units = ["o", "Ko", "Mo", "Go"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toLocaleString("fr-FR", { maximumFractionDigits: index === 0 ? 0 : 1 })} ${units[index]}`;
}
