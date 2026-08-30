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
  PhoneOff,
  Play,
  PlayCircle,
  ScreenShare,
  ScreenShareOff,
  Settings,
  ShieldCheck,
  StopCircle,
  Upload,
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
  user: { id: number; name: string };
}

interface Person {
  user_id: number;
  name: string;
  role: string;
  hand_raised: boolean;
}

interface SignalMessage {
  id: number;
  sender_id: number;
  sender_name: string;
  kind: "offer" | "answer" | "ice" | "chat" | "control" | "code";
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

type SidebarTab = "participants" | "chat" | "files";
type WorkspaceMode = "video" | "code";
type ModerationAction = "mute" | "camera_off" | "remove";
type CodeLanguage = "javascript" | "html" | "css" | "python" | "java" | "c" | "cpp" | "text";

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

  function toggleCamera() {
    if (screenSharing) return;
    const next = !cameraOn;
    localStreamRef.current?.getVideoTracks().forEach((track) => {
      track.enabled = next;
    });
    if (cameraTrackRef.current) cameraTrackRef.current.enabled = next;
    setCameraOn(next);
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

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
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
    navigator.clipboard.writeText(codeText).then(() => setNotice("Code copié dans le presse-papiers.")).catch(() => {});
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

  function runCode() {
    setCodeRunning(true);
    setCodeOutput("");
    const nonce = ++codeRunNonceRef.current;
    if (codeLanguage === "html") {
      setCodeOutput("Aperçu HTML affiché dans le panneau de résultat.");
      setCodeRunning(false);
      return;
    }
    if (codeLanguage !== "javascript") {
      setCodeOutput(`Exécution non disponible dans le navigateur pour ${codeLanguage}. Le code reste éditable et partagé en direct.`);
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
      <div className="mx-auto flex h-full max-w-[1680px] flex-col px-3 py-3 sm:px-5">
        <div className="mb-3 shrink-0 flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-brand-300">
              Salle LearnEas · Séance {room.session_number}
            </p>
            <h1 className="mt-1.5 text-xl font-bold sm:text-2xl">{room.title}</h1>
            <p className="mt-1.5 max-w-3xl text-xs text-gray-400 sm:text-sm">
              Caméra, audio, partage d&apos;écran, chat, fichiers, levée de main et outils de modération intégrés.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={copyLink} className="toolbar-secondary !px-3 !py-2 !text-xs">
              <Copy size={16} /> {copied ? "Lien copié" : "Copier le lien"}
            </button>
            {room.is_organizer && attendanceId && (
              <button
                onClick={recording ? stopRecording : startRecording}
                className={recording ? "toolbar-danger" : "toolbar-secondary"}
              >
                <span className={`h-2.5 w-2.5 rounded-full ${recording ? "animate-pulse bg-white" : "bg-red-500"}`} />
                {recording ? "Arrêter l'enregistrement" : "Enregistrer"}
              </button>
            )}
            {room.is_organizer && !room.started_at && !room.completed && (
              <button onClick={startSession} disabled={actionBusy} className="toolbar-success !px-3 !py-2 !text-xs">
                <PlayCircle size={16} /> Démarrer
              </button>
            )}
            {room.is_organizer && room.started_at && !room.completed && (
              <button onClick={endSession} disabled={actionBusy} className="toolbar-danger !px-3 !py-2 !text-xs">
                <StopCircle size={16} /> Terminer
              </button>
            )}
          </div>
        </div>

        {notice && (
          <div className="mb-3 flex items-start justify-between gap-3 rounded-2xl border border-brand-400/20 bg-brand-400/10 px-3.5 py-2.5 text-xs text-brand-100 sm:text-sm">
            <span>{notice}</span>
            <button onClick={() => setNotice("")} className="text-xs font-semibold text-white/70 hover:text-white">Fermer</button>
          </div>
        )}

        <div className="mb-3 shrink-0 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
          <InfoCard icon={<Users size={18} />} label="Participants" value={`${participantsCount}`} />
          <InfoCard icon={<Hand size={18} />} label="Mains levées" value={`${raisedHandsCount}`} />
          <InfoCard icon={<StopCircle size={18} />} label="Durée live" value={elapsedLabel} />
          <InfoCard icon={<Monitor size={18} />} label="Durée planifiée" value={`${room.planned_duration_minutes} min`} />
          <InfoCard icon={<FileText size={18} />} label="Fichiers partagés" value={`${files.length}`} />
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto pb-20 xl:overflow-hidden">
        {!attendanceId ? (
          <div className="mx-auto mt-12 max-w-lg rounded-3xl border border-white/10 bg-white/5 p-6 text-center shadow-2xl">
            <ShieldCheck size={42} className="mx-auto mb-4 text-brand-300" />
            <h2 className="text-xl font-bold">Prêt à rejoindre la séance ?</h2>
            <p className="mt-2 text-sm text-gray-400">
              Votre présence et votre temps de connexion seront enregistrés pour le suivi de la formation.
            </p>
            {room.completed ? (
              <p className="mt-5 text-sm text-gray-400">Cette séance est terminée.</p>
            ) : !room.is_organizer && !room.started_at ? (
              <div className="mt-5 rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-sm text-gray-300">La séance n&apos;a pas encore été démarrée par l&apos;organisateur.</p>
                <p className="mt-1 text-xs text-gray-500">Cette page se met à jour automatiquement.</p>
              </div>
            ) : (
              <button onClick={enterRoom} disabled={joining} className="mt-6 rounded-xl bg-brand-600 px-6 py-3 font-semibold text-white hover:bg-brand-700">
                {joining ? <Loader2 className="mr-2 inline animate-spin" size={18} /> : <Video className="mr-2 inline" size={18} />}
                Entrer dans la salle
              </button>
            )}
            {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
          </div>
        ) : (
          <>
            <div className="grid h-full min-h-0 gap-3 xl:grid-cols-[minmax(0,1fr)_330px]">
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
                ) : (
                  <div className="flex h-full min-h-0 flex-col rounded-3xl border border-white/10 bg-white/5 p-3">
                    <div className="mb-3 flex shrink-0 flex-wrap items-center justify-between gap-3">
                      <div>
                        <h2 className="text-base font-semibold">Scène de la session</h2>
                        <p className="text-xs text-gray-400 sm:text-sm">
                          {screenSharing ? "Votre écran est visible par les participants." : "Vue vidéo de la séance en temps réel."}
                        </p>
                      </div>
                      <button onClick={toggleFullscreen} className="toolbar-secondary !px-3 !py-2 !text-xs">
                        <Maximize2 size={15} /> {fullscreen ? "Quitter le plein écran" : "Plein écran"}
                      </button>
                    </div>

                    <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 overflow-y-auto lg:grid-cols-2 2xl:grid-cols-3">
                      <VideoTile
                        title="Vous"
                        subtitle={screenSharing ? "Partage d'écran" : room.is_organizer ? "Organisateur" : "Participant"}
                        videoRef={localVideoRef}
                        muted
                        footer={screenSharing ? "Écran partagé" : cameraOn ? "Caméra active" : "Caméra coupée"}
                        handRaised={myHandRaised}
                      />
                      {remoteFeeds.map((feed) => (
                        <RemoteVideo
                          key={feed.userId}
                          feed={feed}
                          handRaised={Boolean(people.find((person) => person.user_id === feed.userId)?.hand_raised)}
                          onElement={(element) => {
                            if (element) remoteVideoElementsRef.current.set(feed.userId, element);
                            else remoteVideoElementsRef.current.delete(feed.userId);
                          }}
                        />
                      ))}
                      {remoteFeeds.length === 0 && (
                        <div className="grid min-h-[190px] place-items-center rounded-3xl border border-dashed border-white/10 bg-gray-900/80 p-5 text-center text-xs text-gray-500 sm:text-sm">
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

              <aside className="flex h-full min-h-0 flex-col overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-3">
                <div className="mb-3 grid grid-cols-3 gap-1 rounded-2xl bg-black/20 p-1">
                  <SidebarButton active={sidebarTab === "participants"} onClick={() => setSidebarTab("participants")}>Participants</SidebarButton>
                  <SidebarButton active={sidebarTab === "chat"} onClick={() => setSidebarTab("chat")}>Chat</SidebarButton>
                  <SidebarButton active={sidebarTab === "files"} onClick={() => setSidebarTab("files")}>Fichiers</SidebarButton>
                </div>

                {sidebarTab === "participants" && (
                  <div className="min-h-0 flex-1 overflow-y-auto pr-1">
                    <div className="mb-4 flex items-center justify-between">
                      <h3 className="font-semibold">Présences actives</h3>
                      <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-gray-300">{participantsCount} en ligne</span>
                    </div>
                    <div className="space-y-2.5">
                      {people.map((person) => (
                        <div key={person.user_id} className={`rounded-2xl border px-3 py-2.5 ${person.hand_raised ? "border-amber-400/40 bg-amber-400/10" : "border-white/10 bg-black/20"}`}>
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <p className="truncate font-medium text-white">{person.name}</p>
                                {person.hand_raised && <Hand size={15} className="shrink-0 text-amber-300" />}
                              </div>
                              <p className="text-xs text-gray-400">{person.role === "organizer" ? "Organisateur" : person.role === "admin" ? "Administrateur" : "Participant"}</p>
                            </div>
                            <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-emerald-400" />
                          </div>
                          {room.is_organizer && person.user_id !== room.user.id && (
                            <div className="mt-2.5 flex flex-wrap gap-1.5 border-t border-white/10 pt-2.5">
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
                    <div className="mb-4 flex items-center justify-between">
                      <h3 className="font-semibold">Messagerie de séance</h3>
                      <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-gray-300">{messages.length}</span>
                    </div>
                    <div className="flex-1 space-y-2.5 overflow-y-auto rounded-2xl border border-white/10 bg-black/20 p-2.5">
                      {messages.length === 0 ? (
                        <div className="grid min-h-[210px] place-items-center text-center text-xs text-gray-500 sm:text-sm">
                          <div>
                            <MessageSquare className="mx-auto mb-2" size={28} />
                            <p>Aucun message pour le moment.</p>
                            <p className="mt-1 text-xs text-gray-600">Posez une question ou partagez une information.</p>
                          </div>
                        </div>
                      ) : (
                        messages.map((message) => (
                          <div key={message.id} className={`max-w-[92%] rounded-2xl px-3 py-2.5 text-xs sm:text-sm ${message.mine ? "ml-auto bg-brand-600 text-white" : "bg-white/10 text-gray-100"}`}>
                            <div className="mb-1 flex items-center justify-between gap-4 text-[11px] opacity-80">
                              <span className="font-semibold">{message.mine ? "Vous" : message.senderName}</span>
                              <span>{new Date(message.at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}</span>
                            </div>
                            <p className="whitespace-pre-wrap leading-5">{message.text}</p>
                          </div>
                        ))
                      )}
                      <div ref={chatEndRef} />
                    </div>
                    <div className="mt-3 rounded-2xl border border-white/10 bg-black/20 p-2.5">
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
                        className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-white placeholder:text-gray-500 focus:border-brand-400 focus:outline-none sm:text-sm"
                      />
                      <div className="mt-3 flex items-center justify-between gap-2">
                        <span className="text-[11px] text-gray-500">{chatInput.length}/2000</span>
                        <button onClick={sendChatMessage} disabled={chatBusy || !chatInput.trim()} className="rounded-xl bg-brand-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60 sm:text-sm">
                          {chatBusy ? <Loader2 className="mr-2 inline animate-spin" size={16} /> : null}Envoyer
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {sidebarTab === "files" && (
                  <div className="min-h-0 flex-1 overflow-y-auto pr-1">
                    <div className="mb-4 flex items-center justify-between gap-3">
                      <div>
                        <h3 className="font-semibold">Fichiers de la séance</h3>
                        <p className="text-xs text-gray-500">20 Mo maximum par fichier.</p>
                      </div>
                      <button onClick={() => fileInputRef.current?.click()} disabled={fileBusy} className="toolbar-secondary !px-3 !py-2">
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
                      <div className="mb-4 rounded-2xl border border-brand-400/20 bg-brand-400/10 p-3">
                        <div className="mb-2 flex items-center justify-between text-xs text-brand-100"><span>Envoi en cours</span><span>{fileProgress}%</span></div>
                        <div className="h-2 overflow-hidden rounded-full bg-black/30"><div className="h-full rounded-full bg-brand-400 transition-all" style={{ width: `${fileProgress}%` }} /></div>
                      </div>
                    )}
                    <div className="space-y-2.5">
                      {files.map((item) => (
                        <div key={item.id} className="rounded-2xl border border-white/10 bg-black/20 p-3">
                          <div className="flex items-start gap-3">
                            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/10 text-brand-200"><FileText size={18} /></div>
                            <div className="min-w-0 flex-1">
                              <p className="break-words text-sm font-semibold text-white">{item.name}</p>
                              <p className="mt-1 text-xs text-gray-500">{formatBytes(item.size)} · {item.uploader_name}</p>
                              <p className="mt-1 text-[11px] text-gray-600">{new Date(item.uploaded_at).toLocaleString("fr-FR")}</p>
                            </div>
                          </div>
                          <button onClick={() => downloadRoomFile(item)} className="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-brand-200 hover:text-white"><Download size={14} /> Télécharger</button>
                        </div>
                      ))}
                      {files.length === 0 && <EmptyPanel>Aucun fichier partagé dans cette séance.</EmptyPanel>}
                    </div>
                  </div>
                )}
              </aside>
            </div>

            {devicePanelOpen && (
              <div className="fixed bottom-24 left-1/2 z-30 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 rounded-3xl border border-white/10 bg-gray-900/95 p-4 shadow-2xl backdrop-blur">
                <div className="mb-4 flex items-center justify-between">
                  <div><h3 className="font-semibold">Périphériques audio et vidéo</h3><p className="text-xs text-gray-400">Le changement est appliqué sans quitter la salle.</p></div>
                  <button onClick={() => setDevicePanelOpen(false)} className="text-xs font-semibold text-gray-400 hover:text-white">Fermer</button>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="text-xs font-semibold text-gray-300">Microphone
                    <select value={selectedAudioInput} onChange={(e) => switchAudioDevice(e.target.value)} disabled={recording} className="mt-2 w-full rounded-xl border border-white/10 bg-gray-950 px-3 py-2 text-xs text-white sm:text-sm">
                      {audioInputs.map((device) => <option key={device.deviceId} value={device.deviceId}>{device.label}</option>)}
                    </select>
                  </label>
                  <label className="text-xs font-semibold text-gray-300">Caméra
                    <select value={selectedVideoInput} onChange={(e) => switchVideoDevice(e.target.value)} disabled={recording} className="mt-2 w-full rounded-xl border border-white/10 bg-gray-950 px-3 py-2 text-xs text-white sm:text-sm">
                      {videoInputs.map((device) => <option key={device.deviceId} value={device.deviceId}>{device.label}</option>)}
                    </select>
                  </label>
                </div>
                {recording && <p className="mt-3 text-xs text-amber-300">Arrêtez l'enregistrement avant de changer de périphérique.</p>}
              </div>
            )}

            <div className="fixed bottom-4 left-1/2 z-20 flex w-[calc(100%-1rem)] max-w-4xl -translate-x-1/2 flex-wrap items-center justify-center gap-1.5 rounded-2xl border border-white/10 bg-gray-900/95 p-1.5 shadow-2xl backdrop-blur">
              <ControlButton active={micOn} onClick={toggleMic} label={micOn ? "Micro" : "Micro coupé"}>{micOn ? <Mic size={18} /> : <MicOff size={18} />}</ControlButton>
              <ControlButton active={cameraOn && !screenSharing} onClick={toggleCamera} disabled={screenSharing} label={screenSharing ? "Caméra verrouillée pendant le partage" : cameraOn ? "Caméra" : "Caméra coupée"}>{cameraOn ? <Video size={18} /> : <VideoOff size={18} />}</ControlButton>
              <ControlButton active={screenSharing} onClick={screenSharing ? () => stopScreenShare() : () => startScreenShare()} disabled={recording} label={screenSharing ? "Arrêter le partage" : "Partager l'écran"}>{screenSharing ? <ScreenShareOff size={18} /> : <ScreenShare size={18} />}</ControlButton>
              <ControlButton active={myHandRaised} onClick={toggleHand} label={myHandRaised ? "Baisser la main" : "Lever la main"}><Hand size={18} /></ControlButton>
              <ControlButton active={devicePanelOpen} onClick={() => { refreshDevices(); setDevicePanelOpen((value) => !value); }} label="Périphériques"><Settings size={18} /></ControlButton>
              <ControlButton active={workspaceMode === "code"} onClick={() => setWorkspaceMode(workspaceMode === "code" ? "video" : "code")} label={workspaceMode === "code" ? "Retour vidéo" : "Code"}><Code2 size={18} /></ControlButton>
              <ControlButton active={sidebarTab === "chat"} onClick={() => setSidebarTab(sidebarTab === "chat" ? "participants" : "chat")} label="Chat"><MessageSquare size={18} /></ControlButton>
              <button onClick={() => leaveRoom(false)} className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-3.5 py-2.5 text-xs font-semibold text-white hover:bg-red-500 sm:text-sm" title="Quitter"><PhoneOff size={18} /> <span className="hidden sm:inline">Quitter</span></button>
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
  const [scrollTop, setScrollTop] = useState(0);
  const lineNumbers = useMemo(() => Array.from({ length: Math.max(code.split("\n").length, 1) }, (_, index) => index + 1), [code]);

  function handleEditorKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Tab") return;
    event.preventDefault();
    const element = event.currentTarget;
    const start = element.selectionStart;
    const end = element.selectionEnd;
    const next = `${code.slice(0, start)}  ${code.slice(end)}`;
    onCodeChange(next);
    window.requestAnimationFrame(() => {
      textareaRef.current?.setSelectionRange(start + 2, start + 2);
    });
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#0b1020]">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-white/10 px-3 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-500/15 text-brand-200"><Code2 size={16} /></div>
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-white">Éditeur de code partagé</h2>
            <p className="text-[10px] text-gray-500">Les modifications sont synchronisées avec les participants présents.</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <button onClick={onBackToVideo} className="toolbar-secondary !px-2.5 !py-1.5 !text-[11px]"><Video size={14} /> Vidéo</button>
          <button onClick={onCopy} className="toolbar-secondary !px-2.5 !py-1.5 !text-[11px]"><Copy size={14} /> Copier</button>
          <button onClick={onDownload} className="toolbar-secondary !px-2.5 !py-1.5 !text-[11px]"><Download size={14} /> Télécharger</button>
          <button onClick={onRun} disabled={running} className="toolbar-success !px-2.5 !py-1.5 !text-[11px]">
            {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />} Exécuter
          </button>
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-white/10 bg-black/15 px-3 py-2">
        <label className="flex items-center gap-2 text-[11px] text-gray-400">
          Langage
          <select
            value={language}
            onChange={(event) => onLanguageChange(event.target.value as CodeLanguage)}
            className="rounded-lg border border-white/10 bg-gray-950 px-2.5 py-1.5 text-xs text-white outline-none focus:border-brand-400"
          >
            <option value="javascript">JavaScript</option>
            <option value="html">HTML</option>
            <option value="css">CSS</option>
            <option value="python">Python</option>
            <option value="java">Java</option>
            <option value="c">C</option>
            <option value="cpp">C++</option>
            <option value="text">Texte</option>
          </select>
        </label>
        <label className="flex min-w-0 flex-1 items-center gap-2 text-[11px] text-gray-400">
          Fichier
          <input
            value={fileName}
            onChange={(event) => onFileNameChange(event.target.value.slice(0, 80))}
            className="min-w-[140px] max-w-xs flex-1 rounded-lg border border-white/10 bg-gray-950 px-2.5 py-1.5 font-mono text-xs text-white outline-none focus:border-brand-400"
          />
        </label>
        <span className="rounded-full bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold text-emerald-300">Partage live actif</span>
      </div>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="relative min-h-0 overflow-hidden border-r border-white/10 bg-[#070b14] font-mono text-[13px] leading-6">
          <div className="absolute inset-y-0 left-0 w-11 overflow-hidden border-r border-white/10 bg-black/20 text-right text-gray-600" aria-hidden="true">
            <div style={{ transform: `translateY(-${scrollTop}px)` }} className="py-3 pr-2">
              {lineNumbers.map((line) => <div key={line} className="h-6 select-none">{line}</div>)}
            </div>
          </div>
          <textarea
            ref={textareaRef}
            value={code}
            onChange={(event) => onCodeChange(event.target.value.slice(0, 100000))}
            maxLength={100000}
            onKeyDown={handleEditorKeyDown}
            onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
            spellCheck={false}
            autoCapitalize="off"
            autoCorrect="off"
            className="h-full min-h-[260px] w-full resize-none overflow-auto bg-transparent py-3 pl-14 pr-4 font-mono text-[13px] leading-6 text-gray-100 outline-none selection:bg-brand-500/30"
            aria-label="Éditeur de code LearnEas"
          />
        </div>

        <div className="flex min-h-0 flex-col bg-[#0a0f1b]">
          <div className="shrink-0 border-b border-white/10 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">Résultat / Console</p>
          </div>
          {language === "html" ? (
            <iframe
              title="Aperçu HTML"
              sandbox="allow-scripts"
              srcDoc={code}
              className="min-h-0 flex-1 bg-white"
            />
          ) : (
            <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-xs leading-5 text-gray-300">
              {output || (language === "javascript" ? "Cliquez sur Exécuter pour afficher la console." : "Édition et partage en direct disponibles. L’exécution locale est réservée à JavaScript et HTML.")}
            </pre>
          )}
        </div>
      </div>
      <iframe ref={runnerRef} title="Exécution JavaScript sécurisée" sandbox="allow-scripts" className="hidden" />
    </div>
  );
}

function InfoCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
      <div className="flex items-center gap-2.5 text-brand-200">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white/10">{icon}</div>
        <div className="min-w-0"><p className="text-[11px] uppercase tracking-wide text-gray-400">{label}</p><p className="truncate text-base font-semibold text-white">{value}</p></div>
      </div>
    </div>
  );
}

function SidebarButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button onClick={onClick} className={`rounded-xl px-2 py-1.5 text-[11px] font-semibold transition sm:text-xs ${active ? "bg-white text-gray-950" : "text-gray-300 hover:bg-white/5"}`}>{children}</button>;
}

function MiniAction({ onClick, danger, children }: { onClick: () => void; danger?: boolean; children: React.ReactNode }) {
  return <button onClick={onClick} className={`rounded-lg px-2 py-1 text-[10px] font-semibold transition ${danger ? "bg-red-500/10 text-red-300 hover:bg-red-500/20" : "bg-white/10 text-gray-300 hover:bg-white/15"}`}>{children}</button>;
}

function EmptyPanel({ children }: { children: React.ReactNode }) {
  return <div className="rounded-2xl border border-dashed border-white/10 p-4 text-xs text-gray-400 sm:text-sm">{children}</div>;
}

function ControlButton({ active, label, onClick, disabled, children }: { active: boolean; label: string; onClick: () => void; disabled?: boolean; children: React.ReactNode }) {
  return (
    <button onClick={onClick} disabled={disabled} title={label} className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-2.5 text-xs font-medium transition sm:px-3.5 sm:text-sm ${active ? "bg-brand-600 text-white" : "bg-white/10 text-gray-200 hover:bg-white/15"} ${disabled ? "cursor-not-allowed opacity-50" : ""}`}>
      {children}<span className="hidden lg:inline">{label}</span>
    </button>
  );
}

function VideoTile({ title, subtitle, footer, videoRef, muted, handRaised }: { title: string; subtitle: string; footer: string; videoRef: React.RefObject<HTMLVideoElement>; muted?: boolean; handRaised?: boolean }) {
  return (
    <div className={`overflow-hidden rounded-3xl border bg-gray-900 shadow-2xl ${handRaised ? "border-amber-400/60" : "border-white/10"}`}>
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-2.5">
        <div className="min-w-0"><div className="flex items-center gap-2"><p className="truncate font-semibold text-white">{title}</p>{handRaised && <Hand size={15} className="shrink-0 text-amber-300" />}</div><p className="truncate text-xs text-gray-400">{subtitle}</p></div>
        <span className="ml-2 shrink-0 rounded-full bg-black/30 px-2 py-0.5 text-[10px] text-gray-300">{footer}</span>
      </div>
      <div className="relative min-h-[220px] bg-black"><video ref={videoRef} autoPlay playsInline muted={muted} className="h-full min-h-[220px] w-full object-cover" /></div>
    </div>
  );
}

function RemoteVideo({ feed, handRaised, onElement }: { feed: RemoteFeed; handRaised: boolean; onElement: (element: HTMLVideoElement | null) => void }) {
  const ref = useRef<HTMLVideoElement | null>(null);
  useEffect(() => {
    const element = ref.current;
    if (element) {
      element.srcObject = feed.stream;
      onElement(element);
    }
    return () => onElement(null);
  }, [feed.stream, onElement]);

  return <VideoTile title={feed.name} subtitle="Participant connecté" footer="En direct" videoRef={ref} handRaised={handRaised} />;
}

function formatBytes(value: number) {
  if (!Number.isFinite(value) || value <= 0) return "0 o";
  const units = ["o", "Ko", "Mo", "Go"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toLocaleString("fr-FR", { maximumFractionDigits: index === 0 ? 0 : 1 })} ${units[index]}`;
}
