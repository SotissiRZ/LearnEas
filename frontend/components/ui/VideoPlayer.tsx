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
import {
  Captions,
  Check,
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
  Wrench,
  Loader2,
} from "lucide-react";
import { resolveMediaUrl } from "@/lib/media";

type Props = {
  src: string;
  poster?: string | null;
  title?: string;
  subtitlesUrl?: string | null;
  initialTime?: number;
  autoPlayOnLoad?: boolean;
  onEnded?: () => void;
  onProgress?: (seconds: number, duration: number) => void;
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

const VideoPlayer = forwardRef<VideoPlayerHandle, Props>(function VideoPlayer(
  {
    src,
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
  const progressEmitRef = useRef(0);
  const resumeAppliedRef = useRef(false);
  const resolvedSrc = useMemo(() => resolveMediaUrl(src), [src]);
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
    const handler = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  useEffect(() => {
    if (embed) return;
    const video = videoRef.current;
    if (!video) return;
    setError("");
    setLoading(true);
    setPlaying(false);
    setDuration(0);
    setCurrentTime(0);
    setSettingsOpen(false);
    resumeAppliedRef.current = false;
    progressEmitRef.current = 0;
    video.load();
  }, [resolvedSrc, embed]);

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
    if (!video || !video.requestPictureInPicture) return;
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
        src={resolvedSrc}
        playsInline
        preload="metadata"
        controlsList="nodownload noremoteplayback"
        disableRemotePlayback
        poster={poster || undefined}
        muted={muted}
        draggable={false}
        className="h-full w-full select-none object-contain"
        onClick={() => void togglePlay()}
        onLoadedMetadata={(event) => {
          const video = event.currentTarget;
          const nextDuration = Number.isFinite(video.duration) ? video.duration : 0;
          setDuration(nextDuration);
          if (!resumeAppliedRef.current && initialTime > 2 && (!nextDuration || initialTime < nextDuration - 3)) {
            video.currentTime = initialTime;
            setCurrentTime(initialTime);
          }
          resumeAppliedRef.current = true;
          setLoading(false);
          setError("");
          if (autoPlayOnLoad) void video.play().catch(() => {});
        }}
        onDurationChange={(event) => setDuration(Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : 0)}
        onTimeUpdate={(event) => {
          const video = event.currentTarget;
          const seconds = video.currentTime;
          const nextDuration = Number.isFinite(video.duration) ? video.duration : duration;
          setCurrentTime(seconds);
          onTimeChange?.(seconds, nextDuration);
          if (onProgress && Math.abs(seconds - progressEmitRef.current) >= 15) {
            progressEmitRef.current = seconds;
            onProgress(seconds, nextDuration);
          }
        }}
        onCanPlay={() => setLoading(false)}
        onWaiting={() => setLoading(true)}
        onPlaying={() => { setPlaying(true); setLoading(false); }}
        onPause={(event) => {
          setPlaying(false);
          const seconds = event.currentTarget.currentTime;
          onProgress?.(seconds, Number.isFinite(event.currentTarget.duration) ? event.currentTarget.duration : duration);
        }}
        onVolumeChange={(event) => { setMuted(event.currentTarget.muted); setVolume(event.currentTarget.volume); }}
        onRateChange={(event) => setRate(event.currentTarget.playbackRate)}
        onEnded={() => { setPlaying(false); onEnded?.(); }}
        onError={() => { setLoading(false); setPlaying(false); setError(mediaErrorMessage(videoRef.current)); }}
      >
        {resolvedSubtitles && <track kind="subtitles" src={resolvedSubtitles} srcLang="fr" label="Français" default />}
        Votre navigateur ne prend pas en charge la lecture vidéo intégrée.
      </video>

      {!playing && !error && !loading && (
        <button
          type="button"
          onClick={(event) => { event.stopPropagation(); void togglePlay(); }}
          className="absolute left-1/2 top-1/2 grid h-16 w-16 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-white/95 text-gray-950 shadow-2xl transition hover:scale-105"
          aria-label="Lire la vidéo"
        >
          <Play size={28} className="ml-1" fill="currentColor" />
        </button>
      )}

      {loading && !error && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center bg-black/10">
          <div className="flex items-center gap-2 rounded-full bg-black/70 px-4 py-2 text-xs font-medium text-white/85">
            <Loader2 size={15} className="animate-spin" /> Chargement…
          </div>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-black/90 p-6 text-center text-white">
          <div className="max-w-xl">
            <p className="text-base font-semibold">La vidéo ne peut pas être lue</p>
            <p className="mt-2 text-sm leading-6 text-white/70">{error}</p>
            <p className="mt-2 text-xs text-white/45">Les fichiers MP4 H.264/AAC et WebM sont les plus compatibles.</p>
            {repairMessage && <p className="mt-3 rounded-lg bg-white/10 px-3 py-2 text-xs leading-5 text-white/75">{repairMessage}</p>}
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              <button type="button" onClick={retry} disabled={repairing} className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-gray-950 disabled:opacity-50">Réessayer</button>
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
        <div className="absolute inset-x-0 bottom-0 z-10 bg-gradient-to-t from-black via-black/75 to-transparent px-3 pb-3 pt-16 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100">
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

            {resolvedSubtitles && (
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
                <div className="absolute bottom-12 right-0 w-64 overflow-hidden rounded-xl border border-white/10 bg-gray-950/95 p-2 text-sm shadow-2xl backdrop-blur">
                  <p className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/45">Vitesse de lecture</p>
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
                  <div className="mt-2 border-t border-white/10 px-2 py-2 text-[11px] leading-5 text-white/45">
                    Espace/K lecture · J/L ±10 s · M son · F plein écran · C sous-titres
                  </div>
                </div>
              )}
            </div>

            <button type="button" onClick={togglePip} className="hidden rounded-md p-2 hover:bg-white/10 sm:block" title="Picture-in-Picture"><PictureInPicture2 size={19} /></button>
            <button type="button" onClick={() => void toggleFullscreen()} className="rounded-md p-2 hover:bg-white/10" title="Plein écran (F)">{fullscreen ? <Minimize size={19} /> : <Maximize size={19} />}</button>
          </div>
        </div>
      )}

      {!playing && currentTime > 1 && !error && (
        <button
          type="button"
          onClick={() => { const video = videoRef.current; if (video) { video.currentTime = 0; setCurrentTime(0); } }}
          className="absolute right-4 top-4 hidden items-center gap-2 rounded-lg bg-black/60 px-3 py-2 text-xs font-medium text-white/80 backdrop-blur hover:bg-black/80 md:flex"
        >
          <RotateCcw size={14} /> Recommencer
        </button>
      )}

      <div className="sr-only" aria-live="polite">{playing ? "Lecture" : "Pause"}</div>
    </div>
  );
});

export default VideoPlayer;
