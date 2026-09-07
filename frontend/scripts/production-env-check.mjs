const args = new Set(process.argv.slice(2));
const jsonMode = args.has("--json");

const blockers = [];
const warnings = [];

function clean(value) {
  return String(value || "").trim();
}

function parseUrl(name, value, protocols) {
  const raw = clean(value);
  if (!raw) {
    blockers.push(`${name.toLowerCase()}_missing`);
    return null;
  }
  try {
    const url = new URL(raw);
    if (!protocols.includes(url.protocol)) blockers.push(`${name.toLowerCase()}_invalid_protocol`);
    if (["localhost", "127.0.0.1", "0.0.0.0"].includes(url.hostname)) blockers.push(`${name.toLowerCase()}_local_host`);
    return url;
  } catch {
    blockers.push(`${name.toLowerCase()}_invalid_url`);
    return null;
  }
}

const apiProxy = parseUrl("API_PROXY_TARGET", process.env.API_PROXY_TARGET, ["https:"]);
if (apiProxy && /\/api\/?$/.test(apiProxy.pathname)) blockers.push("api_proxy_target_must_not_end_with_api");

if (clean(process.env.NEXT_PUBLIC_API_URL) !== "/api") blockers.push("next_public_api_url_must_be_same_origin_api");
parseUrl("NEXT_PUBLIC_WS_URL", process.env.NEXT_PUBLIC_WS_URL, ["wss:"]);

const mediaOrigin = clean(process.env.NEXT_PUBLIC_MEDIA_ORIGIN);
if (mediaOrigin) parseUrl("NEXT_PUBLIC_MEDIA_ORIGIN", mediaOrigin, ["https:"]);
else warnings.push("next_public_media_origin_missing");

for (const [key, value] of Object.entries(process.env)) {
  if (!key.startsWith("NEXT_PUBLIC_")) continue;
  if (!clean(value)) continue;
  if (/(SECRET|TOKEN|PASSWORD|CREDENTIAL|PRIVATE|API_KEY|ACCESS_KEY)/i.test(key)) {
    blockers.push(`public_secret_like_variable:${key}`);
  }
}

const snapshot = {
  status: blockers.length ? "error" : "ok",
  api_proxy_target: apiProxy ? apiProxy.origin + apiProxy.pathname.replace(/\/+$/, "") : "",
  next_public_api_url: clean(process.env.NEXT_PUBLIC_API_URL),
  websocket_configured: Boolean(clean(process.env.NEXT_PUBLIC_WS_URL)),
  media_origin_configured: Boolean(mediaOrigin),
  blockers: [...new Set(blockers)].sort(),
  warnings: [...new Set(warnings)].sort(),
};

if (jsonMode) {
  console.log(JSON.stringify(snapshot));
} else {
  console.log(`KalanPro frontend production preflight: ${snapshot.status}`);
  for (const item of snapshot.blockers) console.error(`BLOCKER ${item}`);
  for (const item of snapshot.warnings) console.warn(`WARNING ${item}`);
}

if (snapshot.status !== "ok") process.exit(1);
