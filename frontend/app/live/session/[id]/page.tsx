"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Code2,
  Copy,
  Download,
  FileText,
  X,
  FolderOpen,
  FilePlus,
  Hand,
  Loader2,
  Maximize2,
  Minimize2,
  MessageSquare,
  Mic,
  MicOff,
  Monitor,
  Move,
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
import { buildRealtimeWebSocketUrl } from "@/lib/realtime";
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
  ice_servers: RTCIceServer[];
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
type VideoLayout = "auto" | "gallery" | "focus";
type ModerationAction = "mute" | "camera_off" | "remove";
type CodeLanguage = "javascript" | "html" | "css" | "python" | "java" | "c" | "cpp" | "text";
type CodeTheme = "midnight" | "dracula" | "light";
type CodeFramework = "none" | "react" | "nextjs" | "django" | "drf" | "fastapi" | "flask" | "express";
interface CodeProjectFile { id: string; path: string; language: CodeLanguage; content: string }
interface WhiteboardPoint { x: number; y: number }
interface WhiteboardStroke { id: string; color: string; width: number; points: WhiteboardPoint[] }

function languageFromPath(path: string): CodeLanguage {
  const lower = path.toLowerCase();
  if (lower.endsWith(".py")) return "python";
  if (lower.endsWith(".html")) return "html";
  if (lower.endsWith(".css")) return "css";
  if (lower.endsWith(".java")) return "java";
  if (lower.endsWith(".cpp") || lower.endsWith(".cc")) return "cpp";
  if (lower.endsWith(".c")) return "c";
  if (lower.endsWith(".js") || lower.endsWith(".jsx") || lower.endsWith(".mjs") || lower.endsWith(".ts") || lower.endsWith(".tsx")) return "javascript";
  return "text";
}

