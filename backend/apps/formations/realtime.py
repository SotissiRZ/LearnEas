from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core import signing

TICKET_SALT = "learneas.formations.realtime"


def session_group(session_id: int) -> str:
    return f"live.session.{int(session_id)}"


def user_group(session_id: int, user_id: int) -> str:
    return f"live.session.{int(session_id)}.user.{int(user_id)}"


def make_realtime_ticket(*, session_id: int, user_id: int) -> str:
    return signing.dumps(
        {"session_id": int(session_id), "user_id": int(user_id)},
        salt=TICKET_SALT,
        compress=True,
    )


def load_realtime_ticket(ticket: str) -> dict:
    return signing.loads(
        ticket,
        salt=TICKET_SALT,
        max_age=settings.REALTIME_TICKET_MAX_AGE_SECONDS,
    )


def serialize_signal(signal) -> dict:
    sender = signal.sender
    return {
        "id": signal.id,
        "sender_id": signal.sender_id,
        "sender_name": sender.get_full_name() or sender.username,
        "kind": signal.kind,
        "payload": signal.payload,
    }


def _group_send(group: str, event: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(group, event)
    except Exception:
        # Le temps réel est une accélération, jamais une dépendance transactionnelle :
        # l'API/DB restent la source de vérité et le frontend bascule sur le fallback HTTP.
        return


def publish_signal(signal) -> None:
    _group_send(
        user_group(signal.session_id, signal.recipient_id),
        {"type": "signal.message", "message": serialize_signal(signal)},
    )


def publish_presence_changed(session_id: int) -> None:
    _group_send(
        session_group(session_id),
        {"type": "presence.changed"},
    )


def publish_files_changed(session_id: int) -> None:
    _group_send(
        session_group(session_id),
        {"type": "files.changed"},
    )


def publish_session_state(session_id: int, state: str) -> None:
    _group_send(
        session_group(session_id),
        {"type": "session.state", "state": str(state)},
    )
