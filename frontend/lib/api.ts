/**
 * En environnement Docker, le frontend a besoin de DEUX URLs différentes pour joindre l'API :
 *  - Côté NAVIGATEUR (client) : une URL publique, accessible depuis la machine de l'utilisateur
 *    (ex: http://localhost/api, routée par nginx). C'est NEXT_PUBLIC_API_URL.
 *  - Côté SERVEUR (rendu SSR des Server Components, qui s'exécute DANS le conteneur Next.js) :
 *    "localhost" y désigne le conteneur frontend lui-même, pas nginx/backend ! Il faut donc une
 *    URL interne au réseau Docker (ex: http://backend:8000/api). C'est INTERNAL_API_URL, une
 *    variable serveur-only (non préfixée NEXT_PUBLIC_), donc pas besoin de rebuild l'image pour
 *    la changer : elle est lue à l'exécution.
 * En dehors de Docker (dev local classique), les deux valeurs sont identiques et ce mécanisme
 * est transparent.
 */
/**
 * En environnement Docker, le frontend a besoin de DEUX URLs différentes pour joindre l'API :
 *  - Côté NAVIGATEUR (client) : on utilise une URL RELATIVE ("/api"), pour que la requête reste
 *    TOUJOURS sur la même origine que la page · que le site soit ouvert via http://localhost ou
 *    http://127.0.0.1 (ce sont deux origines DIFFÉRENTES du point de vue du navigateur/CORS, même
 *    si elles pointent vers la même machine !). Une URL relative supprime totalement ce risque.
 *  - Côté SERVEUR (rendu SSR des Server Components, qui s'exécute DANS le conteneur Next.js) :
 *    "localhost" y désigne le conteneur frontend lui-même, pas nginx/backend ! Il faut donc une
 *    URL interne au réseau Docker (http://backend:8000/api, le nom du service). C'est
 *    INTERNAL_API_URL, une variable serveur-only (non préfixée NEXT_PUBLIC_), donc pas besoin de
 *    rebuild l'image pour la changer : elle est lue à l'exécution.
 * En dehors de Docker (dev local classique avec `npm run dev`), définissez NEXT_PUBLIC_API_URL
 * dans .env.local (ex: http://localhost:8000/api) pour retrouver le comportement absolu habituel.
 */
const API_URL =
  typeof window === "undefined"
    ? process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://backend:8000/api"
    : process.env.NEXT_PUBLIC_API_URL || "/api";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("learneas_access");
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  const refresh = localStorage.getItem("learneas_refresh");
  if (!refresh) return null;
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_URL}/auth/token/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
        cache: "no-store",
      });
      if (!response.ok) throw new Error("Refresh JWT refusé");
      const data = await response.json() as { access?: string; refresh?: string };
      if (!data.access) throw new Error("Nouveau jeton absent");
      localStorage.setItem("learneas_access", data.access);
      if (data.refresh) localStorage.setItem("learneas_refresh", data.refresh);
      return data.access;
    } catch {
      localStorage.removeItem("learneas_access");
      localStorage.removeItem("learneas_refresh");
      localStorage.removeItem("learneas_user");
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

const FIELD_LABELS: Record<string, string> = {
  username: "Nom d'utilisateur",
  email: "Email",
  password: "Mot de passe",
  password2: "Confirmation du mot de passe",
  first_name: "Prénom",
  last_name: "Nom",
  country: "Pays",
  non_field_errors: "",
  detail: "",
};

/** Transforme une réponse d'erreur DRF ({champ: [messages]} ou {detail: "..."})
 * en un message clair, lisible par un humain, sans JSON brut. */
export class ApiError extends Error {
  fieldErrors: Record<string, string[]>;
  constructor(message: string, fieldErrors: Record<string, string[]> = {}) {
    super(message);
    this.fieldErrors = fieldErrors;
  }
}

function buildErrorMessage(status: number, data: unknown): ApiError {
  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;

    if (typeof obj.detail === "string") {
      return new ApiError(obj.detail);
    }

    const fieldErrors: Record<string, string[]> = {};
    const messages: string[] = [];
    for (const [key, value] of Object.entries(obj)) {
      const list = Array.isArray(value) ? value.map(String) : [String(value)];
      fieldErrors[key] = list;
      const label = FIELD_LABELS[key] ?? key;
      for (const msg of list) {
        messages.push(label ? `${label} : ${msg}` : msg);
      }
    }
    if (messages.length > 0) {
      return new ApiError(messages.join(" · "), fieldErrors);
    }
  }
  if (status === 401) return new ApiError("Identifiants invalides ou session expirée.");
  if (status === 403) return new ApiError("Vous n'avez pas les droits nécessaires pour cette action.");
  if (status === 404) return new ApiError("Ressource introuvable.");
  if (status >= 500) return new ApiError("Erreur serveur, veuillez réessayer dans quelques instants.");
  return new ApiError(`Une erreur est survenue (${status}).`);
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.body && !(options.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) || {}),
  };

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, headers, cache: "no-store" });
  } catch {
    throw new ApiError(
      "Impossible de contacter le serveur. Vérifiez votre connexion ou réessayez plus tard."
    );
  }

  if (res.status === 401 && token && typeof window !== "undefined" && !path.includes("/auth/token/refresh/")) {
    const renewed = await refreshAccessToken();
    if (renewed) {
      headers.Authorization = `Bearer ${renewed}`;
      try {
        res = await fetch(`${API_URL}${path}`, { ...options, headers, cache: "no-store" });
      } catch {
        throw new ApiError("Impossible de contacter le serveur. Vérifiez votre connexion ou réessayez plus tard.");
      }
    }
  }

  if (!res.ok) {
    let data: unknown = null;
    try {
      data = await res.json();
    } catch {
      /* corps vide ou non-JSON */
    }
    throw buildErrorMessage(res.status, data);
  }
  if (res.status === 204) return undefined as unknown as T;
  try {
    return await res.json();
  } catch {
    return undefined as unknown as T;
  }
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  post: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, {
      method: "PATCH",
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    }),
  del: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
};