function projectTemplate(framework: CodeFramework): CodeProjectFile[] {
  const file = (path: string, content: string): CodeProjectFile => ({ id: path, path, language: languageFromPath(path), content });
  if (framework === "react") return [
    file("src/App.jsx", `export default function App() {\n  return <main className="app"><h1>Bonjour React</h1></main>;\n}`),
    file("src/main.jsx", `import React from "react";\nimport { createRoot } from "react-dom/client";\nimport App from "./App";\nimport "./styles.css";\n\ncreateRoot(document.getElementById("root")).render(<App />);`),
    file("src/styles.css", `.app { font-family: system-ui; padding: 2rem; }`),
    file("index.html", `<div id="root"></div><script type="module" src="/src/main.jsx"></script>`),
    file("package.json", `{"scripts":{"dev":"vite","build":"vite build"},"dependencies":{"vite":"latest","react":"latest","react-dom":"latest"}}`),
  ];
  if (framework === "nextjs") return [
    file("app/page.jsx", `export default function Page() {\n  return <main><h1>KalanPro avec Next.js</h1></main>;\n}`),
    file("app/layout.jsx", `export default function RootLayout({ children }) {\n  return <html lang="fr"><body>{children}</body></html>;\n}`),
    file("app/globals.css", `body { margin: 0; font-family: system-ui; }`),
    file("package.json", `{"scripts":{"dev":"next dev","build":"next build","start":"next start"},"dependencies":{"next":"latest","react":"latest","react-dom":"latest"}}`),
  ];
  if (framework === "django" || framework === "drf") {
    const base = [
      file("manage.py", `import os, sys\n\nif __name__ == "__main__":\n    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")\n    from django.core.management import execute_from_command_line\n    execute_from_command_line(sys.argv)`),
      file("config/__init__.py", ``),
      file("config/settings.py", `SECRET_KEY = "atelier-uniquement"\nDEBUG = True\nROOT_URLCONF = "config.urls"\nINSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth", "app"${framework === "drf" ? `, "rest_framework"` : ""}]\nMIDDLEWARE = []\nDATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "db.sqlite3"}}\nDEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"\nUSE_TZ = True`),
      file("config/urls.py", `from django.urls import path, include\n\nurlpatterns = [path("", include("app.urls"))]`),
      file("app/__init__.py", ``),
      file("app/models.py", `from django.db import models\n\nclass Article(models.Model):\n    title = models.CharField(max_length=200)\n    created_at = models.DateTimeField(auto_now_add=True)\n\n    def __str__(self):\n        return self.title`),
      file("app/views.py", framework === "drf" ? `from rest_framework.viewsets import ModelViewSet\nfrom .models import Article\nfrom .serializers import ArticleSerializer\n\nclass ArticleViewSet(ModelViewSet):\n    queryset = Article.objects.all()\n    serializer_class = ArticleSerializer` : `from django.http import JsonResponse\n\ndef home(request):\n    return JsonResponse({"message": "Bonjour Django"})`),
      file("app/urls.py", framework === "drf" ? `from rest_framework.routers import DefaultRouter\nfrom .views import ArticleViewSet\n\nrouter = DefaultRouter()\nrouter.register("articles", ArticleViewSet)\nurlpatterns = router.urls` : `from django.urls import path\nfrom .views import home\n\nurlpatterns = [path("", home)]`),
    ];
    if (framework === "drf") base.push(file("app/serializers.py", `from rest_framework import serializers\nfrom .models import Article\n\nclass ArticleSerializer(serializers.ModelSerializer):\n    class Meta:\n        model = Article\n        fields = "__all__"`));
    return base;
  }
  if (framework === "fastapi") return [
    file("main.py", `from fastapi import FastAPI\nfrom models import Article\n\napp = FastAPI()\n\n@app.get("/")\ndef home():\n    return {"message": "Bonjour FastAPI"}`),
    file("models.py", `from dataclasses import dataclass\n\n@dataclass\nclass Article:\n    title: str`),
    file("requirements.txt", `fastapi\nuvicorn`),
  ];
  if (framework === "flask") return [
    file("app.py", `from flask import Flask, jsonify\nfrom services.greeting import greeting\n\napp = Flask(__name__)\n\n@app.get("/")\ndef home():\n    return jsonify(message=greeting("KalanPro"))`),
    file("services/greeting.py", `def greeting(name):\n    return f"Bonjour {name}"`),
    file("requirements.txt", `flask`),
  ];
  if (framework === "express") return [
    file("server.js", `const express = require("express");\nconst api = require("./routes/api");\nconst app = express();\napp.use("/api", api);\napp.listen(3000, () => console.log("Serveur prêt"));`),
    file("routes/api.js", `const router = require("express").Router();\nrouter.get("/", (req, res) => res.json({ message: "Bonjour Express" }));\nmodule.exports = router;`),
    file("package.json", `{"scripts":{"start":"node server.js"},"dependencies":{"express":"latest"}}`),
  ];
  return [file("main.js", `class Apprenant {\n  constructor(nom) { this.nom = nom; }\n  saluer() { return \`Bonjour ${'${this.nom}'}\`; }\n}\n\nconsole.log(new Apprenant("KalanPro").saluer());`)];
}

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
  const [remoteScreenShareUserId, setRemoteScreenShareUserId] = useState<number | null>(null);
  const [shareExpanded, setShareExpanded] = useState(false);
  const [presenterPipPosition, setPresenterPipPosition] = useState({ x: 0.745, y: 0.68 });
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
  const [videoLayout, setVideoLayout] = useState<VideoLayout>("auto");
  const [codeLanguage, setCodeLanguage] = useState<CodeLanguage>("javascript");
  const [codeFileName, setCodeFileName] = useState("main.js");
  const [codeText, setCodeText] = useState(`// Atelier KalanPro\nfunction bienvenue(nom) {\n  return \`Bonjour \${nom} !\`;\n}\n\nconsole.log(bienvenue("KalanPro"));`);
  const [codeFramework, setCodeFramework] = useState<CodeFramework>("none");
  const [activeCodeFileId, setActiveCodeFileId] = useState("main");
  const [codeFiles, setCodeFiles] = useState<CodeProjectFile[]>([
    { id: "main", path: "main.js", language: "javascript", content: `// Atelier KalanPro\nfunction bienvenue(nom) {\n  return \`Bonjour \${nom} !\`;\n}\n\nconsole.log(bienvenue("KalanPro"));` },
  ]);
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
  const shareCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const shareScreenSourceRef = useRef<HTMLVideoElement | null>(null);
  const shareCameraSourceRef = useRef<HTMLVideoElement | null>(null);
  const shareCompositeStreamRef = useRef<MediaStream | null>(null);
  const shareCompositeTrackRef = useRef<MediaStreamTrack | null>(null);
  const shareAnimationRef = useRef<number | null>(null);
  const presenterCameraRef = useRef<HTMLVideoElement | null>(null);
  const presenterPipPositionRef = useRef({ x: 0.745, y: 0.68 });
  const peersRef = useRef<Map<number, RTCPeerConnection>>(new Map());
  const pendingIceRef = useRef<Map<number, RTCIceCandidateInit[]>>(new Map());
  const lastSignalIdRef = useRef(0);
  const attendanceIdRef = useRef<number | null>(null);
  const realtimeSocketRef = useRef<WebSocket | null>(null);
  const realtimeReconnectTimerRef = useRef<number | null>(null);
  const remoteVideoElementsRef = useRef<Map<number, HTMLVideoElement>>(new Map());
  const codeRunnerRef = useRef<HTMLIFrameElement | null>(null);
  const skipCodeBroadcastRef = useRef(false);
  const codeRunNonceRef = useRef(0);
  const whiteboardBroadcastTimerRef = useRef<number | null>(null);
  const whiteboardRecipientsRef = useRef<Set<number>>(new Set());
  const screenShareRecipientsRef = useRef<Set<number>>(new Set());

  const recorderRef = useRef<MediaRecorder | null>(null);
  const recordingChunksRef = useRef<Blob[]>([]);
  const recordingStreamRef = useRef<MediaStream | null>(null);
  const recordingAnimationRef = useRef<number | null>(null);
  const recordingAudioContextRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    attendanceIdRef.current = attendanceId;
  }, [attendanceId]);

  useEffect(() => {
    presenterPipPositionRef.current = presenterPipPosition;
  }, [presenterPipPosition]);

  useEffect(() => {
    const element = presenterCameraRef.current;
    if (!element) return;
    const track = cameraTrackRef.current;
    if (screenSharing && cameraOn && track && track.readyState === "live") {
      element.srcObject = new MediaStream([track]);
      void element.play().catch(() => {});
    } else {
      element.srcObject = null;
    }
  }, [screenSharing, cameraOn]);

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
      if (realtimeReconnectTimerRef.current !== null) {
        window.clearTimeout(realtimeReconnectTimerRef.current);
        realtimeReconnectTimerRef.current = null;
      }
      realtimeSocketRef.current?.close(1000, "page-unmount");
      realtimeSocketRef.current = null;
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

  // L'état du partage est signalé séparément du média afin que chaque client
  // puisse rester en réunion ou agrandir le partage selon son besoin.
  useEffect(() => {
    if (!attendanceId || !room || !screenSharing) {
      screenShareRecipientsRef.current.clear();
      return;
    }
    const activeIds = new Set(people.map((person) => person.user_id));
    for (const known of Array.from(screenShareRecipientsRef.current)) {
      if (!activeIds.has(known)) screenShareRecipientsRef.current.delete(known);
    }
    for (const person of people) {
      if (person.user_id === room.user.id || screenShareRecipientsRef.current.has(person.user_id)) continue;
      sendSignal(person.user_id, "control", {
        action: "screen_share_state",
        active: true,
        sent_at: new Date().toISOString(),
      }).then(() => screenShareRecipientsRef.current.add(person.user_id)).catch(() => {});
    }
  }, [attendanceId, room, people, screenSharing, sendSignal]);

  useEffect(() => {
    if (remoteScreenShareUserId === null || !room) return;
    if (!people.some((person) => person.user_id === remoteScreenShareUserId)) {
      setRemoteScreenShareUserId(null);
      setShareExpanded(false);
    }
  }, [people, remoteScreenShareUserId, room]);

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
          framework: codeFramework,
          active_file_id: activeCodeFileId,
          files: codeFiles.slice(0, 30).map((file) => ({ id: file.id, path: file.path, language: file.language, content: file.content.slice(0, 100000) })),
          sent_at: new Date().toISOString(),
        }).catch(() => {});
      });
    }, 450);
    return () => window.clearTimeout(timer);
  }, [attendanceId, room, people, codeLanguage, codeFileName, codeText, codeFramework, activeCodeFileId, codeFiles, sendSignal]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.source !== codeRunnerRef.current?.contentWindow) return;
      if (event.data?.source !== "learneas-code-runner") return;
      if (event.data?.nonce !== codeRunNonceRef.current) return;
      setCodeOutput(String(event.data?.output || ""));
      setCodeRunning(false);
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  const syncLocalVideo = useCallback(() => {
    if (!localVideoRef.current) return;
    // Pendant une présentation, le présentateur voit la capture brute de son
    // écran. La caméra est rendue au-dessus comme une vignette DOM déplaçable,
    // tandis que les autres participants reçoivent le flux composite.
    if (screenStreamRef.current) {
      localVideoRef.current.srcObject = screenStreamRef.current;
    } else if (localStreamRef.current) {
      localVideoRef.current.srcObject = localStreamRef.current;
    } else {
      localVideoRef.current.srcObject = null;
    }
  }, []);

  const stopShareComposite = useCallback(() => {
    if (shareAnimationRef.current !== null) {
      cancelAnimationFrame(shareAnimationRef.current);
      shareAnimationRef.current = null;
    }
    shareCompositeTrackRef.current?.stop();
    shareCompositeStreamRef.current?.getTracks().forEach((track) => track.stop());
    shareCompositeTrackRef.current = null;
    shareCompositeStreamRef.current = null;
    if (shareScreenSourceRef.current) {
      shareScreenSourceRef.current.pause();
      shareScreenSourceRef.current.srcObject = null;
    }
    if (shareCameraSourceRef.current) {
      shareCameraSourceRef.current.pause();
      shareCameraSourceRef.current.srcObject = null;
    }
    shareScreenSourceRef.current = null;
    shareCameraSourceRef.current = null;
    shareCanvasRef.current = null;
  }, []);

  const attachCameraToShareComposite = useCallback(async (track: MediaStreamTrack | null) => {
    const source = shareCameraSourceRef.current;
    if (!source) return;
    if (track && track.readyState === "live") {
      source.srcObject = new MediaStream([track]);
      await source.play().catch(() => {});
    } else {
      source.pause();
      source.srcObject = null;
    }
  }, []);

  const startShareComposite = useCallback(async (displayStream: MediaStream) => {
    stopShareComposite();
    const displayTrack = displayStream.getVideoTracks()[0];
    if (!displayTrack) throw new Error("Aucune piste d'écran");

    const screenSource = document.createElement("video");
    screenSource.autoplay = true;
    screenSource.muted = true;
    screenSource.playsInline = true;
    screenSource.srcObject = displayStream;
    await screenSource.play().catch(() => {});

    const cameraSource = document.createElement("video");
    cameraSource.autoplay = true;
    cameraSource.muted = true;
    cameraSource.playsInline = true;
    const activeCamera = cameraTrackRef.current;
    if (activeCamera && activeCamera.readyState === "live") {
      cameraSource.srcObject = new MediaStream([activeCamera]);
      await cameraSource.play().catch(() => {});
    }

    shareScreenSourceRef.current = screenSource;
    shareCameraSourceRef.current = cameraSource;

    const settings = displayTrack.getSettings();
    const sourceWidth = Math.max(640, Number(settings.width) || screenSource.videoWidth || 1280);
    const sourceHeight = Math.max(360, Number(settings.height) || screenSource.videoHeight || 720);
    const scale = Math.min(1, 1280 / sourceWidth, 720 / sourceHeight);
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(640, Math.round(sourceWidth * scale));
    canvas.height = Math.max(360, Math.round(sourceHeight * scale));
    const context = canvas.getContext("2d", { alpha: false });
    if (!context) throw new Error("Canvas indisponible");
    shareCanvasRef.current = canvas;

    const roundedRect = (ctx: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) => {
      const r = Math.min(radius, width / 2, height / 2);
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + width, y, x + width, y + height, r);
      ctx.arcTo(x + width, y + height, x, y + height, r);
      ctx.arcTo(x, y + height, x, y, r);
      ctx.arcTo(x, y, x + width, y, r);
      ctx.closePath();
    };

    let lastFrameAt = 0;
    const draw = (now: number) => {
      shareAnimationRef.current = requestAnimationFrame(draw);
      if (now - lastFrameAt < 32) return;
      lastFrameAt = now;

      context.fillStyle = "#05070b";
      context.fillRect(0, 0, canvas.width, canvas.height);
      if (screenSource.readyState >= 2) {
        context.drawImage(screenSource, 0, 0, canvas.width, canvas.height);
      }

      const pipWidth = Math.round(canvas.width * 0.22);
      const cameraRatio = cameraSource.videoWidth > 0 && cameraSource.videoHeight > 0
        ? cameraSource.videoWidth / cameraSource.videoHeight
        : 16 / 9;
      const pipHeight = Math.round(pipWidth / Math.max(1.15, Math.min(cameraRatio, 2)));
      const pos = presenterPipPositionRef.current;
      const pipX = Math.round(Math.max(8, Math.min(canvas.width - pipWidth - 8, pos.x * canvas.width)));
      const pipY = Math.round(Math.max(8, Math.min(canvas.height - pipHeight - 8, pos.y * canvas.height)));
      const radius = Math.max(10, Math.round(canvas.width * 0.008));

      context.save();
      context.shadowColor = "rgba(0,0,0,.45)";
      context.shadowBlur = Math.max(10, Math.round(canvas.width * 0.01));
      context.shadowOffsetY = Math.max(3, Math.round(canvas.height * 0.004));
      roundedRect(context, pipX, pipY, pipWidth, pipHeight, radius);
      context.fillStyle = "#111827";
      context.fill();
      context.clip();
      if (cameraSource.srcObject && cameraSource.readyState >= 2 && cameraTrackRef.current?.readyState === "live") {
        const vw = cameraSource.videoWidth || pipWidth;
        const vh = cameraSource.videoHeight || pipHeight;
        const videoRatio = vw / vh;
        const boxRatio = pipWidth / pipHeight;
        let sx = 0, sy = 0, sw = vw, sh = vh;
        if (videoRatio > boxRatio) {
          sw = vh * boxRatio;
          sx = (vw - sw) / 2;
        } else {
          sh = vw / boxRatio;
          sy = (vh - sh) / 2;
        }
        context.drawImage(cameraSource, sx, sy, sw, sh, pipX, pipY, pipWidth, pipHeight);
      } else {
        context.fillStyle = "#111827";
        context.fillRect(pipX, pipY, pipWidth, pipHeight);
        context.fillStyle = "#10b981";
        context.beginPath();
        context.arc(pipX + pipWidth / 2, pipY + pipHeight / 2 - pipHeight * 0.08, pipHeight * 0.19, 0, Math.PI * 2);
        context.fill();
        context.fillStyle = "#ffffff";
        context.font = `600 ${Math.max(14, Math.round(pipHeight * 0.16))}px system-ui, sans-serif`;
        context.textAlign = "center";
        context.textBaseline = "middle";
        const initial = room?.user.name?.trim().charAt(0).toUpperCase() || "U";
        context.fillText(initial, pipX + pipWidth / 2, pipY + pipHeight / 2 - pipHeight * 0.08);
      }
      context.restore();
      context.save();
      roundedRect(context, pipX, pipY, pipWidth, pipHeight, radius);
      context.strokeStyle = "rgba(255,255,255,.82)";
      context.lineWidth = Math.max(2, Math.round(canvas.width * 0.0015));
      context.stroke();
      context.restore();
    };
    shareAnimationRef.current = requestAnimationFrame(draw);

    const capture = canvas.captureStream(30);
    const compositeTrack = capture.getVideoTracks()[0];
    if (!compositeTrack) throw new Error("Flux composite indisponible");
    compositeTrack.contentHint = "detail";
    shareCompositeStreamRef.current = capture;
    shareCompositeTrackRef.current = compositeTrack;
    return compositeTrack;
  }, [room?.user.name, stopShareComposite]);

  const replaceTrackOnPeers = useCallback(async (kind: "audio" | "video", track: MediaStreamTrack | null) => {
    const updates = Array.from(peersRef.current.values()).map(async (pc) => {
      // Après replaceTrack(null), sender.track devient null. On retrouve donc aussi
      // le sender via son transceiver pour pouvoir rattacher une nouvelle caméra
      // sans créer un second sender vidéo ni perdre le flux distant.
      const sender =
        pc.getSenders().find((item) => item.track?.kind === kind) ||
        pc.getTransceivers().find(
          (item) => item.sender.track?.kind === kind || item.receiver.track?.kind === kind
        )?.sender;
      if (sender) {
        await sender.replaceTrack(track);
      } else if (track && localStreamRef.current) {
        pc.addTrack(track, localStreamRef.current);
      }
    });
    await Promise.allSettled(updates);
  }, []);

  const releaseCamera = useCallback(
    async (detachFromPeers = true) => {
      const track = cameraTrackRef.current;
      cameraTrackRef.current = null;

      // Libérer le matériel immédiatement, sans attendre la signalisation WebRTC.
      // C'est ce stop() qui éteint réellement le voyant caméra du navigateur/OS.
      if (track) {
        track.onended = null;
        localStreamRef.current?.getVideoTracks().forEach((item) => {
          if (item.id === track.id) localStreamRef.current?.removeTrack(item);
        });
        track.stop();
      }
      setCameraOn(false);
      if (shareCameraSourceRef.current) {
        shareCameraSourceRef.current.pause();
        shareCameraSourceRef.current.srcObject = null;
      }
      syncLocalVideo();

      if (detachFromPeers) {
        await replaceTrackOnPeers("video", null);
      }
    },
    [replaceTrackOnPeers, syncLocalVideo]
  );

  const addMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => {
      if (prev.some((item) => item.id === message.id)) return prev;
      return [...prev, message];
    });
  }, []);

  const stopAllConferenceMedia = useCallback(() => {
    stopShareComposite();
    screenStreamRef.current?.getTracks().forEach((track) => track.stop());
    localStreamRef.current?.getTracks().forEach((track) => track.stop());
    peersRef.current.forEach((pc) => pc.close());
    peersRef.current.clear();
    remoteVideoElementsRef.current.clear();
    screenStreamRef.current = null;
    localStreamRef.current = null;
    cameraTrackRef.current = null;
  }, [stopShareComposite]);

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

      const iceServers: RTCIceServer[] = room?.ice_servers?.length
        ? room.ice_servers
        : [{ urls: "stun:stun.l.google.com:19302" }];

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
    [sendSignal, room]
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
        const incomingFiles = Array.isArray(message.payload?.files) ? message.payload.files : [];
        if (incomingFiles.length) {
          const cleaned: CodeProjectFile[] = incomingFiles.slice(0, 30).map((item: any, index: number) => ({
            id: String(item?.id || item?.path || `file-${index}`).slice(0, 100),
            path: String(item?.path || `file-${index}.txt`).slice(0, 120),
            language: String(item?.language || languageFromPath(String(item?.path || ""))) as CodeLanguage,
            content: String(item?.content || "").slice(0, 100000),
          }));
          const requestedId = String(message.payload?.active_file_id || cleaned[0].id);
          const active = cleaned.find((file) => file.id === requestedId) || cleaned[0];
          setCodeFiles(cleaned);
          setActiveCodeFileId(active.id);
          setCodeFileName(active.path);
          setCodeLanguage(active.language);
          setCodeText(active.content);
          setCodeFramework((String(message.payload?.framework || "none") as CodeFramework));
        } else {
          const nextLanguage = String(message.payload?.language || "javascript") as CodeLanguage;
          const name = String(message.payload?.file_name || "main.js");
          const content = String(message.payload?.text || "");
          setCodeLanguage(nextLanguage); setCodeFileName(name); setCodeText(content);
          setCodeFiles([{ id: "main", path: name, language: nextLanguage, content }]);
          setActiveCodeFileId("main");
        }
        setWorkspaceMode("code");
        setNotice(`${message.sender_name} partage le projet de code.`);
        return;
      }

      if (message.kind === "whiteboard") {
        const strokes = Array.isArray(message.payload?.strokes) ? message.payload.strokes : [];
        setWhiteboardStrokes(strokes.slice(-120));
        setWorkspaceMode("whiteboard");
        return;
      }

      if (message.kind === "control") {
        const rawAction = String(message.payload?.action || "");
        if (rawAction === "screen_share_state") {
          const active = Boolean(message.payload?.active);
          setRemoteScreenShareUserId((current) => active ? message.sender_id : (current === message.sender_id ? null : current));
          if (!active) setShareExpanded(false);
          setNotice(active ? `${message.sender_name} partage son écran.` : `${message.sender_name} a arrêté le partage d'écran.`);
          return;
        }
        const action = rawAction as ModerationAction;
        if (action === "mute") {
          localStreamRef.current?.getAudioTracks().forEach((track) => {
            track.enabled = false;
          });
          setMicOn(false);
          setNotice("L'organisateur a désactivé votre microphone.");
        } else if (action === "camera_off") {
          // Une piste simplement disabled garde le périphérique caméra réservé.
          // On la détache et on la stoppe réellement afin que le voyant système
          // et l'indicateur navigateur s'éteignent.
          await releaseCamera(!screenStreamRef.current);
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
    [addMessage, ensurePeer, flushIce, handleForcedRemoval, releaseCamera, sendSignal]
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
        const initialTrack = cameraTrackRef.current;
        initialTrack.onended = () => {
          if (cameraTrackRef.current?.id === initialTrack.id) {
            void releaseCamera(!screenStreamRef.current);
          }
        };
        setCameraOn(initialTrack.enabled);
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
      // Une reconnexion temps réel ou le fallback HTTP réessaiera.
    }
  }, [sessionId]);

  const loadPresence = useCallback(async () => {
    if (!attendanceIdRef.current || !room) return;
    try {
      const active = await api.get<Person[]>(`/sessions/${sessionId}/presence/`);
      setPeople(active);
      for (const person of active) {
        if (
          person.user_id !== room.user.id &&
          room.user.id < person.user_id &&
          !peersRef.current.has(person.user_id)
        ) {
          createOffer(person.user_id, person.name).catch(() => {});
        }
      }
    } catch {
      // Une perte momentanée de réseau ne ferme pas la salle.
    }
  }, [sessionId, room, createOffer]);

  useEffect(() => {
    if (!attendanceId || !room) return;
    let cancelled = false;
    let reconnectAttempt = 0;
    let fallbackTimer: number | null = null;

    async function heartbeat() {
      try {
        await api.post(`/sessions/${sessionId}/heartbeat/`, { attendance_id: attendanceId });
        if (realtimeSocketRef.current?.readyState === WebSocket.OPEN) {
          realtimeSocketRef.current.send(JSON.stringify({ type: "ping" }));
        }
      } catch {
        // Trois heartbeats manqués sont tolérés avant expiration de présence côté serveur.
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
        // Le fallback suivant réessaiera.
      }
    }

    function stopFallback() {
      if (fallbackTimer !== null) {
        window.clearInterval(fallbackTimer);
        fallbackTimer = null;
      }
    }

    function startFallback() {
      if (fallbackTimer !== null || cancelled) return;
      void pollSignals();
      void loadPresence();
      void loadFiles();
      fallbackTimer = window.setInterval(() => {
        void pollSignals();
        void loadPresence();
        void loadFiles();
      }, 3000);
    }

    function scheduleReconnect() {
      if (cancelled || realtimeReconnectTimerRef.current !== null) return;
      const delay = Math.min(1000 * (2 ** reconnectAttempt), 10000);
      reconnectAttempt += 1;
      realtimeReconnectTimerRef.current = window.setTimeout(() => {
        realtimeReconnectTimerRef.current = null;
        void connectRealtime();
      }, delay);
    }

    async function refreshRoomState() {
      try {
        const nextRoom = await api.get<RoomInfo>(`/sessions/${sessionId}/room/`);
        if (!cancelled) setRoom(nextRoom);
      } catch {
        // L'état courant reste affiché jusqu'à la prochaine reconnexion.
      }
    }

    async function connectRealtime() {
      try {
        const ticketData = await api.post<{ ticket: string; expires_in: number }>(
          `/sessions/${sessionId}/realtime-ticket/`
        );
        if (cancelled) return;
        const url = buildRealtimeWebSocketUrl({
          sessionId,
          ticket: ticketData.ticket,
          explicitBase: process.env.NEXT_PUBLIC_WS_URL,
          pageProtocol: window.location.protocol,
          pageHost: window.location.host,
        });
        const socket = new WebSocket(url);
        realtimeSocketRef.current?.close(1000, "reconnect");
        realtimeSocketRef.current = socket;

        socket.onopen = () => {
          reconnectAttempt = 0;
          stopFallback();
          void pollSignals(); // récupère un éventuel message créé pendant la poignée de main WS.
          void loadPresence();
          void loadFiles();
        };
        socket.onmessage = (event) => {
          void (async () => {
            try {
              const payload = JSON.parse(String(event.data || "{}"));
              if (payload.type === "signal" && payload.message) {
                const message = payload.message as SignalMessage;
                if (message.id <= lastSignalIdRef.current) return;
                lastSignalIdRef.current = message.id;
                await handleSignal(message);
              } else if (payload.type === "presence_changed") {
                await loadPresence();
              } else if (payload.type === "files_changed") {
                await loadFiles();
              } else if (payload.type === "session_state") {
                await refreshRoomState();
              }
            } catch {
              // Message temps réel malformé : ignoré, le canal reste ouvert.
            }
          })();
        };
        socket.onerror = () => socket.close();
        socket.onclose = () => {
          if (realtimeSocketRef.current === socket) realtimeSocketRef.current = null;
          if (cancelled) return;
          startFallback();
          scheduleReconnect();
        };
      } catch {
        startFallback();
        scheduleReconnect();
      }
    }

    void heartbeat();
    void loadPresence();
    void loadFiles();
    void connectRealtime();
    const heartbeatTimer = window.setInterval(() => void heartbeat(), 15000);
    const stalePresenceTimer = window.setInterval(() => void loadPresence(), 30000);

    return () => {
      cancelled = true;
      stopFallback();
      window.clearInterval(heartbeatTimer);
      window.clearInterval(stalePresenceTimer);
      if (realtimeReconnectTimerRef.current !== null) {
        window.clearTimeout(realtimeReconnectTimerRef.current);
        realtimeReconnectTimerRef.current = null;
      }
      realtimeSocketRef.current?.close(1000, "room-cleanup");
      realtimeSocketRef.current = null;
    };
  }, [attendanceId, room, sessionId, handleSignal, loadPresence, loadFiles]);

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
    // Comme dans les outils de visioconférence modernes, la caméra peut rester
    // active pendant un partage d'écran : elle est alors intégrée comme une
    // vignette présentateur dans le flux composite.
    if (screenSharing && cameraOn) {
      await releaseCamera(false);
      await attachCameraToShareComposite(null);
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
        const activatedTrack = track;
        activatedTrack.onended = () => {
          if (cameraTrackRef.current?.id === activatedTrack.id) {
            void releaseCamera(!screenStreamRef.current);
          }
        };
        if (!localStreamRef.current) localStreamRef.current = new MediaStream();
        if (screenSharing) {
          // Le flux sortant reste le composite écran + vignette. La piste caméra
          // sert uniquement de source au composite et à la vignette locale.
          await attachCameraToShareComposite(track);
        } else {
          localStreamRef.current.getVideoTracks().forEach((item) => localStreamRef.current?.removeTrack(item));
          localStreamRef.current.addTrack(track);
          await replaceTrackOnPeers("video", track);
        }
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
    // Couper la caméra doit libérer le matériel, pas seulement rendre la
    // piste muette. Au prochain clic, getUserMedia recréera une piste propre.
    await releaseCamera(!screenSharing);
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
    if (!deviceId || recording || screenSharing) return;
    setSelectedVideoInput(deviceId);

    // Si la caméra est coupée, mémoriser seulement le périphérique choisi.
    // Ne pas appeler getUserMedia ici : cela rallumerait physiquement la caméra
    // alors que l'utilisateur vient précisément de la désactiver.
    if (!cameraOn) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      const nextTrack = stream.getVideoTracks()[0];
      if (!nextTrack || !localStreamRef.current) {
        stream.getTracks().forEach((item) => item.stop());
        return;
      }
      const previousCamera = cameraTrackRef.current;
      const activatedTrack = nextTrack;
      activatedTrack.onended = () => {
        if (cameraTrackRef.current?.id === activatedTrack.id) {
          void releaseCamera(!screenStreamRef.current);
        }
      };
      cameraTrackRef.current = nextTrack;

      const currentVideo = localStreamRef.current.getVideoTracks()[0];
      if (currentVideo) localStreamRef.current.removeTrack(currentVideo);
      localStreamRef.current.addTrack(nextTrack);
      await replaceTrackOnPeers("video", nextTrack);
      syncLocalVideo();
      if (previousCamera && previousCamera.id !== nextTrack.id) {
        previousCamera.onended = null;
        previousCamera.stop();
      }
      await refreshDevices();
    } catch {
      setNotice("Impossible de changer de caméra.");
    }
  }

  async function startScreenShare() {
    if (!attendanceId || screenSharing || !localStreamRef.current || recording) return;
    try {
      const displayStream = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: { ideal: 30, max: 30 } },
        audio: false,
      });
      const displayTrack = displayStream.getVideoTracks()[0];
      if (!displayTrack) {
        displayStream.getTracks().forEach((track) => track.stop());
        return;
      }

      // Conserver la caméra physique en parallèle. Elle n'est plus envoyée
      // directement : elle devient la vignette du présentateur dans le canvas.
      const currentOutgoing = localStreamRef.current.getVideoTracks()[0] || null;
      if (currentOutgoing) localStreamRef.current.removeTrack(currentOutgoing);

      screenStreamRef.current = displayStream;
      const compositeTrack = await startShareComposite(displayStream);
      localStreamRef.current.addTrack(compositeTrack);
      await replaceTrackOnPeers("video", compositeTrack);
      setShareExpanded(false);
      setRemoteScreenShareUserId(null);
      setScreenSharing(true);
      syncLocalVideo();
      await localVideoRef.current?.play().catch(() => {});

      displayTrack.onended = () => {
        void stopScreenShare();
      };
    } catch {
      stopShareComposite();
      screenStreamRef.current?.getTracks().forEach((track) => track.stop());
      screenStreamRef.current = null;
      // Si la composition échoue après avoir détaché la caméra du MediaStream
      // local, la remettre immédiatement afin de ne pas casser la visioconférence.
      const cameraTrack = cameraTrackRef.current;
      if (cameraTrack && cameraTrack.readyState === "live" && localStreamRef.current) {
        if (!localStreamRef.current.getVideoTracks().some((track) => track.id === cameraTrack.id)) {
          localStreamRef.current.addTrack(cameraTrack);
        }
        await replaceTrackOnPeers("video", cameraTrack);
        setCameraOn(true);
      }
      setScreenSharing(false);
      syncLocalVideo();
      setNotice("Le partage d'écran a été annulé ou n'est pas disponible dans ce navigateur.");
    }
  }

  async function stopScreenShare() {
    if (!screenStreamRef.current && !shareCompositeTrackRef.current) return;
    const compositeTrack = shareCompositeTrackRef.current;
    if (compositeTrack && localStreamRef.current) {
      localStreamRef.current.getVideoTracks().forEach((track) => {
        if (track.id === compositeTrack.id) localStreamRef.current?.removeTrack(track);
      });
    }

    // Couper d'abord l'animation/capture, puis rendre la caméra classique aux
    // pairs. Cela évite un flash noir ou un second sender vidéo.
    stopShareComposite();
    screenStreamRef.current?.getTracks().forEach((track) => {
      track.onended = null;
      track.stop();
    });
    screenStreamRef.current = null;

    const cameraTrack = cameraTrackRef.current;
    // cameraTrackRef est la source de vérité ici : le callback onended du partage
    // peut avoir été créé avant un changement d'état React de la caméra.
    if (cameraTrack && cameraTrack.readyState !== "ended") {
      if (localStreamRef.current && !localStreamRef.current.getVideoTracks().some((track) => track.id === cameraTrack.id)) {
        localStreamRef.current.addTrack(cameraTrack);
      }
      await replaceTrackOnPeers("video", cameraTrack);
      setCameraOn(true);
    } else {
      await replaceTrackOnPeers("video", null);
      setCameraOn(false);
    }

    Array.from(screenShareRecipientsRef.current).forEach((recipientId) => {
      sendSignal(recipientId, "control", {
        action: "screen_share_state",
        active: false,
        sent_at: new Date().toISOString(),
      }).catch(() => {});
    });
    screenShareRecipientsRef.current.clear();
    setShareExpanded(false);
    setScreenSharing(false);
    syncLocalVideo();
    await localVideoRef.current?.play().catch(() => {});
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
          context.fillText("KalanPro · séance en direct", canvas.width / 2, canvas.height / 2);
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
          anchor.download = `kalanpro-session-${sessionId}-${new Date().toISOString().replace(/[:.]/g, "-")}.webm`;
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

  function uniqueCodeFilePath(value: string, ignoreId?: string) {
    const normalized = value.replace(/\\/g, "/").replace(/^\/+/, "").split("/").filter((part) => part && part !== "." && part !== "..").join("/").slice(0, 120) || "file.txt";
    const occupied = new Set(codeFiles.filter((file) => file.id !== ignoreId).map((file) => file.path.toLowerCase()));
    if (!occupied.has(normalized.toLowerCase())) return normalized;
    const slash = normalized.lastIndexOf("/");
    const directory = slash >= 0 ? normalized.slice(0, slash + 1) : "";
    const filename = slash >= 0 ? normalized.slice(slash + 1) : normalized;
    const dot = filename.lastIndexOf(".");
    const stem = dot > 0 ? filename.slice(0, dot) : filename;
    const extension = dot > 0 ? filename.slice(dot) : "";
    let index = 2;
    let candidate = `${directory}${stem}-${index}${extension}`;
    while (occupied.has(candidate.toLowerCase())) candidate = `${directory}${stem}-${++index}${extension}`;
    return candidate.slice(0, 120);
  }

  function updateActiveProjectFile(patch: Partial<CodeProjectFile>) {
    setCodeFiles((current) => current.map((file) => file.id === activeCodeFileId ? { ...file, ...patch } : file));
  }

  function updateActiveCodeText(value: string) {
    const otherChars = codeFiles.reduce((total, file) => total + (file.id === activeCodeFileId ? 0 : file.content.length), 0);
    const available = Math.max(0, Math.min(100000, 220000 - otherChars));
    const content = value.slice(0, available);
    if (value.length > available) setNotice("Le projet collaboratif est limité à 220 000 caractères au total.");
    setCodeText(content);
    updateActiveProjectFile({ content });
  }

  function updateCodeLanguage(language: CodeLanguage) {
    setCodeLanguage(language);
    const extensions: Record<CodeLanguage, string> = { javascript: "js", html: "html", css: "css", python: "py", java: "java", c: "c", cpp: "cpp", text: "txt" };
    const current = codeFiles.find((file) => file.id === activeCodeFileId);
    const path = current?.path || codeFileName;
    const base = path.replace(/\.[^./]+$/, "") || "main";
    const nextPath = uniqueCodeFilePath(`${base}.${extensions[language]}`, activeCodeFileId);
    setCodeFileName(nextPath);
    updateActiveProjectFile({ language, path: nextPath });
    setCodeOutput("");
  }

  function renameCodeFile(value: string) {
    const safe = uniqueCodeFilePath(value, activeCodeFileId);
    setCodeFileName(safe);
    const language = languageFromPath(safe);
    setCodeLanguage(language);
    updateActiveProjectFile({ path: safe, language });
  }

  function selectCodeFile(id: string) {
    const file = codeFiles.find((item) => item.id === id);
    if (!file) return;
    setActiveCodeFileId(file.id);
    setCodeFileName(file.path);
    setCodeLanguage(file.language);
    setCodeText(file.content);
    setCodeOutput("");
  }

  function addCodeFile() {
    if (codeFiles.length >= 30) { setNotice("Le projet est limité à 30 fichiers dans la salle live."); return; }
    const id = `file-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const existing = new Set(codeFiles.map((file) => file.path));
    let n = 1; let path = "nouveau.py";
    while (existing.has(path)) path = `nouveau-${++n}.py`;
    const file: CodeProjectFile = { id, path, language: "python", content: "" };
    setCodeFiles((current) => [...current, file]);
    setActiveCodeFileId(id); setCodeFileName(path); setCodeLanguage("python"); setCodeText(""); setCodeOutput("");
  }

  function removeCodeFile(id: string) {
    if (codeFiles.length <= 1) { setNotice("Un projet doit conserver au moins un fichier."); return; }
    const remaining = codeFiles.filter((file) => file.id !== id);
    setCodeFiles(remaining);
    if (id === activeCodeFileId) {
      const next = remaining[0];
      setActiveCodeFileId(next.id); setCodeFileName(next.path); setCodeLanguage(next.language); setCodeText(next.content); setCodeOutput("");
    }
  }

  function changeCodeFramework(framework: CodeFramework) {
    if (framework !== codeFramework && codeFiles.some((file) => file.content.trim()) && !confirm("Charger ce modèle va remplacer les fichiers actuels du projet. Continuer ?")) return;
    const files = projectTemplate(framework);
    const first = files[0];
    setCodeFramework(framework); setCodeFiles(files); setActiveCodeFileId(first.id);
    setCodeFileName(first.path); setCodeLanguage(first.language); setCodeText(first.content); setCodeOutput("");
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

  async function runCode() {
    if (codeRunning) return;
    setCodeRunning(true);
    setCodeOutput("");
    const nonce = ++codeRunNonceRef.current;

    if (codeFramework !== "none") {
      setCodeOutput(`Projet ${codeFramework} multi-fichiers prêt pour l'édition et la collaboration. Son exécution complète requiert un runner serveur isolé et n'est pas lancée dans le navigateur.`);
      setCodeRunning(false);
      return;
    }
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
      const runner = codeRunnerRef.current?.contentWindow;
      if (!runner) {
        setCodeOutput("Erreur Python: runner isolé indisponible.");
        setCodeRunning(false);
        return;
      }
      setCodeOutput("Chargement du moteur Python isolé…");
      runner.postMessage({
        source: "learneas-code-parent",
        runtime: "python",
        nonce,
        active: codeFileName,
        files: codeFiles.filter((item) => item.path.toLowerCase().endsWith(".py")).map((item) => ({ path: item.path, content: item.content })),
      }, "*");
      return;
    }

    if (codeLanguage !== "javascript") {
      setCodeOutput(`L'exécution locale n'est pas disponible pour ${codeLanguage}. Utilisez JavaScript, Python, HTML ou CSS.`);
      setCodeRunning(false);
      return;
    }

    const runner = codeRunnerRef.current?.contentWindow;
    if (!runner) {
      setCodeOutput("Erreur JavaScript: runner isolé indisponible.");
      setCodeRunning(false);
      return;
    }
    runner.postMessage({
      source: "learneas-code-parent",
      runtime: "javascript",
      nonce,
      code: codeText,
    }, "*");
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

  const activeScreenShareUserId = screenSharing ? room.user.id : remoteScreenShareUserId;
  const screenShareActive = activeScreenShareUserId !== null;
  const remoteScreenShareFeed = remoteScreenShareUserId !== null
    ? (remoteFeeds.find((feed) => feed.userId === remoteScreenShareUserId) || null)
    : null;
  const effectiveVideoLayout: "solo" | "gallery" | "focus" = shareExpanded && screenShareActive
    ? "focus"
    : videoLayout === "auto"
      ? (remoteFeeds.length === 0 ? (screenSharing ? "focus" : "solo") : "gallery")
      : videoLayout;
  const organizerIsLocal = room.organizer.id === room.user.id;
  const focusedRemoteFeed = shareExpanded && remoteScreenShareFeed
    ? remoteScreenShareFeed
    : organizerIsLocal
      ? null
      : (remoteFeeds.find((feed) => feed.userId === room.organizer.id) || remoteFeeds[0] || null);
  const focusLocal = shareExpanded && screenSharing ? true : !focusedRemoteFeed;

  const localTile = (compact = false, className = "") => (
    <VideoTile
      title="Vous"
      subtitle={screenSharing ? (cameraOn ? "Écran + caméra" : "Partage d'écran") : room.is_organizer ? "Organisateur" : "Participant"}
      videoRef={localVideoRef}
      muted
      footer={screenSharing ? "Écran partagé" : cameraOn ? "Caméra active" : "Caméra coupée"}
      handRaised={myHandRaised}
      avatar={room.user.avatar}
      videoEnabled={screenSharing || cameraOn}
      objectFit={screenSharing ? "contain" : "cover"}
      compact={compact}
      className={className}
    >
      {screenSharing && (
        <PresenterPip
          videoRef={presenterCameraRef}
          cameraOn={cameraOn}
          avatar={room.user.avatar}
          name={room.user.name}
          position={presenterPipPosition}
          onPositionChange={(position) => {
            presenterPipPositionRef.current = position;
            setPresenterPipPosition(position);
          }}
        />
      )}
    </VideoTile>
  );

  const remoteTile = (feed: RemoteFeed, compact = false, className = "") => (
    <RemoteVideo
      key={feed.userId}
      feed={feed}
      compact={compact}
      className={className}
      handRaised={Boolean(people.find((person) => person.user_id === feed.userId)?.hand_raised)}
      avatar={people.find((person) => person.user_id === feed.userId)?.avatar || null}
      onElement={(element) => {
        if (element) remoteVideoElementsRef.current.set(feed.userId, element);
        else remoteVideoElementsRef.current.delete(feed.userId);
      }}
    />
  );

  return (
    <div className="fixed inset-0 z-[100] h-[100dvh] overflow-hidden bg-gray-950 text-white">
      <div className="mx-auto flex h-full max-w-[1820px] flex-col px-2.5 py-2.5 sm:px-4">
        <div className="mb-2 grid shrink-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2 gap-y-1 xl:grid-cols-[minmax(260px,1fr)_auto_minmax(260px,1fr)]">
          <div className="flex min-w-0 items-center gap-2.5">
            {room.organizer.avatar ? <img loading="lazy" decoding="async" src={room.organizer.avatar} alt="" className="h-8 w-8 shrink-0 rounded-full object-cover ring-1 ring-white/10" /> : <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-500/20 text-[11px] font-bold text-brand-200">{room.organizer.name.charAt(0).toUpperCase()}</span>}
            <div className="min-w-0">
              <p className="truncate text-[9px] font-semibold uppercase tracking-[0.16em] text-brand-300">Salle KalanPro · Séance {room.session_number} · {room.organizer.name}</p>
              <h1 className="mt-0.5 max-w-[300px] truncate text-base font-bold sm:max-w-[420px] sm:text-lg 2xl:max-w-[520px]" title={room.title}>{room.title}</h1>
            </div>
          </div>
          {!metricsCollapsed && (
            <div className="order-3 col-span-2 flex min-w-0 items-center justify-center gap-1.5 overflow-x-auto xl:order-none xl:col-span-1">
              <InlineMetric icon={<Users size={16} />} label="Participants" value={`${participantsCount}`} />
              <InlineMetric icon={<Hand size={16} />} label="Mains" value={`${raisedHandsCount}`} />
              <InlineMetric icon={<StopCircle size={16} />} label="Live" value={elapsedLabel} />
              <InlineMetric icon={<Monitor size={16} />} label="Planifié" value={`${room.planned_duration_minutes} min`} />
            </div>
          )}
          <div className="flex shrink-0 items-center justify-self-end gap-1 overflow-x-auto">
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
                    framework={codeFramework}
                    files={codeFiles}
                    activeFileId={activeCodeFileId}
                    output={codeOutput}
                    running={codeRunning}
                    runnerRef={codeRunnerRef}
                    onFrameworkChange={changeCodeFramework}
                    onSelectFile={selectCodeFile}
                    onAddFile={addCodeFile}
                    onRemoveFile={removeCodeFile}
                    onLanguageChange={updateCodeLanguage}
                    onFileNameChange={renameCodeFile}
                    onCodeChange={updateActiveCodeText}
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
                          {screenSharing
                            ? "Vous partagez votre écran sans quitter la vue de réunion."
                            : remoteScreenShareUserId !== null
                              ? `${people.find((person) => person.user_id === remoteScreenShareUserId)?.name || "Un participant"} partage son écran.`
                              : "Vue vidéo de la séance en temps réel."}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        {screenShareActive && (
                          <button
                            onClick={() => setShareExpanded((current) => !current)}
                            className="toolbar-secondary !px-2 !py-1.5 !text-[10px]"
                            title={shareExpanded ? "Réduire le partage et retrouver tous les participants" : "Agrandir le partage d'écran"}
                          >
                            {shareExpanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
                            {shareExpanded ? "Revenir à la réunion" : "Agrandir le partage"}
                          </button>
                        )}
                        <label className="sr-only" htmlFor="video-layout">Disposition vidéo</label>
                        <select id="video-layout" value={videoLayout} onChange={(event) => { setVideoLayout(event.target.value as VideoLayout); setShareExpanded(false); }} className="rounded-xl border border-white/10 bg-gray-950 px-2 py-1.5 text-[10px] font-medium text-gray-200 outline-none">
                          <option value="auto">Disposition : Auto</option>
                          <option value="gallery">Réunion / galerie</option>
                          <option value="focus">Intervenant</option>
                        </select>
                        <button onClick={toggleFullscreen} className="toolbar-secondary !px-2 !py-1.5 !text-[10px]">
                          <Maximize2 size={15} /> {fullscreen ? "Quitter le plein écran" : "Plein écran"}
                        </button>
                      </div>
                    </div>

                    {effectiveVideoLayout === "solo" ? (
                      <div className="relative min-h-0 flex-1 overflow-hidden rounded-3xl border border-dashed border-white/10 bg-gray-900/80">
                        <div className="absolute inset-0 grid place-items-center p-5 text-center text-[11px] text-gray-500 sm:text-xs">
                          <div>
                            <Users size={32} className="mx-auto mb-2" />
                            <p className="font-medium text-gray-300">En attente des autres participants...</p>
                            <p className="mt-1 text-xs text-gray-500">Votre caméra reste en vignette. Les nouveaux flux apparaîtront automatiquement.</p>
                          </div>
                        </div>
                        <div className="absolute bottom-3 right-3 z-20 aspect-video w-[min(310px,44%)] min-w-[190px] max-w-[310px] sm:bottom-4 sm:right-4">
                          {localTile(true, "h-full shadow-2xl ring-1 ring-white/10")}
                        </div>
                      </div>
                    ) : effectiveVideoLayout === "gallery" ? (
                      <div className="grid min-h-0 flex-1 grid-cols-1 gap-2.5 overflow-y-auto sm:grid-cols-2 2xl:grid-cols-3">
                        {localTile(false, "h-full")}
                        {remoteFeeds.map((feed) => remoteTile(feed, false, "h-full"))}
                      </div>
                    ) : (
                      <div className="flex min-h-0 flex-1 flex-col gap-2.5">
                        <div className="min-h-0 flex-1">
                          {focusLocal ? localTile(false, "h-full") : focusedRemoteFeed ? remoteTile(focusedRemoteFeed, false, "h-full") : localTile(false, "h-full")}
                        </div>
                        {(remoteFeeds.length > 0 || !focusLocal) && (
                          <div className="grid max-h-[150px] shrink-0 grid-cols-2 gap-2 overflow-y-auto sm:grid-cols-3 lg:grid-cols-4">
                            {!focusLocal && localTile(true, "h-full")}
                            {remoteFeeds.filter((feed) => focusLocal || feed.userId !== focusedRemoteFeed?.userId).map((feed) => remoteTile(feed, true, "h-full"))}
                          </div>
                        )}
                      </div>
                    )}
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
                              {person.avatar ? <img loading="lazy" decoding="async" src={person.avatar} alt="" className="h-8 w-8 shrink-0 rounded-full object-cover" /> : <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-500/20 text-[11px] font-bold text-brand-200">{person.name.charAt(0).toUpperCase()}</span>}
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
                    <select value={selectedVideoInput} onChange={(e) => switchVideoDevice(e.target.value)} disabled={recording || screenSharing} className="mt-1.5 w-full rounded-xl border border-white/10 bg-gray-950 px-2.5 py-1.5 text-[11px] text-white sm:text-xs">
                      {videoInputs.map((device) => <option key={device.deviceId} value={device.deviceId}>{device.label}</option>)}
                    </select>
                  </label>
                </div>
                {recording && <p className="mt-3 text-xs text-amber-300">Arrêtez l'enregistrement avant de changer de périphérique.</p>}
              </div>
            )}

            <div className={`fixed bottom-2 left-1/2 z-20 flex max-w-[calc(100%-1rem)] -translate-x-1/2 flex-nowrap items-center justify-center gap-1 overflow-x-auto whitespace-nowrap rounded-2xl border border-white/10 bg-gray-900/95 shadow-2xl backdrop-blur pointer-events-auto ${controlsCompact ? "px-1.5 py-1" : "w-auto lg:min-w-[980px] max-w-[1600px] px-2.5 py-1.5"}`}>
              <button type="button" onClick={() => setControlsCompact((value) => !value)} className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white/10 text-gray-200 hover:bg-white/20" title={controlsCompact ? "Déployer les contrôles" : "Réduire les contrôles"}>{controlsCompact ? <ChevronsRight size={14} /> : <ChevronsLeft size={14} />}</button>
              <ControlButton compact={controlsCompact} active={micOn} onClick={toggleMic} label={micOn ? "Micro" : "Micro coupé"}>{micOn ? <Mic size={15} /> : <MicOff size={15} />}</ControlButton>
              <ControlButton compact={controlsCompact} active={cameraOn} onClick={() => void toggleCamera()} label={cameraOn ? (screenSharing ? "Masquer la caméra du présentateur" : "Caméra") : (screenSharing ? "Afficher la caméra du présentateur" : "Caméra coupée")}>{cameraOn ? <Video size={15} /> : <VideoOff size={15} />}</ControlButton>
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
  framework,
  files,
  activeFileId,
  output,
  running,
  runnerRef,
  onFrameworkChange,
  onSelectFile,
  onAddFile,
  onRemoveFile,
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
  framework: CodeFramework;
  files: CodeProjectFile[];
  activeFileId: string;
  output: string;
  running: boolean;
  runnerRef: React.RefObject<HTMLIFrameElement>;
  onFrameworkChange: (framework: CodeFramework) => void;
  onSelectFile: (id: string) => void;
  onAddFile: () => void;
  onRemoveFile: (id: string) => void;
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
  const canRun = framework === "none" && ["javascript", "python", "html", "css"].includes(language);
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
          <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-brand-500/20 text-brand-200"><Code2 size={15} /></div>
          <div className="min-w-0"><h2 className="truncate text-xs font-semibold text-white">Éditeur partagé</h2><p className="text-[9px] text-gray-500">Coloration syntaxique et synchronisation en direct.</p></div>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <button type="button" onClick={onBackToVideo} className="toolbar-secondary !px-2 !py-1 !text-[10px]"><Video size={13} /> Vidéo</button>
          <button type="button" onClick={onCopy} className="toolbar-secondary !px-2 !py-1 !text-[10px]"><Copy size={13} /> Copier</button>
          <button type="button" onClick={onDownload} className="toolbar-secondary !px-2 !py-1 !text-[10px]"><Download size={13} /> Télécharger</button>
          <button type="button" onClick={() => setConsoleCollapsed((value) => !value)} className="toolbar-secondary !px-2 !py-1 !text-[10px]">{consoleCollapsed ? <PanelRightOpen size={12} /> : <PanelRightClose size={12} />} Console</button>
          <button type="button" onClick={onRun} disabled={running || !canRun} title={canRun ? "Exécuter le code" : framework !== "none" ? "Le projet framework est éditable/collaboratif ; son runtime serveur isolé n’est pas activé dans la réunion." : "Exécution locale disponible pour JavaScript, Python, HTML et CSS"} className="toolbar-success !px-2 !py-1 !text-[10px] disabled:cursor-not-allowed disabled:opacity-45">{running ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />} {running ? "Exécution…" : "Exécuter"}</button>
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-1.5 border-b border-white/10 bg-black/20 px-2.5 py-1.5">
        <label className="flex items-center gap-1 text-[10px] text-gray-400">Projet<select value={framework} onChange={(event) => onFrameworkChange(event.target.value as CodeFramework)} className="rounded-lg border border-white/10 bg-gray-950 px-2 py-1 text-[11px] text-white outline-none focus:border-brand-400"><option value="none">Libre / POO</option><option value="react">React</option><option value="nextjs">Next.js</option><option value="django">Django</option><option value="drf">Django REST</option><option value="fastapi">FastAPI</option><option value="flask">Flask</option><option value="express">Node / Express</option></select></label>
        <label className="flex items-center gap-1 text-[10px] text-gray-400">Langage<select value={language} onChange={(event) => onLanguageChange(event.target.value as CodeLanguage)} className="rounded-lg border border-white/10 bg-gray-950 px-2 py-1 text-[11px] text-white outline-none focus:border-brand-400"><option value="javascript">JavaScript</option><option value="html">HTML</option><option value="css">CSS</option><option value="python">Python</option><option value="java">Java</option><option value="c">C</option><option value="cpp">C++</option><option value="text">Texte</option></select></label>
        <label className="flex items-center gap-1 text-[10px] text-gray-400">Thème<select value={theme} onChange={(event) => setTheme(event.target.value as CodeTheme)} className="rounded-lg border border-white/10 bg-gray-950 px-2 py-1 text-[11px] text-white outline-none focus:border-brand-400"><option value="midnight">Midnight</option><option value="dracula">Dracula</option><option value="light">Clair</option></select></label>
        <label className="flex min-w-0 flex-1 items-center gap-1 text-[10px] text-gray-400">Fichier<input value={fileName} onChange={(event) => onFileNameChange(event.target.value.slice(0, 120))} className="min-w-[110px] max-w-xs flex-1 rounded-lg border border-white/10 bg-gray-950 px-2 py-1 font-mono text-[11px] text-white outline-none focus:border-brand-400" /></label>
        <span className="rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-300">Live</span>
      </div>
      <div className="flex shrink-0 items-center gap-1 overflow-x-auto border-b border-white/10 bg-black/10 px-2 py-1">
        <FolderOpen size={13} className="mr-1 shrink-0 text-gray-500" />
        {files.map((file) => <div key={file.id} className={`flex shrink-0 items-center rounded-lg border ${file.id === activeFileId ? "border-brand-400/40 bg-brand-400/10" : "border-white/10 bg-white/[0.03]"}`}><button type="button" onClick={() => onSelectFile(file.id)} className="max-w-[180px] truncate px-2 py-1 font-mono text-[10px] text-gray-200" title={file.path}>{file.path}</button>{files.length > 1 && <button type="button" onClick={() => onRemoveFile(file.id)} className="px-1.5 text-gray-500 hover:text-red-300" aria-label={`Fermer ${file.path}`}><X size={11} /></button>}</div>)}
        <button type="button" onClick={onAddFile} disabled={files.length >= 30} className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-dashed border-white/20 px-2 py-1 text-[10px] text-gray-400 hover:text-white disabled:opacity-40"><FilePlus size={11} /> Fichier</button>
      </div>

      <div ref={editorGridRef} className="grid min-h-0 flex-1" style={{ gridTemplateColumns: consoleCollapsed ? "minmax(0,1fr)" : `minmax(0, ${100 - consolePercent}fr) 5px minmax(190px, ${consolePercent}fr)` }}>
        <div className="relative min-h-0 overflow-hidden border-r border-white/10 font-mono text-[12px] leading-5" style={{ background: palette.background }}>
          <div className="absolute inset-y-0 left-0 z-20 w-10 overflow-hidden border-r border-white/10 bg-black/20 text-right" style={{ color: palette.lineNumber }} aria-hidden="true"><div style={{ transform: `translateY(-${scrollTop}px)` }} className="py-2.5 pr-2">{lineNumbers.map((line) => <div key={line} className="h-5 select-none">{line}</div>)}</div></div>
          <pre aria-hidden="true" className="pointer-events-none absolute inset-0 m-0 overflow-hidden whitespace-pre py-2.5 pl-12 pr-3 font-mono text-[12px] leading-5" style={{ color: palette.text }}><code style={{ display: "block", transform: `translate(${-scrollLeft}px, ${-scrollTop}px)` }} dangerouslySetInnerHTML={{ __html: highlighted }} /></pre>
          <textarea ref={textareaRef} value={code} onChange={(event) => onCodeChange(event.target.value.slice(0, 100000))} maxLength={100000} onKeyDown={handleEditorKeyDown} onScroll={(event) => { setScrollTop(event.currentTarget.scrollTop); setScrollLeft(event.currentTarget.scrollLeft); }} spellCheck={false} autoCapitalize="off" autoCorrect="off" className="absolute inset-0 z-10 h-full w-full resize-none overflow-auto bg-transparent py-2.5 pl-12 pr-3 font-mono text-[12px] leading-5 text-transparent outline-none selection:bg-brand-500/25" style={{ caretColor: theme === "light" ? "#0f172a" : "#ffffff" }} aria-label="Éditeur de code KalanPro" />
        </div>

        {!consoleCollapsed && <>
          <div role="separator" aria-label="Redimensionner la console" aria-orientation="vertical" className="cursor-col-resize bg-white/5 transition hover:bg-brand-500/50" onPointerDown={(event) => { draggingRef.current = true; event.currentTarget.setPointerCapture(event.pointerId); }} onPointerMove={(event) => { if (draggingRef.current) resizeConsoleFromPointer(event.clientX); }} onPointerUp={(event) => { draggingRef.current = false; event.currentTarget.releasePointerCapture(event.pointerId); }} onPointerCancel={() => { draggingRef.current = false; }} />
          <div className="flex min-h-0 flex-col bg-[#0a0f1b]">
            <div className="flex shrink-0 items-center justify-between border-b border-white/10 px-2.5 py-1.5"><p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Résultat / Console</p><div className="flex items-center gap-1"><button type="button" onClick={() => setConsolePercent((value) => Math.max(value - 10, 18))} className="rounded-md bg-white/5 p-1 text-gray-300 hover:bg-white/10" title="Réduire la console"><Minus size={11} /></button><button type="button" onClick={() => setConsolePercent((value) => Math.min(value + 10, 62))} className="rounded-md bg-white/5 p-1 text-gray-300 hover:bg-white/10" title="Agrandir la console"><Plus size={11} /></button></div></div>
            {language === "html" ? <iframe title="Aperçu HTML" sandbox="" referrerPolicy="no-referrer" srcDoc={`<!doctype html><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; font-src data:">${code}`} className="min-h-0 flex-1 bg-white" /> : language === "css" ? <iframe title="Aperçu CSS" sandbox="" referrerPolicy="no-referrer" srcDoc={`<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><style>${code}</style></head><body><main class="demo"><h1>Aperçu CSS</h1><p>Modifiez les styles pour voir le résultat.</p><button>Exemple de bouton</button></main></body></html>`} className="min-h-0 flex-1 bg-white" /> : <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap break-words p-2.5 font-mono text-[11px] leading-[18px] text-gray-300">{output || (language === "python" ? "Cliquez sur Exécuter. Le moteur Python sera chargé au premier lancement." : language === "javascript" ? "Cliquez sur Exécuter pour afficher la console." : "Ce langage reste éditable et partageable, mais son exécution locale est désactivée.")}</pre>}
          </div>
        </>}
      </div>
      <iframe ref={runnerRef} src="/code-runner/index.html" title="Exécution de code isolée" sandbox="allow-scripts" referrerPolicy="no-referrer" className="hidden" />
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

