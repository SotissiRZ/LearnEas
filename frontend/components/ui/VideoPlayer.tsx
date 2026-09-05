"use client";

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import Hls from "hls.js";
import {
  Captions,
  Headphones,
  Loader2,
  Maximize,
  Minimize,
  Pause,
  PictureInPicture2,
  Play,
  RotateCcw,
  Settings,
  SkipBack,
  SkipForward,
  Volume1,
  Volume2,
  VolumeX,
  Wifi,
  WifiOff,
  Wrench,
} from "lucide-react";
import { resolveMediaUrl } from "@/lib/media";

type StreamingVariant = {
  height: number;
  width?: number;
  bandwidth?: number;
};

type Props = {
  src: string;
  hlsSrc?: string | null;
  dataSaverHlsSrc?: string | null;
  audioHlsSrc?: string | null;
  offlineSrc?: string | null;
  streamingVariants?: StreamingVariant[];
  streamingStatus?: "pending" | "processing" | "ready" | "failed" | string;
  poster?: string | null;
  title?: string;
  subtitlesUrl?: string | null;
  initialTime?: number;
  autoPlayOnLoad?: boolean;
  onEnded?: (seconds: number, duration: number, watchedDeltaSeconds: number) => void;
  onProgress?: (seconds: number, duration: number, watchedDeltaSeconds: number) => void;
  onTimeChange?: (seconds: number, duration: number) => void;
  onRepair?: () => Promise<void>;
};

export type VideoPlayerHandle = {
  seekTo: (seconds: number) => void;
  play: () => Promise<void>;
  pause: () => void;
  getCurrentTime: () => number;
  getDuration: () => number;
};

type EmbedSource = { kind: "youtube" | "vimeo"; url: string };
type QualityChoice = "auto" | number;
type DataSaverMode = "auto" | "on" | "off";

type NetworkInformationLike = EventTarget & {
  effectiveType?: string;
  saveData?: boolean;
  downlink?: number;
  rtt?: number;
};

type NavigatorWithConnection = Navigator & {
  connection?: NetworkInformationLike;
};

type NetworkState = {
  online: boolean;
  effectiveType: string;
  saveData: boolean;
  downlink: number | null;
  rtt: number | null;
};

function getEmbedSource(value: string): EmbedSource | null {
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase().replace(/^www\./, "");

    if (host === "youtu.be") {
      const id = url.pathname.split("/").filter(Boolean)[0];
      if (id) return { kind: "youtube", url: `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?rel=0&playsinline=1` };
    }
    if (host === "youtube.com" || host.endsWith(".youtube.com")) {
      let id = url.searchParams.get("v") || "";
      const parts = url.pathname.split("/").filter(Boolean);
      if (!id && ["embed", "shorts", "live"].includes(parts[0] || "")) id = parts[1] || "";
      if (id) return { kind: "youtube", url: `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?rel=0&playsinline=1` };
    }

    if (host === "vimeo.com" || host.endsWith(".vimeo.com")) {
      const match = url.pathname.match(/(?:video\/)?(\d{5,})/);
      if (match?.[1]) return { kind: "vimeo", url: `https://player.vimeo.com/video/${match[1]}?title=0&byline=0&portrait=0` };
    }
  } catch {
    return null;
  }
  return null;
}