/**
 * Upload d'un FormData (fichier vidéo/PDF/image) avec suivi de progression réel · `fetch()` ne
 * permet pas d'observer la progression d'un envoi, on utilise donc XMLHttpRequest pour ce cas
 * précis. `onProgress` reçoit un pourcentage (0-100).
 */
export async function apiUploadWithProgress<T>(
  path: string,
  formData: FormData,
  onProgress?: (percent: number) => void,
  method: "POST" | "PATCH" = "POST"
): Promise<T> {
  const attempt = (token: string | null) => new Promise<{ status: number; data: unknown }>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, `${API_URL}${path}`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onload = () => {
      let data: unknown = null;
      try { data = xhr.responseText ? JSON.parse(xhr.responseText) : null; } catch { /* réponse non JSON */ }
      resolve({ status: xhr.status, data });
    };
    xhr.onerror = () => reject(new ApiError("Impossible de contacter le serveur. Vérifiez votre connexion ou réessayez plus tard."));
    xhr.send(formData);
  });

  let result = await attempt(getToken());
  if (result.status === 401 && typeof window !== "undefined") {
    const renewed = await refreshAccessToken();
    if (renewed) result = await attempt(renewed);
  }
  if (result.status < 200 || result.status >= 300) throw buildErrorMessage(result.status, result.data);
  return result.data as T;
}

/**
 * Pour les Server Components : tente l'appel API et retourne `fallback` en cas d'échec,
 * SANS masquer l'information. `ok: false` signale une vraie panne (API injoignable) à distinguer
 * d'un résultat simplement vide (`ok: true`, tableau/liste vide) · évite la confusion "aucune
 * donnée" alors qu'il s'agit en réalité d'une erreur réseau/configuration.
 */
export async function safeGet<T>(
  path: string,
  fallback: T
): Promise<{ data: T; ok: boolean; error?: string }> {
  try {
    const data = await apiFetch<T>(path);
    return { data, ok: true };
  } catch (e) {
    return { data: fallback, ok: false, error: e instanceof ApiError ? e.message : String(e) };
  }
}

export function formatPrice(value: number | string): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (n === 0) return "Gratuit";
  return `${n.toLocaleString("fr-FR", { minimumFractionDigits: 0 })} MAD`;
}

export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} min`;
  if (m === 0) return `${h} h`;
  return `${h} h ${m} min`;
}

export function levelLabel(level: string): string {
  return { beginner: "Débutant", intermediate: "Intermédiaire", expert: "Expert" }[level] || level;
}

/** Télécharge une ressource protégée avec le même jeton JWT que les appels API. */
export async function apiDownload(path: string, filename = "download"): Promise<void> {
  const doFetch = (token: string | null) => fetch(`${API_URL}${path}`, {
    method: "GET",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });

  let response: Response;
  try {
    response = await doFetch(getToken());
    if (response.status === 401 && typeof window !== "undefined") {
      const renewed = await refreshAccessToken();
      if (renewed) response = await doFetch(renewed);
    }
  } catch {
    throw new ApiError("Impossible de télécharger le fichier. Vérifiez votre connexion.");
  }
  if (!response.ok) {
    let data: unknown = null;
    try { data = await response.json(); } catch { /* réponse non JSON */ }
    throw buildErrorMessage(response.status, data);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
