import assert from "node:assert/strict";
import { test } from "node:test";
import { readFrontend, readRepo } from "./test-paths.mjs";

const read = (path) => readFrontend(path);
const repo = (path) => readRepo(path);

test("v91 expose une politique RTC bornée et plusieurs STUN/TURN", () => {
  const rtc = repo("backend/apps/formations/rtc.py");
  const settings = repo("backend/learneas/settings.py");
  assert.match(rtc, /RTC_STUN_URLS/);
  assert.match(rtc, /RTC_TURN_URLS/);
  assert.match(rtc, /def rtc_policy/);
  assert.match(rtc, /"topology": "mesh"/);
  assert.match(rtc, /"recommended_topology": "sfu" if recommended else "mesh"/);
  assert.match(settings, /RTC_MESH_SOFT_LIMIT/);
  assert.match(settings, /RTC_SFU_RECOMMEND_THRESHOLD/);
  assert.match(settings, /RTC_ICE_TRANSPORT_POLICY/);
});

test("v91 télémétrie WebRTC reste éphémère dans le cache", () => {
  const quality = repo("backend/apps/formations/quality.py");
  const views = repo("backend/apps/formations/views.py");
  assert.match(quality, /cache\.set\(key, snapshot, timeout=ttl\)/);
  assert.match(quality, /packet_loss_pct/);
  assert.match(quality, /avg_rtt_ms/);
  assert.match(views, /url_path="quality"/);
  assert.match(views, /record_session_quality/);
  assert.match(views, /session_quality_snapshot/);
});

test("v91 ne supprime plus immédiatement un pair sur disconnected", () => {
  const live = read("app/live/session/[id]/page.tsx");
  assert.match(live, /RTC_DISCONNECT_GRACE_SECONDS|disconnect_grace_seconds/);
  assert.match(live, /pc\.restartIce\(\)/);
  assert.match(live, /createOffer\(\{ iceRestart: true \}\)/);
  assert.match(live, /room\.user\.id < peerId/);
  assert.doesNotMatch(live, /\["failed", "closed", "disconnected"\]\.includes\(pc\.connectionState\)[\s\S]{0,180}peersRef\.current\.delete/);
});

test("v91 adapte le bitrate mesh et collecte getStats", () => {
  const live = read("app/live/session/[id]/page.tsx");
  assert.match(live, /sender\.setParameters\(params\)/);
  assert.match(live, /maxBitrate/);
  assert.match(live, /pc\.getStats\(\)/);
  assert.match(live, /packetLossPct/);
  assert.match(live, /\/quality\//);
  assert.match(live, /topologie WebRTC mesh/);
});

test("v91 observabilité admin agrège qualité live sans activer un faux SFU", () => {
  const operations = repo("backend/apps/common/operations.py");
  const admin = read("app/dashboard/admin/page.tsx");
  assert.match(operations, /poor_quality_reports/);
  assert.match(operations, /avg_packet_loss_pct/);
  assert.match(operations, /"active_adapter": False/);
  assert.match(admin, /Qualité faible/);
  assert.match(admin, /SFU prêt/);
});

test("v91 compose et exemples exposent la configuration RTC de production", () => {
  const dev = repo("docker-compose.dev.yml");
  const prod = repo("docker-compose.yml");
  const env = repo(".env.production.example");
  for (const text of [dev, prod, env]) {
    assert.match(text, /RTC_MESH_SOFT_LIMIT/);
    assert.match(text, /RTC_SFU_RECOMMEND_THRESHOLD/);
    assert.match(text, /RTC_QUALITY_INTERVAL_SECONDS/);
  }
});

test("v91 fournit un rapport de capacité pour décider du SFU sur données réelles", () => {
  const command = repo("backend/apps/formations/management/commands/rtc_capacity_report.py");
  assert.match(command, /--fail-on-sfu-recommended/);
  assert.match(command, /sfu_recommended_sessions/);
  assert.match(command, /session_quality_snapshot/);
  assert.match(command, /active_participants=Count/);
});
