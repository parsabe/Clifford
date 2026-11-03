import pytest
from fastapi import HTTPException

from clifford.voice_tickets import VoiceTickets


def test_ticket_owner_expiry_replay_and_bound():
    clock = [100]
    tickets = VoiceTickets(clock=lambda: clock[0], limit=1)
    ticket = tickets.issue("owner")["ticket"]
    with pytest.raises(HTTPException) as limit:
        tickets.issue("owner")
    assert limit.value.status_code == 429
    assert tickets.consume(ticket) == "owner"
    with pytest.raises(HTTPException):
        tickets.consume(ticket)
    expired = tickets.issue("owner")["ticket"]
    clock[0] += 31
    with pytest.raises(HTTPException):
        tickets.consume(expired)


def test_ticket_only_authorizes_voice_and_is_consumed(client):
    ticket = client.post("/v1/voice/tickets").json()["ticket"]
    assert client.get("/v1/tools", headers={"Authorization": "Bearer " + ticket}).status_code == 401
    with client.websocket_connect("/v1/voice/listen") as ws:
        ws.send_json({"ticket": ticket})
        assert ws.receive_json()["payload"]["code"] == "speech_model_not_installed"
    with client.websocket_connect("/v1/voice/listen") as ws:
        ws.send_json({"ticket": ticket})
        assert ws.receive_json()["payload"]["code"] == "voice_authentication_or_protocol_error"
