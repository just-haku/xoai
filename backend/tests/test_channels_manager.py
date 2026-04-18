import asyncio

from xoai.channels import manager


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def __aiter__(self):
        async def iterate():
            for doc in self.docs:
                yield doc

        return iterate()


class FakeBotCollection:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query):
        return FakeCursor(self.docs)


class FakeDb:
    def __init__(self, docs):
        self.bot_instances = FakeBotCollection(docs)


def test_load_all_tenant_bots_uses_decrypt_value(monkeypatch):
    fake_db = FakeDb([{"_id": 1, "user_id": "u1", "platform": "telegram", "token_encrypted": "cipher", "status": "active"}])
    calls = []
    import xoai.db.mongo

    monkeypatch.setattr(xoai.db.mongo, "db", fake_db)
    monkeypatch.setattr(manager, "decrypt_value", lambda encrypted: "plain-token")

    async def fake_restart(user_id, platform, token):
        calls.append((user_id, platform, token))

    monkeypatch.setattr(manager, "restart_bot_instance", fake_restart)

    asyncio.run(manager.load_all_tenant_bots())

    assert calls == [("u1", "telegram", "plain-token")]

