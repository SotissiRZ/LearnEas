import { rm } from "node:fs/promises";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const distDir = ".next-build-check";

// A validation build may be launched while `next dev` is running in the same Docker
// container. Using an isolated distDir prevents Next from deleting/replacing the
// live development manifests.
await rm(path.join(root, distDir), { recursive: true, force: true });

const nextBin = path.join(root, "node_modules", "next", "dist", "bin", "next");
const child = spawn(process.execPath, [nextBin, "build"], {
  cwd: root,
  stdio: "inherit",
  env: { ...process.env, NEXT_DIST_DIR: distDir },
});

const code = await new Promise((resolve, reject) => {
  child.once("error", reject);
  child.once("exit", (value, signal) => {
    if (signal) reject(new Error(`next build arrêté par le signal ${signal}`));
    else resolve(value ?? 1);
  });
});

await rm(path.join(root, distDir), { recursive: true, force: true });
process.exit(code);
