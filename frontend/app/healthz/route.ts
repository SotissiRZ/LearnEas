/**
 * Lightweight liveness endpoint for Docker/orchestrator health checks.
 *
 * Keep this route independent from the backend: probing the homepage would execute
 * its Server Component and therefore trigger several catalogue API requests every
 * few seconds, eventually exhausting DRF's anonymous throttle budget.
 */
export const dynamic = "force-static";

export function GET() {
  return new Response("ok\n", {
    status: 200,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
