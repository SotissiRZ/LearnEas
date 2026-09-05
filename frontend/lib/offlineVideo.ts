import { resolveMediaUrl } from "@/lib/media";

const DB_NAME = "kalanpro-offline-media";
const DB_VERSION = 2;
const STORE = "videos";

export type OfflineVideoRecord = {
  key: string;
  userId: number;
  lessonId: number;
  courseId: number;
  title: string;
  blob: Blob;
  size: number;
  contentType: string;
  progressToken?: string | null;
  downloadedAt: number;
};

function keyFor(userId: number, courseId: number, lessonId: number): string {
  return `${userId}:${courseId}:${lessonId}`;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("Le stockage hors connexion n'est pas disponible sur ce navigateur."));
      return;
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (event) => {
      const db = request.result;
      let store: IDBObjectStore;
      if (!db.objectStoreNames.contains(STORE)) {
        store = db.createObjectStore(STORE, { keyPath: "key" });
      } else {
        store = request.transaction!.objectStore(STORE);
      }
      if (!store.indexNames.contains("courseId")) store.createIndex("courseId", "courseId", { unique: false });
      if (!store.indexNames.contains("userId")) store.createIndex("userId", "userId", { unique: false });
      if (!store.indexNames.contains("userCourse")) store.createIndex("userCourse", ["userId", "courseId"], { unique: false });

      // Les copies v1 n'étaient pas rattachées à un utilisateur. Elles sont supprimées lors de
      // l'upgrade afin qu'un autre compte utilisant le même navigateur ne puisse jamais les voir.
      if ((event.oldVersion || 0) < 2) store.clear();
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("Stockage hors connexion indisponible."));
  });
}

async function transaction<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore, resolve: (value: T) => void, reject: (reason?: unknown) => void) => void): Promise<T> {
  const db = await openDb();
  return new Promise<T>((resolve, reject) => {
    const tx = db.transaction(STORE, mode);
    const store = tx.objectStore(STORE);
    run(store, resolve, reject);
    tx.oncomplete = () => db.close();
    tx.onerror = () => { db.close(); reject(tx.error || new Error("Erreur de stockage hors connexion.")); };
    tx.onabort = () => { db.close(); reject(tx.error || new Error("Opération hors connexion annulée.")); };
  });
}

export async function hasOfflineVideo(userId: number, courseId: number, lessonId: number): Promise<boolean> {
  return transaction<boolean>("readonly", (store, resolve, reject) => {
    const request = store.getKey(keyFor(userId, courseId, lessonId));
    request.onsuccess = () => resolve(request.result != null);
    request.onerror = () => reject(request.error);
  });
}

export async function getOfflineVideo(userId: number, courseId: number, lessonId: number): Promise<OfflineVideoRecord | null> {
  return transaction<OfflineVideoRecord | null>("readonly", (store, resolve, reject) => {
    const request = store.get(keyFor(userId, courseId, lessonId));
    request.onsuccess = () => resolve((request.result as OfflineVideoRecord | undefined) || null);
    request.onerror = () => reject(request.error);
  });
}

export async function listOfflineLessonIds(userId: number, courseId: number): Promise<number[]> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const index = tx.objectStore(STORE).index("userCourse");
    const request = index.getAll(IDBKeyRange.only([userId, courseId]));
    request.onsuccess = () => resolve((request.result as OfflineVideoRecord[]).map((row) => row.lessonId));
    request.onerror = () => reject(request.error);
    tx.oncomplete = () => db.close();
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

export async function listOfflineVideos(userId: number): Promise<OfflineVideoRecord[]> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const index = tx.objectStore(STORE).index("userId");
    const request = index.getAll(IDBKeyRange.only(userId));
    request.onsuccess = () => resolve((request.result as OfflineVideoRecord[]).sort((a, b) => b.downloadedAt - a.downloadedAt));
    request.onerror = () => reject(request.error);
    tx.oncomplete = () => db.close();
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

async function ensureQuota(expectedSize: number): Promise<void> {
  const storage = navigator.storage;
  if (!storage?.estimate) return;
  try {
    const estimate = await storage.estimate();
    const quota = Number(estimate.quota || 0);
    const usage = Number(estimate.usage || 0);
    if (quota > 0 && expectedSize > 0 && quota - usage < expectedSize * 1.1) {
      throw new Error("Espace de stockage insuffisant pour cette vidéo hors connexion.");
    }
    await storage.persist?.();
  } catch (error) {
    if (error instanceof Error && error.message.includes("insuffisant")) throw error;
  }
}

export async function downloadOfflineVideo({
  userId,
  courseId,
  lessonId,
  title,
  url,
  expectedSize = 0,
  progressToken = null,
  onProgress,
}: {
  userId: number;
  courseId: number;
  lessonId: number;
  title: string;
  url: string;
  expectedSize?: number;
  progressToken?: string | null;
  onProgress?: (percent: number) => void;
}): Promise<OfflineVideoRecord> {
  await ensureQuota(expectedSize);
  const response = await fetch(resolveMediaUrl(url), {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Téléchargement refusé (${response.status}).`);

  const contentLength = Number(response.headers.get("content-length") || expectedSize || 0);
  const contentType = response.headers.get("content-type") || "video/mp4";
  let blob: Blob;

  if (response.body && typeof ReadableStream !== "undefined") {
    const reader = response.body.getReader();
    const chunks: Uint8Array[] = [];
    let loaded = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value) {
        chunks.push(value);
        loaded += value.byteLength;
        if (contentLength > 0) onProgress?.(Math.min(99, Math.round((loaded / contentLength) * 100)));
      }
    }
    blob = new Blob(chunks, { type: contentType });
  } else {
    blob = await response.blob();
  }

  if (!blob.size) throw new Error("La copie hors connexion téléchargée est vide.");
  const record: OfflineVideoRecord = {
    key: keyFor(userId, courseId, lessonId),
    userId,
    lessonId,
    courseId,
    title,
    blob,
    size: blob.size,
    contentType,
    progressToken,
    downloadedAt: Date.now(),
  };

  await transaction<void>("readwrite", (store, resolve, reject) => {
    const request = store.put(record);
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
  try { localStorage.setItem("kalanpro:offline-user-id", String(userId)); } catch {}
  onProgress?.(100);
  return record;
}

export async function removeOfflineVideo(userId: number, courseId: number, lessonId: number): Promise<void> {
  await transaction<void>("readwrite", (store, resolve, reject) => {
    const request = store.delete(keyFor(userId, courseId, lessonId));
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

export function formatOfflineSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "taille inconnue";
  const mb = bytes / 1024 / 1024;
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} Go` : `${Math.max(1, Math.round(mb))} Mo`;
}
