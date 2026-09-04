import "server-only";
import { unstable_cache } from "next/cache";

const API_URL = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://backend:8000/api";

type CachedResult<T> = { data: T; ok: boolean; error?: string };
type CacheTtl = 15 | 30 | 60 | 300;

async function fetchPublicJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      // `unstable_cache` gère la durée de vie. Le fetch interne reste explicite pour ne pas
      // dépendre du mode dynamique requis par le nonce CSP global.
      cache: "no-store",
    });
  } catch {
    throw new Error("Impossible de contacter le serveur.");
  }
  if (!response.ok) {
    if (response.status >= 500) throw new Error("Le serveur rencontre temporairement un problème.");
    throw new Error(`API ${response.status}`);
  }
  return response.json() as Promise<T>;
}

const cached15 = unstable_cache(fetchPublicJson, ["kalanpro-public-api-v1-15"], { revalidate: 15 });
const cached30 = unstable_cache(fetchPublicJson, ["kalanpro-public-api-v1-30"], { revalidate: 30 });
const cached60 = unstable_cache(fetchPublicJson, ["kalanpro-public-api-v1-60"], { revalidate: 60 });
const cached300 = unstable_cache(fetchPublicJson, ["kalanpro-public-api-v1-300"], { revalidate: 300 });

function getter(ttl: CacheTtl) {
  if (ttl === 15) return cached15;
  if (ttl === 30) return cached30;
  if (ttl === 300) return cached300;
  return cached60;
}

/**
 * Lecture publique mise en cache côté Next.js. Elle est réservée aux données qui ne dépendent
 * pas de la session utilisateur (catalogues, catégories, domaines, page d'accueil).
 */
export async function safePublicGet<T>(path: string, fallback: T, ttl: CacheTtl = 60): Promise<CachedResult<T>> {
  try {
    const data = await getter(ttl)<T>(path);
    return { data, ok: true };
  } catch (error) {
    return { data: fallback, ok: false, error: error instanceof Error ? error.message : String(error) };
  }
}
