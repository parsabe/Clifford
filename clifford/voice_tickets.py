"""Short-lived, single-use tickets for the Laravel voice bridge; never general API access."""

import hashlib
import secrets
import time

from fastapi import HTTPException


class VoiceTickets:
    def __init__(self, clock=time.monotonic, ttl=30, limit=128):
        self.clock, self.ttl, self.limit = clock, ttl, limit
        self.pending = {}

    def issue(self, owner):
        now = self.clock()
        self.pending = {key: value for key, value in self.pending.items() if value[1] > now}
        if len(self.pending) >= self.limit:
            raise HTTPException(429, detail={"code": "voice_ticket_limit"})
        ticket = secrets.token_urlsafe(32)
        self.pending[hashlib.sha256(ticket.encode()).digest()] = (owner, now + self.ttl)
        return {"ticket": ticket, "expires_in": self.ttl}

    def consume(self, ticket):
        if not isinstance(ticket, str) or len(ticket) > 128:
            raise HTTPException(401, detail={"code": "invalid_voice_ticket"})
        value = self.pending.pop(hashlib.sha256(ticket.encode()).digest(), None)
        if value is None or value[1] <= self.clock():
            raise HTTPException(401, detail={"code": "invalid_voice_ticket"})
        return value[0]
