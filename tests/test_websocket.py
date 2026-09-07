"""Unit coverage for WebSocket authentication, allow-list and revocation behavior."""
import asyncio
from types import SimpleNamespace
from backend.app.websocket import WebSocketDispatcher
from fastapi import HTTPException
class Socket:
    def __init__(self, session='token'): self.cookies={'session':session}; self.closed=[]; self.sent=[]
    async def accept(self): pass
    async def close(self, **kwargs): self.closed.append(kwargs)
    async def send_json(self, item): self.sent.append(item)
def test_rejects_unauthenticated_connection():
    hub=WebSocketDispatcher(); hub._session_user=lambda _: (_ for _ in ()).throw(HTTPException(401))
    socket=Socket(); assert asyncio.run(hub.connect(socket)) is None; assert socket.closed[0]['code']==1008
def test_subscribe_allow_list_and_dispatch():
    hub=WebSocketDispatcher(); hub._session_user=lambda _: SimpleNamespace(id='u1',role='viewer')
    connection=asyncio.run(hub.connect(Socket())); assert asyncio.run(hub.dispatch({'action':'subscribe','topics':['trade','position']},connection))['type']=='subscribed'
    assert asyncio.run(hub.dispatch({'action':'subscribe','topic':'not-an-event'},connection))['code']=='invalid_subscription'
    asyncio.run(hub.publish('trade',{'id':'t'},user_id='u1')); assert connection.socket.sent == [{'type':'trade','payload':{'id':'t'}}]
def test_revoked_session_closes_before_dispatch_or_publish():
    hub=WebSocketDispatcher(); state={'ok':True}
    def user(_):
        if not state['ok']: raise HTTPException(401)
        return SimpleNamespace(id='u1',role='viewer')
    hub._session_user=user; connection=asyncio.run(hub.connect(Socket())); state['ok']=False
    assert asyncio.run(hub.dispatch({'action':'ping'},connection)) is None
    assert connection.socket.closed[0]['code']==1008

def test_non_admin_cannot_receive_unowned_account_event():
 hub=WebSocketDispatcher(); hub._session_user=lambda _: SimpleNamespace(id='u1',role='viewer')
 connection=asyncio.run(hub.connect(Socket())); asyncio.run(hub.dispatch({'action':'subscribe','topic':'trade'},connection))
 asyncio.run(hub.publish('trade',{'account_id':'account'})); assert connection.socket.sent == []
