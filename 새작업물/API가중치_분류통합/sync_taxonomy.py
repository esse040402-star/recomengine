"""Run in an authorized backend with the existing igdb(endpoint, query) callable.
No credentials are read, written, returned, or embedded by this module.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from normalization import resolve

ENDPOINTS = ("genres","themes","game_modes","player_perspectives","keywords","platforms")

def sync_igdb(fetch, output, max_pages=10000):
    destination = Path(output)
    if destination.exists():
        raise FileExistsError("Choose a new snapshot file; existing data is preserved.")
    result = {"fetched_at":datetime.now(timezone.utc).isoformat(),"complete":False,"sources":{}}
    for endpoint in ENDPOINTS:
        time.sleep(0.3)
        before = fetch(endpoint+"/count", "")
        expected = before.get("count") if isinstance(before, dict) else None
        collected = {}
        cursor = 0
        exhausted = False
        for _ in range(max_pages):
            time.sleep(0.3)
            batch = fetch(endpoint, f"fields id,name,slug; where id > {cursor}; sort id asc; limit 500;")
            if not isinstance(batch, list):
                raise ValueError("Invalid taxonomy response: "+endpoint)
            if not batch:
                exhausted = True
                break
            for row in batch:
                if not isinstance(row, dict) or not isinstance(row.get("id"), int) or not isinstance(row.get("name"), str):
                    raise ValueError("Missing taxonomy identity: "+endpoint)
                collected[row["id"]] = row
            next_cursor = max(row["id"] for row in batch)
            if next_cursor <= cursor:
                raise ValueError("Taxonomy pagination stalled: "+endpoint)
            cursor = next_cursor
        time.sleep(0.3)
        after = fetch(endpoint+"/count", "")
        actual_count = after.get("count") if isinstance(after, dict) else None
        items = [resolve("igdb."+endpoint, row) for _,row in sorted(collected.items())]
        result["sources"][endpoint] = {
            "expected_before":expected,"expected_after":actual_count,"received":len(items),
            "retrieval_complete":exhausted and expected == actual_count == len(items),
            "semantic_complete":all(x["status"] == "mapped" for x in items),
            "items":items,
        }
    result["complete"] = all(v["retrieval_complete"] for v in result["sources"].values())
    result["semantic_complete"] = all(v["semantic_complete"] for k,v in result["sources"].items() if k != "platforms")
    # Exclusive creation: no overwriting team data. A failed fetch never writes a partial success snapshot.
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    return result