function InlineMetric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <span className="inline-flex h-10 shrink-0 items-center gap-2 rounded-xl border border-white/10 bg-white/[0.065] px-3.5 text-[11px] font-medium text-gray-300 shadow-sm shadow-black/10">
      <span className="text-brand-200">{icon}</span>
      <span>{label}</span>
      <strong className="text-[13px] font-semibold text-white">{value}</strong>
    </span>
  );
}

function SidebarButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button type="button" onClick={onClick} className={`rounded-xl px-2 py-1 text-[10px] font-semibold transition sm:text-[11px] ${active ? "bg-white text-gray-950" : "text-gray-300 hover:bg-white/5"}`}>{children}</button>;
}

function MiniAction({ onClick, danger, children }: { onClick: () => void; danger?: boolean; children: React.ReactNode }) {
  return <button type="button" onClick={onClick} className={`rounded-lg px-1.5 py-1 text-[9px] font-semibold transition ${danger ? "bg-red-500/10 text-red-300 hover:bg-red-500/20" : "bg-white/10 text-gray-300 hover:bg-white/20"}`}>{children}</button>;
}

function EmptyPanel({ children }: { children: React.ReactNode }) {
  return <div className="rounded-2xl border border-dashed border-white/10 p-3 text-[11px] text-gray-400 sm:text-xs">{children}</div>;
}

