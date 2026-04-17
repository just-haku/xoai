import asyncio

import pytest
from bson import ObjectId

from xoai.agents import evolution
from xoai.agents import prompt_bench


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs
        self._limit = len(docs)

    def sort(self, *args, **kwargs):
        return self

    def limit(self, value):
        self._limit = value
        return self

    async def to_list(self, length):
        return self.docs[: min(self._limit, length)]


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []
        self.inserted = []

    async def find_one(self, query, sort=None):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                return doc
        return None

    def find(self, query):
        matched = []
        for doc in self.docs:
            include = True
            for key, value in query.items():
                if isinstance(value, dict) and "$in" in value:
                    include = doc.get(key) in value["$in"]
                else:
                    include = doc.get(key) == value
                if not include:
                    break
            if include:
                matched.append(doc)
        return FakeCursor(matched)

    async def update_one(self, query, update):
        doc = await self.find_one(query)
        if not doc:
            return
        for key, value in update.get("$set", {}).items():
            doc[key] = value

    async def insert_one(self, doc):
        stored = dict(doc)
        stored["_id"] = ObjectId()
        self.docs.append(stored)
        self.inserted.append(stored)
        return type("InsertResult", (), {"inserted_id": stored["_id"]})()


class FakeDb:
    def __init__(self, candidate, query_runs=None):
        self.prompt_variants = FakeCollection([candidate])
        self.prompt_versions = FakeCollection()
        self.prompt_promotions = FakeCollection()
        self.prompt_bench_runs = FakeCollection()
        self.query_runs = FakeCollection(query_runs or [])


def test_prompt_promotion_requires_benchmark(monkeypatch):
    candidate_id = ObjectId()
    fake_db = FakeDb(
        {
            "_id": candidate_id,
            "role": "executor",
            "profile_key": "admin.execution",
            "mutation_reason": "Fix retries",
            "latest_benchmark_score": 0.3,
        }
    )
    monkeypatch.setattr(evolution, "get_db", lambda: fake_db)

    with pytest.raises(ValueError, match="cannot be promoted before benchmark passes"):
        asyncio.run(evolution.set_prompt_candidate_status(str(candidate_id), "promoted"))


def test_prompt_promotion_creates_active_version(monkeypatch):
    candidate_id = ObjectId()
    fake_db = FakeDb(
        {
            "_id": candidate_id,
            "role": "executor",
            "profile_key": "admin.execution",
            "mutation_reason": "Fix retries",
            "latest_benchmark_score": 0.8,
            "recommended_model": "gemini-1.5-pro",
            "evaluation_score": 0.7,
            "proposed_prompt_content": "new prompt",
            "current_prompt_content": "old prompt",
        }
    )
    monkeypatch.setattr(evolution, "get_db", lambda: fake_db)

    result = asyncio.run(evolution.set_prompt_candidate_status(str(candidate_id), "promoted"))
    assert result["status"] == "promoted"
    assert fake_db.prompt_versions.inserted[0]["status"] == "active"
    assert fake_db.prompt_promotions.inserted[0]["benchmark_score"] == 0.8
    assert fake_db.prompt_promotions.inserted[0]["recommended_model"] == "gemini-1.5-pro"


def test_prompt_candidate_benchmark_records_model_matrix(monkeypatch):
    candidate_id = ObjectId()
    candidate = {
        "_id": candidate_id,
        "role": "executor",
        "prompt_name": "executor",
        "profile_key": "admin.execution",
        "source_run_id": "run-1",
        "mutation_reason": "Fix retries",
        "promotion_status": "candidate",
    }
    fake_db = FakeDb(
        candidate,
        query_runs=[
            {
                "query_id": "run-1",
                "intent_profile": "admin.execution",
                "user_role": "admin",
                "quality_score": 0.55,
                "node_runs": [{"node_id": "execute"}],
                "failure_modes": [],
                "final_output": "completed",
                "status": "completed",
                "topology_type": "execute_then_verify_then_retry",
            }
        ],
    )

    async def fake_fetch_models(role):
        return ["gemini-1.5-flash", "gemini-1.5-pro"]

    monkeypatch.setattr(evolution, "get_db", lambda: fake_db)
    monkeypatch.setattr(prompt_bench, "get_db", lambda: fake_db)
    monkeypatch.setattr(prompt_bench, "fetch_available_benchmark_models", fake_fetch_models)

    result = asyncio.run(evolution.run_prompt_candidate_benchmark(str(candidate_id)))

    assert result["recommended_model"] == "gemini-1.5-pro"
    assert len(result["model_benchmark_results"]) == 2
    assert result["aggregate_score"] == result["utility_score"]
    assert fake_db.prompt_bench_runs.inserted[0]["recommended_model"] == "gemini-1.5-pro"
    assert fake_db.prompt_variants.docs[0]["recommended_model"] == "gemini-1.5-pro"
    assert fake_db.prompt_variants.docs[0]["latest_model_benchmark_results"] == result["model_benchmark_results"]
