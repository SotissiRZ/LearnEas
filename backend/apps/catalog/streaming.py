from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage

from apps.common.media_metadata import _uploaded_file_path, probe_video_path

# Profils volontairement modestes pour l'Afrique francophone : l'objectif est de garder
# une image lisible sur mobile tout en permettant un vrai mode faible débit.
HLS_PROFILES = (
    {"height": 240, "video_bitrate": "280k", "maxrate": "340k", "bufsize": "560k", "audio_bitrate": "48k"},
    {"height": 360, "video_bitrate": "520k", "maxrate": "650k", "bufsize": "1040k", "audio_bitrate": "64k"},
    {"height": 480, "video_bitrate": "900k", "maxrate": "1100k", "bufsize": "1800k", "audio_bitrate": "80k"},
    {"height": 720, "video_bitrate": "1800k", "maxrate": "2200k", "bufsize": "3600k", "audio_bitrate": "96k"},
)


def _even(value: int) -> int:
    return max(2, int(value) // 2 * 2)


def _storage_delete_tree(prefix: str) -> None:
    """Supprime récursivement un ancien paquet HLS sur FileSystemStorage ou S3."""
    clean = str(PurePosixPath(prefix)).strip("/")
    try:
        dirs, files = default_storage.listdir(clean)
    except Exception:
        return
    for filename in files:
        try:
            default_storage.delete(f"{clean}/{filename}")
        except Exception:
            pass
    for dirname in dirs:
        _storage_delete_tree(f"{clean}/{dirname}")


def _save_directory(local_root: Path, storage_prefix: str) -> None:
    for path in sorted(local_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(local_root).as_posix()
        storage_name = f"{storage_prefix.rstrip('/')}/{relative}"
        with path.open("rb") as handle:
            default_storage.save(storage_name, File(handle, name=path.name))


def _run(command: list[str], *, timeout: int) -> None:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "ffmpeg a échoué").strip()
        raise ValueError(message[-4000:])


def _variant_profiles(source_height: int) -> list[dict[str, Any]]:
    max_height = int(getattr(settings, "HLS_MAX_HEIGHT", 720))
    candidates = [dict(profile) for profile in HLS_PROFILES if profile["height"] <= max_height and profile["height"] <= source_height]
    if candidates:
        return candidates
    # Très petite vidéo : conserver une seule version à sa hauteur, sans upscale.
    fallback_height = _even(max(2, min(source_height or 240, max_height)))
    return [{
        "height": fallback_height,
        "video_bitrate": "220k",
        "maxrate": "280k",
        "bufsize": "440k",
        "audio_bitrate": "48k",
    }]


def generate_lesson_hls(file_obj, *, lesson_id: int, offline_enabled: bool = False) -> dict[str, Any]:
    """Produit un master HLS multi-bitrate + une playlist audio seule puis les stocke.

    Le paquet est versionné afin qu'une régénération ne casse jamais une lecture déjà en cours.
    """
    source_path, source_is_temp = _uploaded_file_path(file_obj)
    timeout = int(getattr(settings, "HLS_TRANSCODE_TIMEOUT_SECONDS", 7200))
    preset = str(getattr(settings, "HLS_TRANSCODE_PRESET", "veryfast"))
    segment_seconds = max(2, int(getattr(settings, "HLS_SEGMENT_SECONDS", 6)))
    package_id = uuid.uuid4().hex[:16]
    storage_prefix = f"courses/hls/{lesson_id}/{package_id}"

    workdir = Path(tempfile.mkdtemp(prefix=f"learneas-hls-{lesson_id}-"))
    try:
        info = probe_video_path(source_path)
        source_width = int(info.get("width") or 1280)
        source_height = int(info.get("height") or 720)
        has_audio = bool(info.get("has_audio"))
        duration_seconds = max(0, int(round(float(info.get("duration_seconds") or 0))))
        profiles = _variant_profiles(source_height)
        master_lines = ["#EXTM3U", "#EXT-X-VERSION:6", "#EXT-X-INDEPENDENT-SEGMENTS"]
        variants: list[dict[str, int]] = []

        for profile in profiles:
            height = int(profile["height"])
            width = _even(round(source_width * (height / max(source_height, 1))))
            variant_dir = workdir / f"v{height}"
            variant_dir.mkdir(parents=True, exist_ok=True)
            playlist = variant_dir / "index.m3u8"
            segment_pattern = variant_dir / "seg_%05d.ts"

            command = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", source_path,
                "-map", "0:v:0", "-map", "0:a:0?",
                "-vf", f"scale=-2:{height}:force_original_aspect_ratio=decrease",
                "-c:v", "libx264", "-preset", preset, "-profile:v", "main", "-pix_fmt", "yuv420p",
                "-b:v", str(profile["video_bitrate"]), "-maxrate", str(profile["maxrate"]), "-bufsize", str(profile["bufsize"]),
                "-sc_threshold", "0",
                # Une image-clé est forcée à chaque frontière de segment. Cela évite les
                # segments anormalement longs sur des sources 24/25/30/60 fps et améliore
                # nettement le changement de qualité sur connexion instable.
                "-force_key_frames", f"expr:gte(t,n_forced*{segment_seconds})",
            ]
            if has_audio:
                command += ["-c:a", "aac", "-b:a", str(profile["audio_bitrate"]), "-ac", "2", "-ar", "44100"]
            command += [
                "-hls_time", str(segment_seconds), "-hls_playlist_type", "vod", "-hls_flags", "independent_segments",
                "-hls_segment_filename", str(segment_pattern), str(playlist),
            ]
            _run(command, timeout=timeout)

            # BANDWIDTH en bits/s. On garde une estimation légèrement supérieure au débit cible.
            numeric_kbps = int(str(profile["maxrate"]).rstrip("k")) + int(str(profile["audio_bitrate"]).rstrip("k"))
            bandwidth = numeric_kbps * 1000
            master_lines += [
                f"#EXT-X-STREAM-INF:BANDWIDTH={bandwidth},AVERAGE-BANDWIDTH={int(bandwidth * 0.82)},RESOLUTION={width}x{height},NAME=\"{height}p\"",
                f"v{height}/index.m3u8",
            ]
            variants.append({
                "height": height,
                "width": width,
                "bandwidth": bandwidth,
                "approx_mb_per_hour": round((bandwidth * 3600) / 8 / 1_000_000),
            })


        offline_path = ""
        offline_size = 0
        if offline_enabled and bool(getattr(settings, "OFFLINE_VIDEO_ENABLED", True)):
            offline_max_height = max(144, int(getattr(settings, "OFFLINE_VIDEO_MAX_HEIGHT", 360)))
            offline_height = _even(min(source_height or offline_max_height, offline_max_height))
            # Réutiliser le profil le plus proche pour maîtriser la taille sur téléphone.
            profile = min(HLS_PROFILES, key=lambda item: abs(int(item["height"]) - offline_height))
            offline_file = workdir / "offline.mp4"
            command = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", source_path, "-map", "0:v:0", "-map", "0:a:0?",
                "-vf", f"scale=-2:{offline_height}:force_original_aspect_ratio=decrease",
                "-c:v", "libx264", "-preset", preset, "-profile:v", "main", "-pix_fmt", "yuv420p",
                "-b:v", str(profile["video_bitrate"]), "-maxrate", str(profile["maxrate"]), "-bufsize", str(profile["bufsize"]),
                "-movflags", "+faststart",
            ]
            if has_audio:
                command += ["-c:a", "aac", "-b:a", "64k", "-ac", "2", "-ar", "44100"]
            else:
                command += ["-an"]
            command += [str(offline_file)]
            _run(command, timeout=timeout)
            offline_size = offline_file.stat().st_size
            max_offline_bytes = max(25, int(getattr(settings, "OFFLINE_VIDEO_MAX_MB", 250))) * 1024 * 1024
            if offline_size > max_offline_bytes:
                offline_file.unlink(missing_ok=True)
                offline_size = 0
            else:
                offline_path = f"{storage_prefix}/offline.mp4"

        audio_path = ""
        if has_audio:
            audio_dir = workdir / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_playlist = audio_dir / "index.m3u8"
            _run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", source_path, "-map", "0:a:0", "-vn",
                "-c:a", "aac", "-b:a", str(getattr(settings, "HLS_AUDIO_ONLY_BITRATE", "48k")),
                "-ac", "1", "-ar", "44100",
                "-hls_time", str(max(segment_seconds, 8)), "-hls_playlist_type", "vod",
                "-hls_segment_filename", str(audio_dir / "seg_%05d.aac"), str(audio_playlist),
            ], timeout=timeout)
            audio_path = f"{storage_prefix}/audio/index.m3u8"

        (workdir / "master.m3u8").write_text("\n".join(master_lines) + "\n", encoding="utf-8")
        try:
            _save_directory(workdir, storage_prefix)
        except Exception:
            _storage_delete_tree(storage_prefix)
            raise

        return {
            "master_path": f"{storage_prefix}/master.m3u8",
            "audio_path": audio_path,
            "variants": variants,
            "duration_seconds": duration_seconds,
            "offline_path": offline_path,
            "offline_size_bytes": offline_size,
            "storage_prefix": storage_prefix,
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
        if source_is_temp:
            try:
                os.unlink(source_path)
            except OSError:
                pass


def delete_hls_package_from_manifest(manifest_path: str) -> None:
    if not manifest_path:
        return
    parts = PurePosixPath(manifest_path).parts
    # courses/hls/<lesson>/<package>/master.m3u8
    if len(parts) >= 5 and parts[0:2] == ("courses", "hls"):
        _storage_delete_tree("/".join(parts[:-1]))