function ControlButton({ active, label, onClick, disabled, children, compact = false }: { active: boolean; label: string; onClick: () => void; disabled?: boolean; children: React.ReactNode; compact?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} title={label} className={`inline-flex shrink-0 items-center justify-center rounded-xl font-medium transition ${compact ? "h-8 w-8 p-0" : "gap-1 px-2.5 py-1.5 text-[11px]"} ${active ? "bg-brand-600 text-white" : "bg-white/10 text-gray-200 hover:bg-white/20"} ${disabled ? "cursor-not-allowed opacity-50" : ""}`}>
      {children}{!compact && <span>{label}</span>}
    </button>
  );
}

function VideoTile({ title, subtitle, footer, videoRef, muted, handRaised, avatar, videoEnabled = true, objectFit = "cover", compact = false, className = "", children }: { title: string; subtitle: string; footer: string; videoRef: React.RefObject<HTMLVideoElement>; muted?: boolean; handRaised?: boolean; avatar?: string | null; videoEnabled?: boolean; objectFit?: "cover" | "contain"; compact?: boolean; className?: string; children?: React.ReactNode }) {
  const initial = title.trim().charAt(0).toUpperCase() || "U";
  return (
    <div className={`relative overflow-hidden rounded-2xl border bg-black ${compact ? "min-h-[105px]" : "min-h-[170px]"} ${handRaised ? "border-amber-400/60" : "border-white/10"} ${className}`}>
      <video ref={videoRef} autoPlay playsInline muted={muted} className={`h-full w-full ${compact ? "min-h-[105px]" : "min-h-[170px]"} ${objectFit === "contain" ? "object-contain" : "object-cover"} transition-opacity ${videoEnabled ? "opacity-100" : "opacity-0"}`} />
      {!videoEnabled && (
        <div className="absolute inset-0 grid place-items-center bg-gradient-to-br from-gray-900 to-gray-950">
          <div className="text-center">
            {avatar ? <img loading="lazy" decoding="async" src={avatar} alt="" className="mx-auto h-16 w-16 rounded-full object-cover ring-2 ring-white/10" /> : <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-brand-500/20 text-2xl font-bold text-brand-200 ring-2 ring-white/10">{initial}</div>}
            <p className="mt-2 text-xs font-semibold text-white">{title}</p>
            <p className="text-[10px] text-gray-500">Caméra désactivée</p>
          </div>
        </div>
      )}
      {children}
      <div className="pointer-events-none absolute left-2 top-2 flex max-w-[75%] items-center gap-2 rounded-full bg-black/60 py-1 pl-1 pr-2.5 backdrop-blur">
        {avatar ? <img loading="lazy" decoding="async" src={avatar} alt="" className="h-6 w-6 rounded-full object-cover" /> : <span className="grid h-6 w-6 place-items-center rounded-full bg-brand-500/20 text-[10px] font-bold text-brand-200">{initial}</span>}
        <div className="min-w-0 leading-tight"><div className="flex items-center gap-1"><p className="truncate text-[10px] font-semibold text-white">{title}</p>{handRaised && <Hand size={11} className="shrink-0 text-amber-300" />}</div><p className="truncate text-[8px] text-gray-400">{subtitle}</p></div>
      </div>
      <span className="pointer-events-none absolute right-2 top-2 rounded-full bg-black/60 px-2 py-1 text-[8px] text-gray-300 backdrop-blur">{footer}</span>
    </div>
  );
}

function PresenterPip({ videoRef, cameraOn, avatar, name, position, onPositionChange }: { videoRef: React.RefObject<HTMLVideoElement>; cameraOn: boolean; avatar?: string | null; name: string; position: { x: number; y: number }; onPositionChange: (position: { x: number; y: number }) => void }) {
  const dragRef = useRef<{ pointerId: number; startX: number; startY: number; originX: number; originY: number } | null>(null);
  const initial = name.trim().charAt(0).toUpperCase() || "U";

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: position.x,
      originY: position.y,
    };
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const element = event.currentTarget;
    const parent = element.parentElement;
    if (!parent) return;
    const rect = parent.getBoundingClientRect();
    const maxX = Math.max(0, 1 - element.offsetWidth / Math.max(1, rect.width) - 0.006);
    const maxY = Math.max(0, 1 - element.offsetHeight / Math.max(1, rect.height) - 0.006);
    const nextX = Math.min(maxX, Math.max(0.006, drag.originX + (event.clientX - drag.startX) / Math.max(1, rect.width)));
    const nextY = Math.min(maxY, Math.max(0.006, drag.originY + (event.clientY - drag.startY) / Math.max(1, rect.height)));
    onPositionChange({ x: nextX, y: nextY });
  };

  const endDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (dragRef.current?.pointerId === event.pointerId) dragRef.current = null;
    try { event.currentTarget.releasePointerCapture(event.pointerId); } catch {}
  };

  return (
    <div
      role="group"
      aria-label="Vignette du présentateur, déplaçable"
      title="Glissez pour déplacer votre vignette"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      className="absolute z-20 aspect-video w-[22%] min-w-[120px] max-w-[240px] cursor-grab touch-none select-none overflow-hidden rounded-xl border-2 border-white/90 bg-gray-900 shadow-2xl active:cursor-grabbing"
      style={{ left: `${position.x * 100}%`, top: `${position.y * 100}%` }}
    >
      {cameraOn ? (
        <video ref={videoRef} autoPlay playsInline muted className="h-full w-full object-cover" />
      ) : (
        <div className="grid h-full w-full place-items-center bg-gradient-to-br from-gray-800 to-gray-950">
          {avatar ? <img loading="lazy" decoding="async" src={avatar} alt="" className="h-14 w-14 rounded-full object-cover ring-2 ring-white/20" /> : <div className="grid h-14 w-14 place-items-center rounded-full bg-brand-600 text-lg font-bold text-white">{initial}</div>}
        </div>
      )}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-between bg-gradient-to-t from-black/80 to-transparent px-2 pb-1.5 pt-5 text-[9px] font-medium text-white">
        <span className="truncate">{name}</span>
        <Move size={12} className="shrink-0 opacity-80" />
      </div>
    </div>
  );
}

