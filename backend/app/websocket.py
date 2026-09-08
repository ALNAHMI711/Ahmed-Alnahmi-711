"""Authenticated, authorized WebSocket event hub.

Connections are bound to a database session; each command and each publication
revalidates that session, so logout/expiry closes the socket before data leaks.
"""
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from fastapi import HTTPException, WebSocket

from backend.app.security.auth import current_user

EVENT_TYPES = frozenset({"order", "trade", "position", "risk", "execution", "strategy", "signal", "bot_status", "notification", "errors"})
Handler = Callable[[dict, "Connection"], Awaitable[dict]]


@dataclass(eq=False)
class Connection:
    socket: WebSocket
    session: str
    user: object
    subscriptions: set[str] = field(default_factory=set)


class WebSocketDispatcher:
    def __init__(self):
        self._connections: set[Connection] = set()
        self._handlers: dict[str, Handler] = {"subscribe": self._subscribe, "unsubscribe": self._unsubscribe, "ping": self._ping}

    def _session_user(self, session: str):
        return current_user(session=session)

    async def connect(self, socket: WebSocket) -> Connection | None:
        session = socket.cookies.get("session")
        if session is None:
            await socket.close(code=1008, reason="authentication required")
            return None
        try:
            user = self._session_user(session)
        except HTTPException:
            await socket.close(code=1008, reason="authentication required")
            return None
        await socket.accept()
        connection = Connection(socket, session, user)
        self._connections.add(connection)
        return connection

    async def dispatch(self, message: object, connection: Connection) -> dict | None:
        """Reauthorize commands; a revoked/expired session is disconnected."""
        try:
            connection.user = self._session_user(connection.session)
        except HTTPException:
            await self.disconnect(connection, 1008, "session expired or revoked")
            return None
        if not isinstance(message, dict) or not isinstance(message.get("action"), str):
            return {"type": "errors", "code": "invalid_message"}
        handler = self._handlers.get(message["action"])
        return await handler(message, connection) if handler else {"type": "errors", "code": "unsupported_action"}

    async def publish(self, event_type: str, payload: dict, *, user_id: str | None = None) -> None:
        """Fan out an already-committed DB/execution event to authorized clients."""
        if event_type not in EVENT_TYPES:
            raise ValueError("unsupported event type")
        message = {"type": event_type, "payload": payload}
        for connection in tuple(self._connections):
            try:
                user = self._session_user(connection.session)
            except HTTPException:
                await self.disconnect(connection, 1008, "session expired or revoked")
                continue
            connection.user = user
            if event_type not in connection.subscriptions:
                continue
            if user.role != "admin" and (user_id is None or user.id != user_id):
                continue
            await connection.socket.send_json(message)

    async def disconnect(self, connection: Connection, code: int = 1000, reason: str = "") -> None:
        self._connections.discard(connection)
        await connection.socket.close(code=code, reason=reason)

    async def _ping(self, _: dict, __: Connection) -> dict:
        return {"type": "pong"}

    async def _subscribe(self, message: dict, connection: Connection) -> dict:
        topics = message.get("topics", [message.get("topic")])
        if not isinstance(topics, list) or not topics or any(topic not in EVENT_TYPES for topic in topics):
            return {"type": "errors", "code": "invalid_subscription"}
        connection.subscriptions.update(topics)
        return {"type": "subscribed", "topics": sorted(topics)}

    async def _unsubscribe(self, message: dict, connection: Connection) -> dict:
        topics = message.get("topics", [message.get("topic")])
        if not isinstance(topics, list) or not topics or any(topic not in EVENT_TYPES for topic in topics):
            return {"type": "errors", "code": "invalid_subscription"}
        connection.subscriptions.difference_update(topics)
        return {"type": "unsubscribed", "topics": sorted(topics)}
