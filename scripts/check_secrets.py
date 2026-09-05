#!/usr/bin/env python3
"""Scan léger de secrets à haute confiance, sans envoyer le dépôt à un service externe."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE_ROOTS = ["backend", "frontend", "docker", ".github"]
ROOT_FILES = ["docker-compose.yml", "docker-compose.dev.yml", "Makefile"]
SKIP_NAMES = {
    "package-lock.json",  # intégrités npm, très bruyantes et non secrètes
    "check_secrets.py",
}
SKIP_PARTS = {".git", "node_modules", ".next", ".next-build-check", "__pycache__", "media", "staticfiles"}
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".json", ".yml", ".yaml", ".md", ".sh", ".conf", ".txt"}

# Construits en fragments pour que ce fichier ne se signale pas lui-même.
PATTERNS = {
    "private-key": re.compile("BEGIN " + "(?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "stripe-secret": re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "openai-like-key": re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}


def candidate_files():
    for root_name in INCLUDE_ROOTS:
        base = ROOT / root_name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.name in SKIP_NAMES or any(part in SKIP_PARTS for part in path.parts):
                continue
            if path.suffix.lower() in TEXT_SUFFIXES or path.name.startswith(".env"):
                yield path
    for name in ROOT_FILES:
        path = ROOT / name
        if path.is_file():
            yield path


def main() -> int:
    findings = []
    for path in candidate_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append((path.relative_to(ROOT), line, label))
    if findings:
        print("Secrets potentiels détectés :", file=sys.stderr)
        for path, line, label in findings:
            print(f"- {path}:{line} [{label}]", file=sys.stderr)
        return 1
    print("Secret scan: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
