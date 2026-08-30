"use client";

import { useEffect, useRef, useState } from "react";
import {
  Download, ExternalLink, Maximize2, Minimize2, PictureInPicture2,
  RotateCcw, SkipBack, SkipForward, Volume2, VolumeX,
} from "lucide-react";

type Props = {
  src: string;
  poster?: string | null;
  title?: string;
  subtitlesUrl?: string | null;
  onEnded?: () => void;
};

export default function VideoPlayer({ src, poster, title = "Vidéo", subtitlesUrl, onEnded }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const [muted, setMuted] = useState(false);
  const [rate, setRate] = useState(1);
  const [loop, setLoop] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    const handler = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  function seek(delta: number) {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = Math.max(0, Math.min(video.duration || Infinity, video.currentTime + delta));
  }

  async function togglePip() {
    const video = videoRef.current as (HTMLVideoElement & { requestPictureInPicture?: () => Promise<unknown> }) | null;
    if (!video || !video.requestPictureInPicture) return;
    try {
      if ((document as Document & { pictureInPictureElement?: Element | null }).pictureInPictureElement) {
        await (document as Document & { exitPictureInPicture?: () => Promise<unknown> }).exitPictureInPicture?.();
      } else {
        await video.requestPictureInPicture();
      }
    } catch { /* fonctionnalité navigateur non disponible */ }
  }

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await wrapperRef.current?.requestFullscreen();
    } catch { /* noop */ }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    if (["INPUT", "SELECT", "TEXTAREA", "BUTTON", "A"].includes(target.tagName)) return;
    const video = videoRef.current;
    if (!video) return;
    const key = event.key.toLowerCase();
    if ([" ", "k", "j", "l", "m", "f", "arrowleft", "arrowright"].includes(key)) event.preventDefault();
    if (key === " " || key === "k") video.paused ? void video.play() : video.pause();
    else if (key === "j") seek(-10);
    else if (key === "l") seek(10);
    else if (key === "arrowleft") seek(-5);
    else if (key === "arrowright") seek(5);
    else if (key === "m") { video.muted = !video.muted; setMuted(video.muted); }
    else if (key === "f") void toggleFullscreen();
  }

  return (
    <div ref={wrapperRef} tabIndex={0} onKeyDown={handleKeyDown} aria-label={`Lecteur vidéo · ${title}`} className="flex h-full w-full flex-col bg-black outline-none focus:ring-2 focus:ring-brand-500">
      <div className="min-h-0 flex-1">
        <video
          ref={videoRef}
          src={src}
          controls
          playsInline
          preload="metadata"
          poster={poster || undefined}
          muted={muted}
          loop={loop}
          className="h-full w-full"
          onEnded={onEnded}
          onRateChange={(e) => setRate(e.currentTarget.playbackRate)}
        >
          {subtitlesUrl && <track kind="subtitles" src={subtitlesUrl} srcLang="fr" label="Français" default />}
          Votre navigateur ne prend pas en charge la lecture vidéo intégrée.
        </video>
      </div>
      <div className="flex flex-wrap items-center gap-1 border-t border-white/10 bg-black/95 px-2 py-2 text-white">
        <button type="button" onClick={() => seek(-10)} className="rounded p-2 hover:bg-white/10" title="Reculer de 10 secondes"><SkipBack size={16} /></button>
        <button type="button" onClick={() => seek(10)} className="rounded p-2 hover:bg-white/10" title="Avancer de 10 secondes"><SkipForward size={16} /></button>
        <button type="button" onClick={() => { if (videoRef.current) videoRef.current.currentTime = 0; }} className="rounded p-2 hover:bg-white/10" title="Recommencer"><RotateCcw size={16} /></button>
        <button type="button" onClick={() => { const next = !muted; setMuted(next); if (videoRef.current) videoRef.current.muted = next; }} className="rounded p-2 hover:bg-white/10" title={muted ? "Activer le son" : "Couper le son"}>{muted ? <VolumeX size={16} /> : <Volume2 size={16} />}</button>
        <label className="ml-1 flex items-center gap-1 text-xs text-white/70">Vitesse
          <select
            value={rate}
            onChange={(e) => { const value = Number(e.target.value); setRate(value); if (videoRef.current) videoRef.current.playbackRate = value; }}
            className="rounded border border-white/15 bg-black px-1.5 py-1 text-xs text-white"
          >
            {[0.5, 0.75, 1, 1.25, 1.5, 1.75, 2].map((value) => <option key={value} value={value}>{value}×</option>)}
          </select>
        </label>
        <label className="ml-2 flex items-center gap-1 text-xs text-white/70"><input type="checkbox" checked={loop} onChange={(e) => setLoop(e.target.checked)} /> Boucle</label>
        <span className="flex-1" />
        <button type="button" onClick={togglePip} className="rounded p-2 hover:bg-white/10" title="Picture-in-Picture"><PictureInPicture2 size={16} /></button>
        <a href={src} target="_blank" rel="noreferrer" className="rounded p-2 hover:bg-white/10" title="Ouvrir dans un nouvel onglet"><ExternalLink size={16} /></a>
        <a href={src} download className="rounded p-2 hover:bg-white/10" title={`Télécharger ${title}`}><Download size={16} /></a>
        <button type="button" onClick={toggleFullscreen} className="rounded p-2 hover:bg-white/10" title="Plein écran (F)">{fullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}</button>
        <span className="hidden text-[10px] text-white/40 xl:inline" title="Raccourcis : Espace/K lecture, J/L ±10s, ←/→ ±5s, M muet, F plein écran">K · J/L · M · F</span>
      </div>
    </div>
  );
}
