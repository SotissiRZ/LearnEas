import { api, ApiError } from "@/lib/api";

export type DirectUploadCapabilities = {
  direct_multipart: boolean;
  part_size_bytes: number;
  max_video_upload_mb: number;
};

type DirectUploadStart = {
  section: number;
  object_key: string;
  upload_id: string;
  part_size_bytes: number;
  parts_count: number;
  content_type: string;
};

type SignedPart = {
  url: string;
  part_number: number;
};

type CompletedPart = {
  PartNumber: number;
  ETag: string;
};

function uploadPart(
  url: string,
  blob: Blob,
  onProgress: (loaded: number) => void,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url, true);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded);
    };
    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new ApiError(`Le bloc vidéo a été refusé par le stockage (${xhr.status}).`));
        return;
      }
      const etag = xhr.getResponseHeader("ETag");
      if (!etag) {
        reject(new ApiError(
          "Le stockage n'expose pas l'en-tête ETag. Ajoutez ETag à ExposeHeaders dans la politique CORS du bucket S3/R2.",
        ));
        return;
      }
      resolve(etag);
    };
    xhr.onerror = () => reject(new ApiError("Connexion interrompue pendant l'envoi d'un bloc vidéo."));
    xhr.onabort = () => reject(new ApiError("Upload vidéo annulé."));
    xhr.send(blob);
  });
}

async function uploadPartWithRetry(
  start: DirectUploadStart,
  partNumber: number,
  blob: Blob,
  onProgress: (loaded: number) => void,
): Promise<string> {
  let lastError: unknown = null;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      // Une nouvelle URL est générée à chaque tentative. Ainsi un upload lent n'échoue pas
      // parce qu'une URL présignée préparée longtemps à l'avance a expiré.
      const signed = await api.post<SignedPart>("/catalog/lessons/direct-upload-part/", {
        object_key: start.object_key,
        upload_id: start.upload_id,
        part_number: partNumber,
      });
      return await uploadPart(signed.url, blob, onProgress);
    } catch (error) {
      lastError = error;
      if (attempt < 3) {
        await new Promise((resolve) => window.setTimeout(resolve, 700 * attempt));
      }
    }
  }
  throw lastError instanceof Error ? lastError : new ApiError("Échec de l'envoi d'un bloc vidéo.");
}

export async function uploadLessonVideoMultipart({
  sectionId,
  title,
  file,
  isPreview,
  subtitles,
  transcript,
  onProgress,
}: {
  sectionId: number;
  title: string;
  file: File;
  isPreview: boolean;
  subtitles: File | null;
  transcript: string;
  onProgress: (percent: number) => void;
}): Promise<void> {
  const start = await api.post<DirectUploadStart>("/catalog/lessons/direct-upload-start/", {
    section: sectionId,
    filename: file.name,
    size: file.size,
    content_type: file.type || "application/octet-stream",
  });

  const parts: CompletedPart[] = [];
  let completedBytes = 0;

  try {
    for (let partNumber = 1; partNumber <= start.parts_count; partNumber += 1) {
      const from = (partNumber - 1) * start.part_size_bytes;
      const to = Math.min(file.size, from + start.part_size_bytes);
      const blob = file.slice(from, to);
      const etag = await uploadPartWithRetry(start, partNumber, blob, (loaded) => {
        const uploaded = Math.min(file.size, completedBytes + loaded);
        onProgress(Math.max(0, Math.min(99, Math.round((uploaded / file.size) * 100))));
      });
      parts.push({ PartNumber: partNumber, ETag: etag });
      completedBytes += blob.size;
      onProgress(Math.max(0, Math.min(99, Math.round((completedBytes / file.size) * 100))));
    }

    const complete = new FormData();
    complete.append("section", String(sectionId));
    complete.append("title", title);
    complete.append("order", "1");
    complete.append("is_preview", String(isPreview));
    complete.append("transcript", transcript);
    complete.append("object_key", start.object_key);
    complete.append("upload_id", start.upload_id);
    complete.append("expected_size", String(file.size));
    complete.append("parts", JSON.stringify(parts));
    if (subtitles) complete.append("subtitles_file", subtitles);

    await api.post("/catalog/lessons/direct-upload-complete/", complete);
    onProgress(100);
  } catch (error) {
    try {
      await api.post("/catalog/lessons/direct-upload-abort/", {
        object_key: start.object_key,
        upload_id: start.upload_id,
      });
    } catch {
      // Best effort : le fournisseur S3/R2 peut aussi purger les multipart incomplets via
      // une règle lifecycle. L'erreur originale reste celle qui doit être montrée à l'utilisateur.
    }
    throw error;
  }
}
