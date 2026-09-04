from __future__ import annotations

import csv
import io
import mimetypes
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from rest_framework import serializers

from apps.common.media_metadata import validate_upload_limits
from .models import AIAttachment, AISettings

ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".pdf", ".docx", ".txt", ".csv", ".md", ".json", ".xlsx", ".pptx",
    ".png", ".jpg", ".jpeg", ".webp",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
TEXT_EXTENSIONS = {".txt", ".csv", ".md", ".json"}


def _reset(file_obj, position=0):
    try:
        file_obj.seek(position or 0)
    except Exception:
        pass


def validate_ai_attachment(file_obj, cfg: AISettings | None = None) -> str:
    cfg = cfg or AISettings.load()
    max_bytes = int(cfg.max_attachment_mb) * 1024 * 1024
    suffix = Path(getattr(file_obj, "name", "")).suffix.lower()
    validate_upload_limits(file_obj, max_bytes=max_bytes, extensions=ALLOWED_ATTACHMENT_EXTENSIONS, field="file")
    if suffix in IMAGE_EXTENSIONS:
        position = None
        try:
            position = file_obj.tell()
        except Exception:
            pass
        try:
            file_obj.seek(0)
            image = Image.open(file_obj)
            width, height = image.size
            if width <= 0 or height <= 0 or width > 12000 or height > 12000 or (width * height) > 25_000_000:
                raise serializers.ValidationError({"file": "Image trop grande. Limite : 25 mégapixels."})
            image.verify()
            if image.format not in {"PNG", "JPEG", "WEBP"}:
                raise serializers.ValidationError({"file": "Format d'image non autorisé."})
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise serializers.ValidationError({"file": "Image invalide ou corrompue."}) from exc
        finally:
            _reset(file_obj, position)
    return suffix


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _xml_text(xml_bytes: bytes) -> str:
    try:
        root = ElementTree.fromstring(xml_bytes)
        values = []
        for node in root.iter():
            if node.text and node.text.strip():
                values.append(node.text.strip())
        return " ".join(values)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", xml_bytes.decode("utf-8", errors="ignore"))
        return re.sub(r"\s+", " ", text)


def _extract_docx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        parts = []
        for name in names:
            if name == "word/document.xml" or name.startswith("word/header") or name.startswith("word/footer"):
                parts.append(_xml_text(archive.read(name)))
        return "\n".join(parts)


def _extract_xlsx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        parts = []
        if "xl/sharedStrings.xml" in names:
            parts.append(_xml_text(archive.read("xl/sharedStrings.xml")))
        for name in names:
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                parts.append(_xml_text(archive.read(name)))
        return "\n".join(parts)


def _extract_pptx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        slides = sorted(name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
        return "\n".join(_xml_text(archive.read(name)) for name in slides)


def extract_attachment_text(file_obj, suffix: str, max_chars: int) -> tuple[str, str, str]:
    """Retourne (texte, statut, erreur). L'extraction est bornée et ne fait aucun OCR."""
    if suffix in IMAGE_EXTENSIONS:
        return "", AIAttachment.ExtractionStatus.IMAGE, ""

    position = None
    try:
        position = file_obj.tell()
    except Exception:
        pass
    try:
        file_obj.seek(0)
        data = file_obj.read()
        text = ""
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(data))
            pages = []
            for page in reader.pages[:40]:
                pages.append(page.extract_text() or "")
                if sum(len(x) for x in pages) >= max_chars * 2:
                    break
            text = "\n".join(pages)
        elif suffix == ".docx":
            text = _extract_docx(data)
        elif suffix == ".xlsx":
            text = _extract_xlsx(data)
        elif suffix == ".pptx":
            text = _extract_pptx(data)
        elif suffix in TEXT_EXTENSIONS:
            raw = _decode_text(data)
            if suffix == ".csv":
                # Normalize delimiters/rows so the model receives a predictable text view.
                sample = raw[:8192]
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                    from itertools import islice
                    rows = csv.reader(io.StringIO(raw), dialect)
                    text = "\n".join(" | ".join(cell.strip() for cell in row[:40]) for row in islice(rows, 1000))
                except Exception:
                    text = raw
            else:
                text = raw
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text or "")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()[:max_chars]
        if text:
            return text, AIAttachment.ExtractionStatus.READY, ""
        return "", AIAttachment.ExtractionStatus.NO_TEXT, "Aucun texte extractible."
    except Exception as exc:
        return "", AIAttachment.ExtractionStatus.FAILED, str(exc)[:450]
    finally:
        _reset(file_obj, position)


def attachment_mime_type(file_obj, suffix: str) -> str:
    client = str(getattr(file_obj, "content_type", "") or "").strip().lower()
    guessed = mimetypes.guess_type(getattr(file_obj, "name", ""))[0] or "application/octet-stream"
    if suffix == ".jpg":
        guessed = "image/jpeg"
    return client or guessed


def serialize_attachment(row: AIAttachment) -> dict:
    return {
        "id": row.id,
        "name": row.original_name,
        "mime_type": row.mime_type,
        "extension": row.extension,
        "size_bytes": row.size_bytes,
        "extraction_status": row.extraction_status,
        "extraction_error": row.extraction_error,
        "is_image": row.is_image,
        "download_path": f"/api/ai/attachments/{row.id}/download/",
        "created_at": row.created_at,
    }


def attachment_context(rows: list[AIAttachment], *, total_chars: int = 32000) -> str:
    """Builds prompt context from private user attachments; never treats content as instructions."""
    blocks = []
    remaining = max(total_chars, 2000)
    for index, row in enumerate(rows, start=1):
        header = f"[FICHIER {index}] {row.original_name} ({row.extension}, {row.size_bytes} octets)"
        if row.extraction_status == AIAttachment.ExtractionStatus.READY and row.extracted_text:
            excerpt = row.extracted_text[:remaining]
            blocks.append(header + "\n" + excerpt)
            remaining -= len(excerpt)
        elif row.extraction_status == AIAttachment.ExtractionStatus.IMAGE:
            blocks.append(header + "\nImage jointe. Le contenu visuel est fourni au modèle uniquement si la vision est activée côté serveur.")
        else:
            blocks.append(header + f"\nTexte non disponible ({row.extraction_status}).")
        if remaining <= 500:
            break
    return "\n\n".join(blocks)


def image_data_urls(rows: list[AIAttachment], *, max_images: int = 3, max_bytes_each: int = 4 * 1024 * 1024) -> list[str]:
    import base64
    urls = []
    for row in rows:
        if not row.is_image or row.size_bytes > max_bytes_each or len(urls) >= max_images:
            continue
        try:
            row.file.open("rb")
            data = row.file.read(max_bytes_each + 1)
            row.file.close()
            if len(data) > max_bytes_each:
                continue
            mime = row.mime_type if row.mime_type.startswith("image/") else "image/jpeg"
            urls.append(f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}")
        except Exception:
            try:
                row.file.close()
            except Exception:
                pass
    return urls
