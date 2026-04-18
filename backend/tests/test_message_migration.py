import asyncio
from datetime import datetime, timezone

from xoai.agents.memory import migrate_embedded_conversation_messages


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs
        self._limit = len(docs)

    def limit(self, value):
        self._limit = value
        return self

    async def to_list(self, length):
        return self.docs[: min(length, self._limit)]


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []

    def find(self, query):
        return FakeCursor(self.docs)

    async def count_documents(self, query):
        return len([doc for doc in self.docs if all(doc.get(key) == value for key, value in query.items())])

    async def insert_many(self, docs):
        self.docs.extend(docs)

    async def update_one(self, query, update):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                for key, value in update.get("$set", {}).items():
                    doc[key] = value
                for key in update.get("$unset", {}):
                    doc.pop(key, None)
                return


class FakeDb:
    def __init__(self):
        self.conversations = FakeCollection(
            [
                {
                    "_id": 1,
                    "chat_id": "chat-1",
                    "messages": [
                        {
                            "role": "assistant",
                            "content": "hello",
                            "created_at": datetime.now(timezone.utc),
                        }
                    ],
                }
            ]
        )
        self.messages = FakeCollection([])


def test_migrate_embedded_messages_backfills_canonical_messages(monkeypatch):
    fake_db = FakeDb()
    import xoai.db.mongo

    monkeypatch.setattr(xoai.db.mongo, "get_db", lambda: fake_db)

    migrated = asyncio.run(migrate_embedded_conversation_messages())

    assert migrated == 1
    assert fake_db.messages.docs[0]["conversation_id"] == "chat-1"
    assert "messages" not in fake_db.conversations.docs[0]
    assert fake_db.conversations.docs[0]["embedded_messages_migrated_at"] is not None

