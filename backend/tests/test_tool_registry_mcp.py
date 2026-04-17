import asyncio

from xoai.agents.tool_registry import ToolRegistry, inject_mcp_tools


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def __aiter__(self):
        async def iterate():
            for doc in self.docs:
                yield doc

        return iterate()


class FakeMcpServers:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query):
        return FakeCursor(self.docs)


class FakeDb:
    def __init__(self, docs):
        self.mcp_servers = FakeMcpServers(docs)


def test_inject_mcp_tools_filters_roles(monkeypatch):
    docs = [
        {
            "name": "admin-only",
            "user_id": None,
            "enabled": True,
            "allowed_roles": ["admin"],
            "tools_cache": [{"name": "inspect", "description": "Inspect"}],
        },
        {
            "name": "user-safe",
            "user_id": None,
            "enabled": True,
            "allowed_roles": ["user"],
            "tools_cache": [{"name": "lookup", "description": "Lookup"}],
        },
    ]
    import xoai.db.mongo
    monkeypatch.setattr(xoai.db.mongo, "get_db", lambda: FakeDb(docs))

    registry = ToolRegistry()
    asyncio.run(inject_mcp_tools(registry, user_id="u1", role="admin"))

    names = registry.metadata.keys()
    assert any("admin_only" in name for name in names)
    assert not any("user_safe" in name for name in names)
