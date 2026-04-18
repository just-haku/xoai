import asyncio
import pytest

from xoai.auth import service as auth_service


class InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        stored = dict(doc)
        stored["_id"] = len(self.docs) + 1
        self.docs.append(stored)
        return InsertResult(stored["_id"])

    async def find_one(self, query):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                return doc
        return None

    async def update_one(self, query, update, upsert=False):
        doc = await self.find_one(query)
        if not doc and upsert:
            doc = dict(query)
            doc["_id"] = len(self.docs) + 1
            self.docs.append(doc)
        if not doc:
            return
        for key, value in update.get("$set", {}).items():
            doc[key] = value

    async def update_many(self, query, update):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                for set_key, set_value in update.get("$set", {}).items():
                    doc[set_key] = set_value

    async def delete_one(self, query):
        for index, doc in enumerate(self.docs):
            if all(doc.get(key) == value for key, value in query.items()):
                self.docs.pop(index)
                return


class FakeDb:
    def __init__(self):
        self.refresh_sessions = FakeCollection()
        self.verification_codes = FakeCollection()
        self.password_reset_tokens = FakeCollection()
        self.proxy_handoffs = FakeCollection()


def test_refresh_session_rotates_and_revokes(monkeypatch):
    fake_db = FakeDb()
    import xoai.db.mongo

    monkeypatch.setattr(xoai.db.mongo, "get_db", lambda: fake_db)

    async def scenario():
        session_id, refresh_token = await auth_service.create_refresh_session("user-1", ip="127.0.0.1", user_agent="pytest")
        rotated = await auth_service.rotate_refresh_session(refresh_token, ip="127.0.0.2", user_agent="pytest-rotated")
        assert rotated["session_id"] == session_id
        assert rotated["refresh_token"] != refresh_token
        stored = fake_db.refresh_sessions.docs[0]
        assert stored["ip"] == "127.0.0.2"
        assert stored["token_hash"] == auth_service.hash_token_value(rotated["refresh_token"])

        await auth_service.revoke_refresh_session(session_id)
        assert stored["revoked_at"] is not None

    asyncio.run(scenario())


def test_verification_codes_are_hashed_and_consumed(monkeypatch):
    fake_db = FakeDb()
    import xoai.db.mongo

    monkeypatch.setattr(xoai.db.mongo, "get_db", lambda: fake_db)

    async def scenario():
        await auth_service.store_verification_code(
            user_id="user-1",
            code_type="email_change",
            target="user@example.com",
            code="123456",
        )
        stored = fake_db.verification_codes.docs[0]
        assert stored["code_hash"] != "123456"

        await auth_service.consume_verification_code(
            user_id="user-1",
            code_type="email_change",
            target="user@example.com",
            code="123456",
        )
        assert fake_db.verification_codes.docs == []

    asyncio.run(scenario())


def test_proxy_handoff_is_single_use_and_preserves_proxy_claim(monkeypatch):
    fake_db = FakeDb()
    import xoai.db.mongo

    monkeypatch.setattr(xoai.db.mongo, "get_db", lambda: fake_db)

    async def scenario():
        handoff = await auth_service.create_proxy_handoff("user-1", "user", "admin-1")
        consumed = await auth_service.consume_proxy_handoff(handoff["handoff_token"])
        assert consumed["proxy_by"] == "admin-1"
        assert consumed["session_id"] == handoff["session_id"]

        token = auth_service.create_access_token(
            "user-1",
            "user",
            consumed["session_id"],
            expires_minutes=auth_service.PROXY_ACCESS_TOKEN_EXPIRE_MINUTES,
            extra_claims={"proxy_by": consumed["proxy_by"]},
        )
        payload = auth_service.decode_token(token, expected_type="access")
        assert payload["proxy_by"] == "admin-1"

        with pytest.raises(auth_service.AuthError):
            await auth_service.consume_proxy_handoff(handoff["handoff_token"])

    asyncio.run(scenario())
