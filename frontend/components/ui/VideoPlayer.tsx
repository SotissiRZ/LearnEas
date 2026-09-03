"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Download,
  ExternalLink,
  Maximize2,
  Minimize2,
  Pause,
  PictureInPicture2,
  Play,
  RotateCcw,
  Wrench,
  Loader2,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
} from "lucide-react";
import { resolveMediaUrl } from "@/lib/media";

type Props = {
  src: string;
  poster?: string | null;
  title?: string;
  subtitlesUrl?: string | null;
  onEnded?: () => void;
  onRepair?: () => Promise<void>;
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
      if (match?.[1]) {
        return { kind: "vimeo", url: `https://player.vimeo.com/video/${match[1]}?title=0&byline=0&portrait=0` };
      }
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

export default function VideoPlayer({ src, poster, title = "Vidéo", subtitlesUrl, onEnded, onRepair }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const resolvedSrc = useMemo(() => resolveMediaUrl(src), [src]);
  const resolvedSubtitles = useMemo(() => subtitlesUrl ? resolveMediaUrl(subtitlesUrl) : null, [subtitlesUrl]);
  const embed = useMemo(() => getEmbedSource(resolvedSrc), [resolvedSrc]);

  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(1);
  const [rate, setRate] = useState(1);
  const [loop, setLoop] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [repairing, setRepairing] = useState(false);
  const [repairMessage, setRepairMessage] = useState("");

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
    video.load();
  }, [resolvedSrc, embed]);

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
      // noop
    }
  }

  function retry() {
    const video = videoRef.current;
    if (!video) return;
    setError("");
    setLoading(true);
    video.load();
    void video.play().catch(() => {
      // L'autoplay peut être bloqué ; le bouton Lecture reste disponible.
    });
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

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    if (["INPUT", "SELECT", "TEXTAREA", "BUTTON", "A"].includes(target.tagName)) return;
    const key = event.key.toLowerCase();
    if ([" ", "k", "j", "l", "m", "f", "arrowleft", "arrowright"].includes(key)) event.preventDefault();
    if (key === " " || key === "k") void togglePlay();
    else if (key === "j") seek(-10);
    else if (key === "l") seek(10);
    else if (key === "arrowleft") seek(-5);
    else if (key === "arrowright") seek(5);
    else if (key === "m") {
      const video = videoRef.current;
      if (!video) return;
      video.muted = !video.muted;
      setMuted(video.muted);
    } else if (key === "f") void toggleFullscreen();
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

  return (
    <div
      ref={wrapperRef}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      aria-label={`Lecteur vidéo · ${title}`}
      className="group relative flex h-full w-full flex-col overflow-hidden bg-black outline-none focus:ring-2 focus:ring-brand-500"
    >
      <div className="relative min-h-0 flex-1 bg-black">
        <video
          ref={videoRef}
          src={resolvedSrc}
          playsInline
          preload="metadata"
          poster={poster || undefined}
          muted={muted}
          loop={loop}
          className="h-full w-full object-contain"
          onClick={() => void togglePlay()}
          onLoadedMetadata={(e) => {
            setDuration(Number.isFinite(e.currentTarget.duration) ? e.currentTarget.duration : 0);
            setLoading(false);
            setError("");
          }}
          onDurationChange={(e) => setDuration(Number.isFinite(e.currentTarget.duration) ? e.currentTarget.duration : 0)}
          onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          onCanPlay={() => setLoading(false)}
          onWaiting={() => setLoading(true)}
          onPlaying={() => { setPlaying(true); setLoading(false); }}
          onPause={() => setPlaying(false)}
          onVolumeChange={(e) => { setMuted(e.currentTarget.muted); setVolume(e.currentTarget.volume); }}
          onRateChange={(e) => setRate(e.currentTarget.playbackRate)}
          onEnded={() => { setPlaying(false); onEnded?.(); }}
          onError={() => { setLoading(false); setPlaying(false); setError(mediaErrorMessage(videoRef.current)); }}
        >
          {resolvedSubtitles && <track kind="subtitles" src={resolvedSubtitles} srcLang="fr" label="Français" default />}
          Votre navigateur ne prend pas en charge la lecture vidéo intégrée.
        </video>

        {!playing && !error && (
          <button
            type="button"
            onClick={() => void togglePlay()}
            className="absolute left-1/2 top-1/2 grid h-16 w-16 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-white/95 text-gray-950 shadow-2xl transition hover:scale-105"
            aria-label="Lire la vidéo"
          >
            <Play size={28} className="ml-1" fill="currentColor" />
          </button>
        )}

        {loading && !error && (
          <div className="pointer-events-none absolute left-1/2 top-[calc(50%+52px)] -translate-x-1/2 rounded-full bg-black/65 px-3 py-1 text-xs text-white/80">
            Chargement…
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/85 p-6 text-center text-white">
            <div className="max-w-xl">
              <p className="text-base font-semibold">La vidéo ne peut pas être lue</p>
              <p className="mt-2 text-sm leading-6 text-white/70">{error}</p>
              <p className="mt-2 text-xs text-white/45">Les fichiers MP4 H.264/AAC et WebM sont les plus compatibles. Les liens YouTube et Vimeo sont également pris en charge.</p>
              {repairMessage && <p className="mt-3 rounded-lg bg-white/10 px-3 py-2 text-xs leading-5 text-white/75">{repairMessage}</p>}
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                <button type="button" onClick={retry} disabled={repairing} className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-gray-950 disabled:opacity-50">Réessayer</button>
                {onRepair && (
                  <button
                    type="button"
                    onClick={() => void repairVideo()}
                    disabled={repairing}
                    className="inline-flex items-center gap-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-400 disabled:cursor-wait disabled:opacity-70"
                  >
                    {repairing ? <Loader2 size={16} className="animate-spin" /> : <Wrench size={16} />}
                    {repairing ? "Réparation en cours…" : "Réparer cette vidéo"}
                  </button>
                )}
                <a href={resolvedSrc} target="_blank" rel="noreferrer" className="rounded-lg border border-white/20 px-4 py-2 text-sm font-semibold text-white">Ouvrir la source</a>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-white/10 bg-gray-950 px-3 py-2.5 text-white">
        <div className="mb-2 flex items-center gap-2">
          <span className="w-11 text-right text-[11px] tabular-nums text-white/65">{formatClock(currentTime)}</span>
          <input
            aria-label="Position dans la vidéo"
            type="range"
            min={0}
            max={Math.max(duration, 0)}
            step={0.1}
            value={Math.min(currentTime, duration || currentTime)}
            disabled={!duration}
            onChange={(e) => {
              const video = videoRef.current;
              if (!video) return;
              const value = Number(e.target.value);
              video.currentTime = value;
              setCurrentTime(value);
            }}
            className="h-1 flex-1 cursor-pointer accent-white disabled:cursor-not-allowed disabled:opacity-40"
          />
          <span className="w-11 text-[11px] tabular-nums text-white/65">{formatClock(duration)}</span>
        </div>

        <div className="flex flex-wrap items-center gap-1">
          <button type="button" onClick={() => void togglePlay()} className="rounded-lg p-2 hover:bg-white/10" title={playing ? "Pause (Espace/K)" : "Lecture (Espace/K)"}>
            {playing ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
          </button>
          <button type="button" onClick={() => seek(-10)} className="rounded-lg p-2 hover:bg-white/10" title="Reculer de 10 secondes"><SkipBack size={17} /></button>
          <button type="button" onClick={() => seek(10)} className="rounded-lg p-2 hover:bg-white/10" title="Avancer de 10 secondes"><SkipForward size={17} /></button>
          <button type="button" onClick={() => { const video = videoRef.current; if (video) { video.currentTime = 0; setCurrentTime(0); } }} className="rounded-lg p-2 hover:bg-white/10" title="Recommencer"><RotateCcw size={17} /></button>
          <button
            type="button"
            onClick={() => {
              const video = videoRef.current;
              if (!video) return;
              video.muted = !video.muted;
              setMuted(video.muted);
            }}
            className="rounded-lg p-2 hover:bg-white/10"
            title={muted ? "Activer le son" : "Couper le son"}
          >
            {muted || volume === 0 ? <VolumeX size={17} /> : <Volume2 size={17} />}
          </button>
          <input
            aria-label="Volume"
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={muted ? 0 : volume}
            onChange={(e) => {
              const video = videoRef.current;
              if (!video) return;
              const value = Number(e.target.value);
              video.volume = value;
              video.muted = value === 0;
              setVolume(value);
              setMuted(value === 0);
            }}
            className="hidden h-1 w-20 cursor-pointer accent-white sm:block"
          />
          <label className="ml-1 flex items-center gap-1 text-xs text-white/70">
            <span className="hidden sm:inline">Vitesse</span>
            <select
              value={rate}
              onChange={(e) => {
                const value = Number(e.target.value);
                setRate(value);
                if (videoRef.current) videoRef.current.playbackRate = value;
              }}
              className="rounded-lg border border-white/15 bg-black px-2 py-1.5 text-xs text-white"
            >
              {[0.5, 0.75, 1, 1.25, 1.5, 1.75, 2].map((value) => <option key={value} value={value}>{value}×</option>)}
            </select>
          </label>
          <label className="ml-1 hidden items-center gap-1 text-xs text-white/65 md:flex"><input type="checkbox" checked={loop} onChange={(e) => setLoop(e.target.checked)} /> Boucle</label>
          <span className="flex-1" />
          <button type="button" onClick={togglePip} className="rounded-lg p-2 hover:bg-white/10" title="Picture-in-Picture"><PictureInPicture2 size={17} /></button>
          <a href={resolvedSrc} target="_blank" rel="noreferrer" className="rounded-lg p-2 hover:bg-white/10" title="Ouvrir dans un nouvel onglet"><ExternalLink size={17} /></a>
          <a href={resolvedSrc} download className="hidden rounded-lg p-2 hover:bg-white/10 sm:inline-flex" title={`Télécharger ${title}`}><Download size={17} /></a>
          <button type="button" onClick={() => void toggleFullscreen()} className="rounded-lg p-2 hover:bg-white/10" title="Plein écran (F)">{fullscreen ? <Minimize2 size={17} /> : <Maximize2 size={17} />}</button>
        </div>
      </div>
    </div>
  );
}
