from __future__ import annotations

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.core import signing

from .models import FormationEnrollment, FormationSession, FormationSessionInvite
from .realtime import load_realtime_ticket, session_group, user_group

User = get_user_model()


@database_sync_to_async
def _authorized_identity(ticket: str, session_id: int):
    try:
        payload = load_realtime_ticket(ticket)
    except (signing.BadSignature, signing.SignatureExpired, TypeError, ValueError):
        return None

    try:
        ticket_session_id = int(payload.get("session_id"))
        user_id = int(payload.get("user_id"))
    except (TypeError, ValueError):
        return None
    if ticket_session_id != int(session_id):
        return None

    try:
        session = FormationSession.objects.select_related(
            "formation__instructor", "formation__co_instructor"
        ).get(pk=session_id)
        user = User.objects.get(pk=user_id, is_active=True)
    except (FormationSession.DoesNotExist, User.DoesNotExist):
        return None

    if session.completed or session.ended_at:
        return None

    formation = session.formation
    organizer = bool(
        user.role == "admin"
        or formation.instructor_id == user.id
        or formation.co_instructor_id == user.id
    )
    enrolled = FormationEnrollment.objects.filter(user=user, formation=formation).exists()
    invited = bool(
        user.email
        and FormationSessionInvite.objects.filter(
            session=session,
            email__iexact=user.email,
            revoked_at__isnull=True,
        ).exists()
    )
    if not (organizer or enrolled or invited):
        return None
    return {"user_id": user.id, "session_id": session.id}


class FormationRealtimeConsumer(AsyncJsonWebsocketConsumer):
    """Canal temps réel léger.

    Les écritures métier restent validées par l'API DRF. Le WebSocket pousse les signaux
    WebRTC/collaboratifs, les changements de présence et les changements de fichiers afin de
    supprimer le polling HTTP permanent.
    """

    async def connect(self):
        self.session_id = int(self.scope["url_route"]["kwargs"]["session_id"])
        params = parse_qs(self.scope.get("query_string", b"").decode("utf-8", errors="ignore"))
        ticket = (params.get("ticket") or [""])[0]
        identity = await _authorized_identity(ticket, self.session_id)
        if not identity:
            await self.close(code=4401)
            return

        self.user_id = int(identity["user_id"])
        self.session_group_name = session_group(self.session_id)
        self.user_group_name = user_group(self.session_id, self.user_id)
        await self.channel_layer.group_add(self.session_group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "ready"})
        await self.send_json({"type": "presence_changed"})
        await self.send_json({"type": "files_changed"})

    async def disconnect(self, close_code):
        if getattr(self, "session_group_name", None):
            await self.channel_layer.group_discard(self.session_group_name, self.channel_name)
        if getattr(self, "user_group_name", None):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Les payloads métier ne sont jamais acceptés directement ici. Un ping applicatif
        # permet uniquement de garder le canal observable sans contourner les validations DRF.
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def signal_message(self, event):
        await self.send_json({"type": "signal", "message": event["message"]})

    async def presence_changed(self, event):
        await self.send_json({"type": "presence_changed"})

    async def files_changed(self, event):
        await self.send_json({"type": "files_changed"})

    async def session_state(self, event):
        await self.send_json({"type": "session_state", "state": event.get("state", "updated")})