function formatClock(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const rounded = Math.floor(seconds);
  const hours = Math.floor(rounded / 3600);
  const minutes = Math.floor((rounded % 3600) / 60);
  const secs = rounded % 60;
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`
    : `${minutes}:${String(secs).padStart(2, "0")}`;
}

function mediaErrorMessage(video: HTMLVideoElement | null): string {
  const code = video?.error?.code;
  if (code === 2) return "Erreur réseau pendant le chargement de la vidéo.";
  if (code === 3) return "Le navigateur n'arrive pas à décoder cette vidéo. Utilisez de préférence MP4 H.264/AAC ou WebM.";
  if (code === 4) return "Source vidéo non prise en charge. Vérifiez l'URL, le format ou le codec de la vidéo.";
  return "Impossible de charger cette vidéo. Vérifiez la source puis réessayez.";
}

function uniqueSortedHeights(values: number[]): number[] {
  return Array.from(new Set(values.filter((value) => Number.isFinite(value) && value > 0))).sort((a, b) => b - a);
}

function readNetworkState(): NetworkState {
  if (typeof navigator === "undefined") return { online: true, effectiveType: "", saveData: false, downlink: null, rtt: null };
  const connection = (navigator as NavigatorWithConnection).connection;
  return {
    online: navigator.onLine !== false,
    effectiveType: connection?.effectiveType || "",
    saveData: Boolean(connection?.saveData),
    downlink: Number.isFinite(connection?.downlink) ? Number(connection?.downlink) : null,
    rtt: Number.isFinite(connection?.rtt) ? Number(connection?.rtt) : null,
  };
}

function isConstrainedNetwork(network: NetworkState): boolean {
  return network.saveData || ["slow-2g", "2g"].includes(network.effectiveType) || (network.downlink != null && network.downlink > 0 && network.downlink < 0.8);
}

function initialBandwidthEstimate(network: NetworkState, dataSaver: boolean): number {
  if (dataSaver) return 320_000;
  if (network.downlink && network.downlink > 0) return Math.max(250_000, Math.min(5_000_000, network.downlink * 1_000_000 * 0.65));
  if (network.effectiveType === "2g" || network.effectiveType === "slow-2g") return 250_000;
  if (network.effectiveType === "3g") return 700_000;
  if (network.effectiveType === "4g") return 2_500_000;
  if (network.effectiveType === "5g") return 5_000_000;
  return 1_000_000;
}

function networkDisplayLabel(network: NetworkState): string {
  if (!network.online) return "Hors ligne";
  const effective = network.effectiveType.toLowerCase();
  if (effective === "slow-2g") return "2G lente";
  if (effective === "2g") return "2G";
  if (effective === "3g") return "3G";
  if (effective === "5g") return "5G";
  if (effective === "4g") {
    // Network Information API ne distingue généralement pas 5G : un débit élevé est présenté comme
    // connexion rapide 4G/5G sans prétendre identifier la technologie radio exacte.
    if ((network.downlink || 0) >= 8) return "Connexion rapide (4G/5G)";
    return "4G";
  }
  return "Réseau";
}

function usagePerHourLabel(bitsPerSecond: number | null): string {
  if (!bitsPerSecond || bitsPerSecond <= 0) return "";
  const megabytes = Math.round((bitsPerSecond * 3600) / 8 / 1_000_000);
  return `~${megabytes} Mo/h`;
}

const VideoPlayer = forwardRef<VideoPlayerHandle, Props>(function VideoPlayer(
  {
    src,
    hlsSrc,
    dataSaverHlsSrc,
    audioHlsSrc,
    offlineSrc,
    streamingVariants = [],
    streamingStatus,
    poster,
    title = "Vidéo",
    subtitlesUrl,
    initialTime = 0,
    autoPlayOnLoad = false,
    onEnded,
    onProgress,
    onTimeChange,
    onRepair,
  },
  ref,
) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const hlsRef = useRef<Hls | null>(null);
  const progressEmitRef = useRef(0);
  const watchedAccumulatorRef = useRef(0);
  const lastPlaybackPositionRef = useRef<number | null>(null);
  const resumeAppliedRef = useRef(false);
  const resumeTargetRef = useRef(initialTime);
  const resumeShouldPlayRef = useRef(autoPlayOnLoad);

  const resolvedSrc = useMemo(() => resolveMediaUrl(src), [src]);
  const resolvedHlsSrc = useMemo(() => hlsSrc ? resolveMediaUrl(hlsSrc) : null, [hlsSrc]);
  const resolvedDataSaverHlsSrc = useMemo(() => dataSaverHlsSrc ? resolveMediaUrl(dataSaverHlsSrc) : null, [dataSaverHlsSrc]);
  const resolvedAudioHlsSrc = useMemo(() => audioHlsSrc ? resolveMediaUrl(audioHlsSrc) : null, [audioHlsSrc]);
  const resolvedOfflineSrc = useMemo(() => offlineSrc ? resolveMediaUrl(offlineSrc) : null, [offlineSrc]);
  const resolvedSubtitles = useMemo(() => subtitlesUrl ? resolveMediaUrl(subtitlesUrl) : null, [subtitlesUrl]);
  const embed = useMemo(() => getEmbedSource(resolvedSrc), [resolvedSrc]);

  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [rate, setRate] = useState(1);
  const [fullscreen, setFullscreen] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [captionsEnabled, setCaptionsEnabled] = useState(Boolean(resolvedSubtitles));
  const [repairing, setRepairing] = useState(false);
  const [repairMessage, setRepairMessage] = useState("");
  const [audioOnly, setAudioOnly] = useState(false);
  const [dataSaverMode, setDataSaverMode] = useState<DataSaverMode>("auto");
  const [network, setNetwork] = useState<NetworkState>(() => readNetworkState());
  const [quality, setQuality] = useState<QualityChoice>("auto");
  const [hlsLevels, setHlsLevels] = useState<number[]>([]);
  const [activeHeight, setActiveHeight] = useState<number | null>(null);
  const [hlsActive, setHlsActive] = useState(false);

  const advertisedHeights = useMemo(
    () => uniqueSortedHeights(streamingVariants.map((variant) => variant.height)),
    [streamingVariants],
  );
  const qualityHeights = hlsLevels.length ? hlsLevels : advertisedHeights;
  const dataSaver = dataSaverMode === "on" || (dataSaverMode === "auto" && isConstrainedNetwork(network));
  const usingOfflineCopy = !network.online && Boolean(resolvedOfflineSrc);
  const playbackSrc = usingOfflineCopy && resolvedOfflineSrc ? resolvedOfflineSrc : resolvedSrc;
  const effectiveHlsSource = usingOfflineCopy
    ? null
    : audioOnly && resolvedAudioHlsSrc
      ? resolvedAudioHlsSrc
      : dataSaver && resolvedDataSaverHlsSrc
        ? resolvedDataSaverHlsSrc
        : resolvedHlsSrc;

  const estimatedBandwidth = useMemo(() => {
    if (audioOnly) return 48_000;
    const variants = streamingVariants.filter((variant) => Number(variant.bandwidth) > 0);
    if (!variants.length) return null;
    if (typeof quality === "number") {
      const exact = variants.find((variant) => variant.height === quality);
      if (exact?.bandwidth) return exact.bandwidth;
    }
    if (activeHeight) {
      const active = variants.find((variant) => variant.height === activeHeight);
      if (active?.bandwidth) return active.bandwidth;
    }
    const allowed = dataSaver ? variants.filter((variant) => variant.height <= 360) : variants;
    const pool = allowed.length ? allowed : variants;
    return Math.max(...pool.map((variant) => Number(variant.bandwidth) || 0));
  }, [audioOnly, streamingVariants, quality, activeHeight, dataSaver]);

  useImperativeHandle(ref, () => ({
    seekTo(seconds: number) {
      const video = videoRef.current;
      if (!video) return;
      const limit = Number.isFinite(video.duration) ? video.duration : Math.max(0, seconds);
      video.currentTime = Math.max(0, Math.min(limit, seconds));
      setCurrentTime(video.currentTime);
    },
    async play() {
      const video = videoRef.current;
      if (video) await video.play();
    },
    pause() {
      videoRef.current?.pause();
    },
    getCurrentTime() {
      return videoRef.current?.currentTime || 0;
    },
    getDuration() {
      return Number.isFinite(videoRef.current?.duration || NaN) ? (videoRef.current?.duration || 0) : 0;
    },
  }), []);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem("kalanpro:data-saver-mode");
      if (stored === "auto" || stored === "on" || stored === "off") {
        setDataSaverMode(stored);
      } else {
        // Migration transparente de l'ancien booléen v80. Sans préférence explicite,
        // le mode Auto est préférable pour les connexions mobiles variables.
        const legacy = window.localStorage.getItem("learneas:data-saver");
        if (legacy === "1") setDataSaverMode("on");
        else if (legacy === "0") setDataSaverMode("off");
      }
    } catch {
      // Le stockage local peut être bloqué en navigation privée stricte.
    }
  }, []);

  useEffect(() => {
    const connection = (navigator as NavigatorWithConnection).connection;
    const refresh = () => setNetwork(readNetworkState());
    window.addEventListener("online", refresh);
    window.addEventListener("offline", refresh);
    connection?.addEventListener?.("change", refresh);
    refresh();
    return () => {
      window.removeEventListener("online", refresh);
      window.removeEventListener("offline", refresh);
      connection?.removeEventListener?.("change", refresh);
    };
  }, []);

  useEffect(() => {
    const handler = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  useEffect(() => {
    if (!network.online) return;
    const hls = hlsRef.current;
    if (hls) {
      try { hls.startLoad(); } catch {}
    }
  }, [network.online]);

  const applyHlsPolicy = useCallback((hls: Hls, nextQuality: QualityChoice, saveData: boolean) => {
    const levels = hls.levels || [];
    if (!levels.length) return;

    if (saveData) {
      let capIndex = -1;
      levels.forEach((level, index) => {
        if ((level.height || 0) <= 360 && (capIndex < 0 || (level.height || 0) > (levels[capIndex]?.height || 0))) capIndex = index;
      });
      hls.autoLevelCapping = capIndex >= 0 ? capIndex : 0;
    } else {
      hls.autoLevelCapping = -1;
    }

    if (nextQuality === "auto") {
      hls.currentLevel = -1;
      hls.nextLevel = -1;
      return;
    }

    let selectedIndex = -1;
    let distance = Number.POSITIVE_INFINITY;
    levels.forEach((level, index) => {
      const delta = Math.abs((level.height || 0) - nextQuality);
      if (delta < distance) {
        selectedIndex = index;
        distance = delta;
      }
    });
    if (selectedIndex >= 0) {
      hls.autoLevelCapping = -1;
      hls.nextLevel = selectedIndex;
    }
  }, []);

  useEffect(() => {
    const hls = hlsRef.current;
    if (hls) applyHlsPolicy(hls, quality, dataSaver);
  }, [quality, dataSaver, applyHlsPolicy]);

  useEffect(() => {
    if (embed && !usingOfflineCopy) return;
    const video = videoRef.current;
    if (!video) return;

    const previousTime = video.currentTime || resumeTargetRef.current || initialTime;
    const shouldResumePlayback = !video.paused || resumeShouldPlayRef.current;
    resumeTargetRef.current = previousTime;
    resumeShouldPlayRef.current = shouldResumePlayback;
    resumeAppliedRef.current = false;
    progressEmitRef.current = 0;

    hlsRef.current?.destroy();
    hlsRef.current = null;
    video.pause();
    video.removeAttribute("src");
    video.load();
    setHlsActive(false);
    setHlsLevels([]);
    setActiveHeight(null);
    watchedAccumulatorRef.current = 0;
    lastPlaybackPositionRef.current = null;
    setError("");
    setLoading(true);
    setPlaying(false);
    setSettingsOpen(false);

    const hlsSource = effectiveHlsSource;
    if (hlsSource) {
      if (Hls.isSupported()) {
        const hls = new Hls({
          enableWorker: true,
          capLevelToPlayerSize: true,
          startLevel: dataSaver ? 0 : -1,
          abrEwmaDefaultEstimate: initialBandwidthEstimate(network, dataSaver),
          maxBufferLength: dataSaver ? 12 : 30,
          maxMaxBufferLength: dataSaver ? 24 : 60,
          backBufferLength: dataSaver ? 10 : 30,
          maxBufferSize: dataSaver ? 12 * 1024 * 1024 : 30 * 1024 * 1024,
        });
        hlsRef.current = hls;
        setHlsActive(true);
        hls.attachMedia(video);
        hls.on(Hls.Events.MEDIA_ATTACHED, () => hls.loadSource(hlsSource));
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          const heights = uniqueSortedHeights(hls.levels.map((level) => level.height || 0));
          setHlsLevels(heights);
          applyHlsPolicy(hls, quality, dataSaver);
        });
        hls.on(Hls.Events.LEVEL_SWITCHED, (_event, data) => {
          const level = hls.levels[data.level];
          setActiveHeight(level?.height || null);
        });
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (!data.fatal) return;
          if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
            // Hors-ligne : attendre l'événement `online` au lieu de boucler sur des requêtes
            // qui consomment batterie et radio. En ligne, hls.js reprend son ABR normalement.
            if (navigator.onLine !== false) hls.startLoad();
            else setLoading(false);
            return;
          }
          if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
            hls.recoverMediaError();
            return;
          }
          setLoading(false);
          setPlaying(false);
          setError("Le flux adaptatif n'a pas pu être chargé. Réessayez ou désactivez le mode audio.");
          hls.destroy();
          if (hlsRef.current === hls) hlsRef.current = null;
        });
      } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = hlsSource;
        video.load();
      } else if (!audioOnly) {
        video.src = playbackSrc;
        video.load();
      } else {
        setLoading(false);
        setError("Le mode audio adaptatif n'est pas pris en charge par ce navigateur.");
      }
    } else {
      video.src = playbackSrc;
      video.load();
    }

    return () => {
      hlsRef.current?.destroy();
      hlsRef.current = null;
    };
  }, [
    playbackSrc,
    effectiveHlsSource,
    embed,
    usingOfflineCopy,
    audioOnly,
    initialTime,
    applyHlsPolicy,
    // quality/dataSaver sont appliqués séparément pour éviter de recharger la source à chaque changement.
  ]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !resolvedSubtitles) return;
    for (const track of Array.from(video.textTracks || [])) track.mode = captionsEnabled ? "showing" : "hidden";
  }, [captionsEnabled, resolvedSubtitles]);

  const seek = useCallback((delta: number) => {
    const video = videoRef.current;
    if (!video) return;
    const max = Number.isFinite(video.duration) ? video.duration : video.currentTime + Math.max(delta, 0);
    video.currentTime = Math.max(0, Math.min(max, video.currentTime + delta));
  }, []);

  const emitProgress = useCallback((video: HTMLVideoElement, force = false) => {
    if (!onProgress) return;
    const seconds = video.currentTime || 0;
    const nextDuration = Number.isFinite(video.duration) ? video.duration : duration;
    const wholeWatchedSeconds = Math.max(0, Math.floor(watchedAccumulatorRef.current));
    if (!force && Math.abs(seconds - progressEmitRef.current) < 15 && wholeWatchedSeconds < 15) return;
    if (wholeWatchedSeconds > 0) watchedAccumulatorRef.current -= wholeWatchedSeconds;
    progressEmitRef.current = seconds;
    onProgress(seconds, nextDuration, wholeWatchedSeconds);
  }, [duration, onProgress]);

  const togglePlay = useCallback(async () => {
    const video = videoRef.current;
    if (!video) return;
    setError("");
    try {
      if (video.paused) await video.play();
      else video.pause();
    } catch {
      setError(mediaErrorMessage(video));
    }
  }, []);

  async function togglePip() {
    const video = videoRef.current as (HTMLVideoElement & { requestPictureInPicture?: () => Promise<unknown> }) | null;
    if (!video || !video.requestPictureInPicture || audioOnly) return;
    try {
      const doc = document as Document & { pictureInPictureElement?: Element | null; exitPictureInPicture?: () => Promise<unknown> };
      if (doc.pictureInPictureElement) await doc.exitPictureInPicture?.();
      else await video.requestPictureInPicture();
    } catch {
      // Fonctionnalité absente ou refusée par le navigateur.
    }
  }

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await wrapperRef.current?.requestFullscreen();
    } catch {
      // Fonctionnalité absente ou refusée par le navigateur.
    }
  }

  function retry() {
    const video = videoRef.current;
    if (!video) return;
    setError("");
    setLoading(true);
    if (hlsRef.current && effectiveHlsSource) {
      hlsRef.current.startLoad();
      return;
    }
    video.load();
    void video.play().catch(() => {});
  }

  async function repairVideo() {
    if (!onRepair || repairing) return;
    setRepairing(true);
    setRepairMessage("Conversion de la vidéo en MP4 H.264/AAC… Vous pouvez rester sur cette page.");
    try {
      await onRepair();
      setRepairMessage("Vidéo réparée. Rechargement du lecteur…");
      setError("");
      setLoading(true);
    } catch (err) {
      setRepairMessage(err instanceof Error ? err.message : "La réparation de la vidéo a échoué.");
    } finally {
      setRepairing(false);
    }
  }

  function toggleMute() {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    setMuted(video.muted);
  }

  function changeVolume(value: number) {
    const video = videoRef.current;
    if (!video) return;
    const safe = Math.max(0, Math.min(1, value));
    video.volume = safe;
    video.muted = safe === 0;
    setVolume(safe);
    setMuted(safe === 0);
  }

  function chooseQuality(value: QualityChoice) {
    if (typeof value === "number" && value > 360 && dataSaver) setDataSaverPreference("off");
    setQuality(value);
    const hls = hlsRef.current;
    if (hls) applyHlsPolicy(hls, value, typeof value === "number" && value > 360 ? false : dataSaver);
  }

  function setDataSaverPreference(mode: DataSaverMode) {
    setDataSaverMode(mode);
    try {
      window.localStorage.setItem("kalanpro:data-saver-mode", mode);
      window.localStorage.removeItem("learneas:data-saver");
    } catch {}
    const nextEnabled = mode === "on" || (mode === "auto" && isConstrainedNetwork(network));
    if (nextEnabled && typeof quality === "number" && quality > 360) setQuality("auto");
  }

  function toggleAudioOnly() {
    if (!resolvedAudioHlsSrc) return;
    const video = videoRef.current;
    resumeTargetRef.current = video?.currentTime || currentTime || initialTime;
    resumeShouldPlayRef.current = Boolean(video && !video.paused);
    setAudioOnly((value) => !value);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    if (["INPUT", "SELECT", "TEXTAREA", "BUTTON", "A"].includes(target.tagName)) return;
    const key = event.key.toLowerCase();
    if ([" ", "k", "j", "l", "m", "f", "c", "arrowleft", "arrowright", "arrowup", "arrowdown"].includes(key)) event.preventDefault();
    if (key === " " || key === "k") void togglePlay();
    else if (key === "j") seek(-10);
    else if (key === "l") seek(10);
    else if (key === "arrowleft") seek(-5);
    else if (key === "arrowright") seek(5);
    else if (key === "arrowup") changeVolume((videoRef.current?.volume || 0) + 0.1);
    else if (key === "arrowdown") changeVolume((videoRef.current?.volume || 0) - 0.1);
    else if (key === "m") toggleMute();
    else if (key === "f") void toggleFullscreen();
    else if (key === "c" && resolvedSubtitles) setCaptionsEnabled((value) => !value);
  }

  if (embed) {
    return (
      <div className="relative h-full w-full overflow-hidden bg-black">
        <iframe
          src={embed.url}
          title={title}
          className="h-full w-full border-0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowFullScreen
          referrerPolicy="strict-origin-when-cross-origin"
        />
      </div>
    );
  }

  const progressPercent = duration > 0 ? Math.min(100, Math.max(0, (currentTime / duration) * 100)) : 0;
  const streamingReady = Boolean(resolvedHlsSrc && streamingStatus === "ready");

  return (
    <div
      ref={wrapperRef}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onContextMenu={(event) => event.preventDefault()}
      onDragStart={(event) => event.preventDefault()}
      onDoubleClick={() => void toggleFullscreen()}
      aria-label={`Lecteur vidéo · ${title}`}
      className="group relative h-full w-full overflow-hidden bg-black outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
    >
      <video
        ref={videoRef}
        playsInline
        preload="metadata"
        controlsList="nodownload noremoteplayback"
        disableRemotePlayback
        poster={!audioOnly ? (poster || undefined) : undefined}
        muted={muted}
        draggable={false}
        className={`h-full w-full select-none object-contain ${audioOnly ? "opacity-0" : "opacity-100"}`}
        onClick={() => void togglePlay()}
        onLoadedMetadata={(event) => {
          const video = event.currentTarget;
          const nextDuration = Number.isFinite(video.duration) ? video.duration : 0;
          setDuration(nextDuration);
          const targetTime = resumeTargetRef.current || initialTime;
          if (!resumeAppliedRef.current && targetTime > 2 && (!nextDuration || targetTime < nextDuration - 1)) {
            video.currentTime = targetTime;
            setCurrentTime(targetTime);
          }
          resumeAppliedRef.current = true;
          setLoading(false);
          setError("");
          video.playbackRate = rate;
          if (resumeShouldPlayRef.current || autoPlayOnLoad) void video.play().catch(() => {});
          resumeShouldPlayRef.current = false;
        }}
        onDurationChange={(event) => setDuration(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0)}
        onTimeUpdate={(event) => {
          const video = event.currentTarget;
          const seconds = video.currentTime;
          const nextDuration = Number.isFinite(video.duration) ? video.duration : duration;
          const previous = lastPlaybackPositionRef.current;
          if (!video.paused && previous != null) {
            const delta = seconds - previous;
            // Les sauts importants sont des seeks/buffer jumps, pas du temps réellement regardé.
            if (delta > 0 && delta <= 3.5) watchedAccumulatorRef.current += delta;
          }
          lastPlaybackPositionRef.current = seconds;
          setCurrentTime(seconds);
          onTimeChange?.(seconds, nextDuration);
          emitProgress(video);
        }}
        onSeeking={() => { lastPlaybackPositionRef.current = null; }}
        onSeeked={(event) => { lastPlaybackPositionRef.current = event.currentTarget.currentTime; }}
        onCanPlay={() => setLoading(false)}
        onWaiting={() => setLoading(true)}
        onPlaying={(event) => { setPlaying(true); setLoading(false); lastPlaybackPositionRef.current = event.currentTarget.currentTime; }}
        onPause={(event) => {
          setPlaying(false);
          emitProgress(event.currentTarget, true);
        }}
        onVolumeChange={(event) => { setMuted(event.currentTarget.muted); setVolume(event.currentTarget.volume); }}
        onRateChange={(event) => setRate(event.currentTarget.playbackRate)}
        onEnded={(event) => {
          setPlaying(false);
          const video = event.currentTarget;
          const seconds = video.currentTime || 0;
          const nextDuration = Number.isFinite(video.duration) ? video.duration : duration;
          const watchedDeltaSeconds = Math.max(0, Math.floor(watchedAccumulatorRef.current));
          if (watchedDeltaSeconds > 0) watchedAccumulatorRef.current -= watchedDeltaSeconds;
          progressEmitRef.current = seconds;
          if (onEnded) onEnded(seconds, nextDuration, watchedDeltaSeconds);
          else if (onProgress) onProgress(seconds, nextDuration, watchedDeltaSeconds);
        }}
        onError={() => {
          if (hlsRef.current) return;
          setLoading(false);
          setPlaying(false);
          setError(mediaErrorMessage(videoRef.current));
        }}
      >
        {resolvedSubtitles && <track kind="subtitles" src={resolvedSubtitles} srcLang="fr" label="Français" default />}
        Votre navigateur ne prend pas en charge la lecture vidéo intégrée.
      </video>

      {audioOnly && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center overflow-hidden bg-[#07101d] text-white">
          {poster && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={poster} alt="" loading="lazy" decoding="async" className="absolute inset-0 h-full w-full scale-105 object-cover opacity-20 blur-xl" />
          )}
          <div className="relative z-10 mx-5 max-w-lg rounded-2xl border border-white/10 bg-black/35 px-7 py-6 text-center shadow-2xl backdrop-blur">
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-emerald-500/20 text-emerald-300"><Headphones size={28} /></div>
            <p className="mt-4 text-base font-semibold">Mode audio uniquement</p>
            <p className="mt-1 text-xs leading-5 text-white/60">La vidéo n'est pas téléchargée. Idéal pour économiser les données mobiles.</p>
          </div>
        </div>
      )}

      <div className="pointer-events-none absolute left-3 top-3 z-10 flex flex-wrap gap-2">
        {!network.online && <span className="rounded-full bg-rose-600/95 px-2.5 py-1 text-[10px] font-bold text-white shadow">HORS LIGNE</span>}
        {audioOnly && <span className="rounded-full bg-emerald-500/90 px-2.5 py-1 text-[10px] font-bold text-white shadow">AUDIO · {usagePerHourLabel(48_000)}</span>}
        {!audioOnly && dataSaver && streamingReady && <span className="rounded-full bg-sky-600/90 px-2.5 py-1 text-[10px] font-bold text-white shadow">ÉCONOMIE ≤360p</span>}
        {!audioOnly && hlsActive && <span className="rounded-full bg-black/60 px-2.5 py-1 text-[10px] font-semibold text-white/80 shadow">{activeHeight ? `${activeHeight}p · ` : ""}HLS adaptatif</span>}
        {!audioOnly && estimatedBandwidth && <span className="rounded-full bg-black/60 px-2.5 py-1 text-[10px] font-semibold text-white/70 shadow">{usagePerHourLabel(estimatedBandwidth)}</span>}
      </div>

      {!playing && !error && !loading && (
        <button
          type="button"
          onClick={(event) => { event.stopPropagation(); void togglePlay(); }}
          className="absolute left-1/2 top-1/2 z-10 grid h-16 w-16 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-white/95 text-gray-950 shadow-2xl transition hover:scale-105"
          aria-label="Lire la vidéo"
        >
          <Play size={28} className="ml-1" fill="currentColor" />
        </button>
      )}

      {loading && !error && (
        <div className="pointer-events-none absolute inset-0 z-10 grid place-items-center bg-black/10">
          <div className="flex items-center gap-2 rounded-full bg-black/70 px-4 py-2 text-xs font-medium text-white/80">
            <Loader2 size={15} className="animate-spin" /> Chargement…
          </div>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/90 p-6 text-center text-white">
          <div className="max-w-xl">
            <p className="text-base font-semibold">La vidéo ne peut pas être lue</p>
            <p className="mt-2 text-sm leading-6 text-white/70">{error}</p>
            <p className="mt-2 text-xs text-white/40">KalanPro utilise HLS adaptatif quand il est disponible et garde le MP4 comme solution de secours.</p>
            {repairMessage && <p className="mt-3 rounded-lg bg-white/10 px-3 py-2 text-xs leading-5 text-white/75">{repairMessage}</p>}
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              <button type="button" onClick={retry} disabled={repairing} className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-gray-950 disabled:opacity-50">Réessayer</button>
              {audioOnly && (
                <button type="button" onClick={toggleAudioOnly} className="rounded-lg border border-white/20 px-4 py-2 text-sm font-semibold text-white hover:bg-white/10">Revenir à la vidéo</button>
              )}
              {onRepair && (
                <button
                  type="button"
                  onClick={() => void repairVideo()}
                  disabled={repairing}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:cursor-wait disabled:opacity-70"
                >
                  {repairing ? <Loader2 size={16} className="animate-spin" /> : <Wrench size={16} />}
                  {repairing ? "Réparation en cours…" : "Réparer cette vidéo"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {!error && (
        <div className="absolute inset-x-0 bottom-0 z-20 bg-gradient-to-t from-black via-black/75 to-transparent px-3 pb-3 pt-16 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100">
          <div className="relative mb-2 flex items-center">
            <input
              aria-label="Position dans la vidéo"
              type="range"
              min={0}
              max={Math.max(duration, 0)}
              step={0.1}
              value={Math.min(currentTime, duration || currentTime)}
              disabled={!duration}
              onChange={(event) => {
                const video = videoRef.current;
                if (!video) return;
                const value = Number(event.target.value);
                video.currentTime = value;
                setCurrentTime(value);
              }}
              className="h-1.5 w-full cursor-pointer accent-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
              style={{ background: `linear-gradient(to right, rgb(16 185 129) ${progressPercent}%, rgba(255,255,255,.35) ${progressPercent}%)` }}
            />
          </div>

          <div className="flex items-center gap-1 text-white">
            <button type="button" onClick={() => void togglePlay()} className="rounded-md p-2 hover:bg-white/10" title={playing ? "Pause (Espace/K)" : "Lecture (Espace/K)"}>
              {playing ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" />}
            </button>
            <button type="button" onClick={() => seek(-10)} className="hidden rounded-md p-2 hover:bg-white/10 sm:block" title="Reculer de 10 secondes (J)"><SkipBack size={18} /></button>
            <button type="button" onClick={() => seek(10)} className="hidden rounded-md p-2 hover:bg-white/10 sm:block" title="Avancer de 10 secondes (L)"><SkipForward size={18} /></button>
            <div className="group/volume flex items-center">
              <button type="button" onClick={toggleMute} className="rounded-md p-2 hover:bg-white/10" title="Son (M)">
                {muted || volume === 0 ? <VolumeX size={19} /> : volume < 0.5 ? <Volume1 size={19} /> : <Volume2 size={19} />}
              </button>
              <input
                aria-label="Volume"
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={muted ? 0 : volume}
                onChange={(event) => changeVolume(Number(event.target.value))}
                className="hidden h-1 w-20 cursor-pointer accent-white lg:block"
              />
            </div>
            <span className="ml-1 text-[11px] tabular-nums text-white/80 sm:text-xs">
              {formatClock(currentTime)} <span className="text-white/40">/</span> {formatClock(duration)}
            </span>

            <span className="flex-1" />

            {resolvedAudioHlsSrc && (
              <button
                type="button"
                onClick={toggleAudioOnly}
                className={`hidden rounded-md p-2 hover:bg-white/10 sm:block ${audioOnly ? "text-emerald-400" : "text-white"}`}
                title={audioOnly ? "Revenir à la vidéo" : "Audio uniquement · très faible consommation"}
                aria-pressed={audioOnly}
              >
                <Headphones size={20} />
              </button>
            )}

            {resolvedSubtitles && !audioOnly && (
              <button
                type="button"
                onClick={() => setCaptionsEnabled((value) => !value)}
                className={`rounded-md p-2 hover:bg-white/10 ${captionsEnabled ? "text-emerald-400" : "text-white"}`}
                title="Sous-titres (C)"
                aria-pressed={captionsEnabled}
              >
                <Captions size={20} />
              </button>
            )}

            <div className="relative">
              <button
                type="button"
                onClick={() => setSettingsOpen((value) => !value)}
                className={`rounded-md p-2 hover:bg-white/10 ${settingsOpen ? "bg-white/10" : ""}`}
                title="Préférences"
                aria-expanded={settingsOpen}
              >
                <Settings size={19} />
              </button>
              {settingsOpen && (
                <div className="absolute bottom-12 right-0 w-[19rem] max-w-[calc(100vw-1.5rem)] overflow-hidden rounded-xl border border-white/10 bg-gray-950/95 p-2 text-sm shadow-2xl backdrop-blur">
                  {resolvedHlsSrc && !audioOnly && (
                    <>
                      <p className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/40">Qualité vidéo</p>
                      <div className="grid grid-cols-3 gap-1">
                        <button
                          type="button"
                          onClick={() => chooseQuality("auto")}
                          className={`rounded-md px-2 py-2 text-xs font-semibold ${quality === "auto" ? "bg-emerald-600 text-white" : "text-white/75 hover:bg-white/10"}`}
                        >
                          Auto
                        </button>
                        {qualityHeights.map((height) => (
                          <button
                            key={height}
                            type="button"
                            onClick={() => chooseQuality(height)}
                            className={`rounded-md px-2 py-2 text-xs font-semibold ${quality === height ? "bg-emerald-600 text-white" : "text-white/75 hover:bg-white/10"}`}
                          >
                            {height}p
                          </button>
                        ))}
                      </div>

                      <div className="mt-2 rounded-lg border border-white/10 bg-white/[0.03] p-2.5">
                        <div className="flex items-center justify-between gap-3">
                          <span className="flex min-w-0 items-center gap-2">
                            {dataSaver ? <WifiOff size={17} className="shrink-0 text-sky-300" /> : <Wifi size={17} className="shrink-0 text-white/60" />}
                            <span className="min-w-0">
                              <span className="block text-xs font-semibold text-white">Connexion & données</span>
                              <span className="block truncate text-[10px] text-white/40">
                                {`${networkDisplayLabel(network)}${network.downlink ? ` · ${network.downlink.toFixed(1)} Mb/s` : ""}${network.saveData ? " · Save-Data" : ""}${usingOfflineCopy ? " · copie locale" : ""}`}
                              </span>
                            </span>
                          </span>
                          {estimatedBandwidth && <span className="shrink-0 text-[10px] font-semibold text-sky-200">{usagePerHourLabel(estimatedBandwidth)}</span>}
                        </div>
                        <div className="mt-2 grid grid-cols-3 gap-1">
                          {([
                            ["auto", "Auto"],
                            ["on", "Éco"],
                            ["off", "Normal"],
                          ] as const).map(([mode, label]) => (
                            <button
                              key={mode}
                              type="button"
                              onClick={() => setDataSaverPreference(mode)}
                              className={`rounded-md px-2 py-2 text-[11px] font-semibold ${dataSaverMode === mode ? "bg-sky-600 text-white" : "bg-white/5 text-white/65 hover:bg-white/10"}`}
                            >
                              {label}
                            </button>
                          ))}
                        </div>
                        <p className="mt-2 text-[10px] leading-4 text-white/35">
                          Auto active ≤360p sur 2G/Save-Data/faible débit. Éco force le master faible débit, y compris sur Safari.
                        </p>
                      </div>
                    </>
                  )}

                  {resolvedAudioHlsSrc && (
                    <button
                      type="button"
                      onClick={toggleAudioOnly}
                      className={`mt-2 flex w-full items-center justify-between rounded-lg border px-3 py-2.5 text-left ${audioOnly ? "border-emerald-500/40 bg-emerald-500/10" : "border-white/10 hover:bg-white/5"}`}
                    >
                      <span className="flex items-center gap-2">
                        <Headphones size={17} className={audioOnly ? "text-emerald-300" : "text-white/60"} />
                        <span>
                          <span className="block text-xs font-semibold text-white">Audio uniquement</span>
                          <span className="block text-[10px] text-white/40">~48 kb/s · consommation minimale</span>
                        </span>
                      </span>
                      <span className={`rounded-full px-2 py-1 text-[10px] font-bold ${audioOnly ? "bg-emerald-500 text-white" : "bg-white/10 text-white/50"}`}>{audioOnly ? "ON" : "OFF"}</span>
                    </button>
                  )}

                  <p className="mt-2 border-t border-white/10 px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/40">Vitesse de lecture</p>
                  <div className="grid grid-cols-4 gap-1">
                    {[0.5, 0.75, 1, 1.25, 1.5, 1.75, 2].map((value) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => {
                          setRate(value);
                          if (videoRef.current) videoRef.current.playbackRate = value;
                        }}
                        className={`rounded-md px-2 py-2 text-xs font-semibold ${rate === value ? "bg-emerald-600 text-white" : "text-white/75 hover:bg-white/10"}`}
                      >
                        {value}×
                      </button>
                    ))}
                  </div>
                  <div className="mt-2 border-t border-white/10 px-2 py-2 text-[11px] leading-5 text-white/40">
                    Espace/K lecture · J/L ±10 s · M son · F plein écran · C sous-titres
                  </div>
                </div>
              )}
            </div>

            <button type="button" onClick={togglePip} disabled={audioOnly} className="hidden rounded-md p-2 hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-30 sm:block" title="Picture-in-Picture"><PictureInPicture2 size={19} /></button>
            <button type="button" onClick={() => void toggleFullscreen()} className="rounded-md p-2 hover:bg-white/10" title="Plein écran (F)">{fullscreen ? <Minimize size={19} /> : <Maximize size={19} />}</button>
          </div>
        </div>
      )}

      {!playing && currentTime > 1 && !error && (
        <button
          type="button"
          onClick={() => { const video = videoRef.current; if (video) { video.currentTime = 0; setCurrentTime(0); } }}
          className="absolute right-4 top-4 z-10 hidden items-center gap-2 rounded-lg bg-black/60 px-3 py-2 text-xs font-medium text-white/80 backdrop-blur hover:bg-black/80 md:flex"
        >
          <RotateCcw size={14} /> Recommencer
        </button>
      )}

      {streamingStatus === "processing" && !resolvedHlsSrc && (
        <div className="pointer-events-none absolute right-3 top-3 z-10 rounded-full bg-black/60 px-2.5 py-1 text-[10px] font-medium text-white/60">Optimisation faible débit en cours…</div>
      )}

      <div className="sr-only" aria-live="polite">{playing ? "Lecture" : "Pause"}</div>
    </div>
  );
});

export default VideoPlayer;
