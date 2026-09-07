from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core import checks
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.common.operations import _broker_check, _cache_check, _database_check, _storage_check


def _pending_migrations() -> list[str]:
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    plan = executor.migration_plan(targets)
    return [f"{migration.app_label}.{migration.name}" for migration, backwards in plan if not backwards]


def _django_checks(*, deploy: bool) -> list[dict[str, Any]]:
    messages = checks.run_checks(include_deployment_checks=deploy)
    threshold = checks.WARNING if deploy else checks.ERROR
    return [
        {
            "level": int(message.level),
            "id": str(message.id or ""),
            "message": str(message.msg),
            "hint": str(message.hint or ""),
        }
        for message in messages
        if message.level >= threshold
    ]


def build_release_gate_snapshot(*, strict_infra: bool = False, deploy: bool = False) -> dict[str, Any]:
    """Build a deterministic release qualification snapshot.

    The default mode is safe for local/dev validation. ``deploy=True`` upgrades Django
    deployment warnings to blockers; ``strict_infra=True`` additionally requires broker
    and storage checks to succeed. Remote media is always enforced when the installation
    explicitly declares ``REQUIRE_REMOTE_MEDIA=True``.
    """

    django_issues = _django_checks(deploy=deploy)
    try:
        migrations = _pending_migrations()
    except Exception as exc:  # database unavailable or migration graph invalid
        migrations = [f"unavailable:{exc.__class__.__name__}"]

    services: dict[str, dict[str, Any]] = {
        "database": _database_check(),
        "cache": _cache_check(),
    }

    remote_media_required = bool(getattr(settings, "REQUIRE_REMOTE_MEDIA", False))
    if strict_infra:
        services["broker"] = _broker_check()
    if strict_infra or remote_media_required:
        services["storage"] = _storage_check(scan=False)

    blockers: list[str] = []
    if django_issues:
        blockers.append("django_checks")
    if migrations:
        blockers.append("pending_migrations")

    for name, payload in services.items():
        status = str(payload.get("status") or "error")
        if status == "error":
            blockers.append(f"service:{name}")
        elif strict_infra and status == "warning" and name == "broker":
            blockers.append("service:broker_warning")

    if remote_media_required:
        storage = services.get("storage") or {}
        if storage.get("backend") != "s3":
            blockers.append("remote_media_required")

    return {
        "status": "ok" if not blockers else "error",
        "deploy_checks": deploy,
        "strict_infra": strict_infra,
        "remote_media_required": remote_media_required,
        "django_issues": django_issues,
        "pending_migrations": migrations,
        "services": services,
        "blockers": blockers,
    }
