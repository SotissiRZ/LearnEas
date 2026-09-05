from __future__ import annotations

import os
from django.conf import settings
from django.core.management.base import CommandError


def postgres_connection_env():
    db = settings.DATABASES["default"]
    engine = str(db.get("ENGINE") or "")
    if "postgresql" not in engine:
        raise CommandError("Cette commande nécessite PostgreSQL.")
    env = os.environ.copy()
    password = str(db.get("PASSWORD") or "")
    if password:
        env["PGPASSWORD"] = password
    args = []
    if db.get("HOST"):
        args += ["--host", str(db["HOST"])]
    if db.get("PORT"):
        args += ["--port", str(db["PORT"])]
    if db.get("USER"):
        args += ["--username", str(db["USER"])]
    args += ["--dbname", str(db["NAME"])]
    return env, args
