import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));

// The frontend is mounted at /app in docker-compose.dev.yml. Selected,
// non-secret repository paths are mounted read-only under /workspace so structural
// tests can inspect backend/Compose/CI/deployment contracts without process.cwd().
export const frontendRoot = path.resolve(scriptDir, "..");
export const repoRoot = process.env.KALANPRO_REPO_ROOT
  ? path.resolve(process.env.KALANPRO_REPO_ROOT)
  : path.resolve(frontendRoot, "..");

export const readFrontend = (file) =>
  fs.readFileSync(path.resolve(frontendRoot, file), "utf8");

export const readRepo = (file) =>
  fs.readFileSync(path.resolve(repoRoot, file), "utf8");

export const readLegacyRelative = (file) => {
  if (file.startsWith("../")) {
    return readRepo(file.slice(3));
  }
  return readFrontend(file);
};