function RemoteVideo({ feed, handRaised, avatar, onElement, compact = false, className = "" }: { feed: RemoteFeed; handRaised: boolean; avatar?: string | null; onElement: (element: HTMLVideoElement | null) => void; compact?: boolean; className?: string }) {
  const ref = useRef<HTMLVideoElement | null>(null);
  useEffect(() => {
    const element = ref.current;
    if (element) {
      element.srcObject = feed.stream;
      onElement(element);
    }
    return () => onElement(null);
  }, [feed.stream, onElement]);

  return <VideoTile title={feed.name} subtitle="Participant" footer="En direct" videoRef={ref} handRaised={handRaised} avatar={avatar} compact={compact} className={className} />;
}

function inviteStatusLabel(status: SessionInvite["status"]) {
  if (status === "accepted") return "A rejoint la séance";
  if (status === "account_exists") return "Compte KalanPro trouvé";
  if (status === "pending_account") return "En attente de création du compte";
  return "Invitation révoquée";
}

function formatBytes(value: number) {
  if (!Number.isFinite(value) || value <= 0) return "0 o";
  const units = ["o", "Ko", "Mo", "Go"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  return `${(value / 1024 ** index).toLocaleString("fr-FR", { maximumFractionDigits: index === 0 ? 0 : 1 })} ${units[index]}`;
}
