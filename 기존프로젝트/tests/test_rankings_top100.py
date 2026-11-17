"""Steam 공식 동시 접속 랭킹 TOP 100: 네트워크 없는 단계별 테스트."""
import asyncio
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

os.environ["USE_MOCK_DB"] = "true"

from app.main import app
from app.services import market, steam


def sample_ranks(size=100):
    return [
        {"rank": i, "appid": 10000 + i, "concurrent_in_game": 200000 - i, "peak_in_game": 300000 - i}
        for i in range(1, size + 1)
    ]


@pytest.fixture(autouse=True)
def reset_cache():
    market.clear_cache()
    yield
    market.clear_cache()


def test_fetch_concurrent_top_uses_actual_steam_fields(monkeypatch):
    called = []

    async def fake_json(url, params, timeout=15):
        called.append((url, params, timeout))
        return {"response": {"last_update": 1790000000, "ranks": sample_ranks()}}

    monkeypatch.setattr(steam, "_get_json", fake_json)
    monkeypatch.setattr(steam, "get_settings", lambda: SimpleNamespace(steam_api_key="TEST_ONLY"))
    rows = asyncio.run(steam.fetch_concurrent_top(100))
    assert len(rows) == 100
    assert [x["rank"] for x in rows] == list(range(1, 101))
    assert rows[0] == {"rank": 1, "app": 10001, "players": 199999, "peakPlayers": 299999}
    assert called == [
        ("https://api.steampowered.com/ISteamChartsService/GetGamesByConcurrentPlayers/v1/",
         {"key": "TEST_ONLY"}, 20)
    ]


def test_missing_counts_are_not_invented(monkeypatch):
    async def fake_json(url, params, timeout=15):
        return {"response": {"ranks": [{"rank": 3, "appid": 123}]}}
    monkeypatch.setattr(steam, "_get_json", fake_json)
    monkeypatch.setattr(steam, "get_settings", lambda: SimpleNamespace(steam_api_key=""))
    assert asyncio.run(steam.fetch_concurrent_top()) == [
        {"rank": 3, "app": 123, "players": None, "peakPlayers": None}
    ]


@pytest.mark.parametrize("payload", [
    {},
    {"response": {"ranks": []}},
    {"response": {"ranks": "invalid"}},
    {"response": {"ranks": [{"rank": 1, "appid": 0}]}},
    {"response": {"ranks": [{"rank": True, "appid": 730}]}},
    {"response": {"ranks": [{"rank": 1, "appid": 730}, {"rank": 2, "appid": 730}]}},
])
def test_invalid_steam_response_fails_instead_of_faking_rankings(monkeypatch, payload):
    async def fake_json(url, params, timeout=15):
        return payload
    monkeypatch.setattr(steam, "_get_json", fake_json)
    monkeypatch.setattr(steam, "get_settings", lambda: SimpleNamespace(steam_api_key=""))
    with pytest.raises(ValueError):
        asyncio.run(steam.fetch_concurrent_top())


def test_top100_endpoint_keeps_rank_and_uses_cache(monkeypatch):
    seen = []

    async def fake_top(limit):
        seen.append(limit)
        return [{"rank": x["rank"], "app": x["appid"], "players": x["concurrent_in_game"],
                 "peakPlayers": x["peak_in_game"]} for x in sample_ranks()]

    monkeypatch.setattr(steam, "fetch_concurrent_top", fake_top)
    with TestClient(app) as client:
        first = client.get("/api/rankings/steam")
        second = client.get("/api/rankings/steam")
    assert first.status_code == second.status_code == 200
    body = first.json()
    assert body["section"] == "rankings"
    assert body["source"] == "steam_concurrent_players"
    assert body["count"] == 100 and body["complete"] is True
    assert len(body["data"]) == 100
    assert body["data"][0]["rank"] == 1 and body["data"][-1]["rank"] == 100
    assert first.json() == second.json()
    assert seen == [100]


def test_short_upstream_list_is_marked_incomplete(monkeypatch):
    async def fake_top(limit):
        return [{"rank": 1, "app": 730, "players": 500, "peakPlayers": 900}]
    monkeypatch.setattr(steam, "fetch_concurrent_top", fake_top)
    with TestClient(app) as client:
        r = client.get("/api/rankings/steam")
    assert r.status_code == 200
    assert r.json()["count"] == 1
    assert r.json()["complete"] is False
    assert r.json()["data"][0]["app"] == 730


def test_upstream_error_is_502_and_does_not_poison_cache(monkeypatch):
    seen = []

    async def fake_top(limit):
        seen.append(limit)
        if len(seen) == 1:
            raise ValueError("잘못된 랭킹 응답")
        return [{"rank": 1, "app": 730, "players": 100, "peakPlayers": 200}]

    monkeypatch.setattr(steam, "fetch_concurrent_top", fake_top)
    with TestClient(app) as client:
        failed = client.get("/api/rankings/steam")
        succeeded = client.get("/api/rankings/steam")
    assert failed.status_code == 502
    assert succeeded.status_code == 200
    assert len(seen) == 2
