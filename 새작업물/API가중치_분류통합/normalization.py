"""Standalone Steam/IGDB feature normalizer. No HTTP, scoring, or UI side effects."""
import json
import math
import re
import unicodedata
from pathlib import Path

REGISTRY = json.loads(Path(__file__).with_name("vocabulary.json").read_text(encoding="utf-8"))
VERSION = REGISTRY["schema_version"]
GROUPS = {e["code"]: e["aliases"] for e in REGISTRY["entries"]}
ENTRIES = {e["code"]: e for e in REGISTRY["entries"]}

def key(value):
    return re.sub(r"[^\w+]", "", unicodedata.normalize("NFKC", str(value)).casefold()).replace("_", "")

ALIASES = {}
for code, aliases in GROUPS.items():
    for alias in aliases:
        token = key(alias)
        if token in ALIASES and ALIASES[token] != code:
            raise ValueError("Conflicting vocabulary alias: " + alias)
        ALIASES[token] = code

STEAM_GENRES = {
    1:"genre:action", 2:"genre:strategy", 3:"genre:rpg", 4:"tag:casual",
    9:"genre:racing", 18:"genre:sports", 23:"tag:indie", 25:"genre:adventure",
    28:"genre:simulation", 29:"category:mmo", 37:"tag:free_to_play",
    70:"tag:early_access",
}
STEAM_CATEGORIES = {
    1:"category:multiplayer", 2:"category:single_player", 9:"category:co_op",
    20:"category:mmo", 24:"category:split_screen", 36:"category:online_pvp",
    37:"category:shared_split_pvp", 38:"category:online_co_op",
    39:"category:shared_split_co_op", 49:"category:pvp",
}
TAXONOMIES = ("genres", "themes", "keywords", "game_modes", "player_perspectives")

def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None

def integer(value):
    try:
        return int(value) if not isinstance(value, bool) else None
    except (TypeError, ValueError):
        return None

def rows(value):
    return value if isinstance(value, list) else []

def record(value):
    return value if isinstance(value, dict) else {}

def resolve(source, value):
    """Preserve unknown IDs/labels; never invent a synonym or auto-score unknowns."""
    row = value if isinstance(value, dict) else {"name": value} if isinstance(value, str) else {"id": value}
    label = row.get("name") or row.get("description")
    ident = row.get("id")
    code = None
    if source == "steam.genres":
        code = STEAM_GENRES.get(integer(ident))
    elif source == "steam.categories":
        code = STEAM_CATEGORIES.get(integer(ident))
        # Categories include capabilities (Steam Cloud, achievements etc.), not all preference tags.
        if code is None:
            return {"source":source,"source_id":ident,"value":label,"code":None,
                    "status":"review_required","raw":value}
    if code is None and isinstance(label, str):
        code = ALIASES.get(key(label))
    return {"source":source,"source_id":ident,"value":label,"code":code,
            "status":"mapped" if code else "review_required","raw":value}

def parent_codes(codes):
    found = set()
    todo = list(codes)
    while todo:
        for parent in ENTRIES[todo.pop()]["parents"]:
            if parent not in found:
                found.add(parent)
                todo.append(parent)
    return sorted(found - set(codes))

def normalize(payload):
    steam = record(payload.get("steam"))
    igdb = record(payload.get("igdb"))
    game = record(igdb.get("game")) if igdb.get("status") == "ok" else {}
    resolved = []
    for field in ("genres", "categories"):
        resolved.extend(resolve("steam."+field, x) for x in rows(steam.get(field)))
    resolved.extend(resolve("steam.store_tags", x) for x in rows(record(payload.get("steam_tags")).get("values")))
    for field in TAXONOMIES:
        resolved.extend(resolve("igdb."+field, x) for x in rows(game.get(field)))
    evidence = {}
    unmapped = []
    for item in resolved:
        code = item["code"]
        if code is None:
            unmapped.append(item)
        elif item not in evidence.setdefault(code, []):
            evidence[code].append(item)
    codes = sorted(c for c in evidence if ENTRIES[c]["score_eligible"])
    platforms = set()
    platform_evidence = []
    for os_name, supported in record(steam.get("platforms")).items():
        if supported is True and os_name in ("windows","mac","linux"):
            platforms.add("pc")
            platform_evidence.append({"source":"steam.platforms","value":os_name,"group":"pc"})
    for value in rows(game.get("platforms")):
        row = record(value)
        name = str(row.get("name") or "").casefold()
        group = None
        if name in ("pc (microsoft windows)","pc","linux","mac","dos"):
            group = "pc"
        elif name in ("android","ios","windows phone"):
            group = "mobile"
        elif any(n in name for n in ("playstation","xbox","nintendo","wii","gamecube")):
            group = "console"
        if group:
            platforms.add(group)
        platform_evidence.append({"source":"igdb.platforms","value":value,"group":group})
    supported_platforms = platforms & {"pc","console"}
    price = record(steam.get("price_overview"))
    amount = number(price.get("final"))
    price_value = amount / 100 if amount is not None else 0 if steam.get("is_free") is True else None
    times = []
    for t in rows(igdb.get("time_to_beat_seconds")):
        t = record(t)
        times.append({**t, **{k:(number(t.get(k))/3600 if number(t.get(k)) is not None and number(t.get(k)) > 0 else None)
                             for k in ("hastily","normally","completely")}})
    reviews = record(payload.get("reviews"))
    summary = record(reviews.get("query_summary"))
    positive = number(summary.get("total_positive"))
    negative = number(summary.get("total_negative"))
    denominator = positive + negative if positive is not None and negative is not None and positive >= 0 and negative >= 0 else None
    return {
        "schema_version":VERSION,"appid":payload.get("appid"),
        "name":steam.get("name") or game.get("name"),
        "codes":codes,"evidence":evidence,"unmapped":unmapped,
        "parent_codes":parent_codes(codes),
        "metadata_codes":sorted(set(evidence)-set(codes)),
        "coverage":{"received":len(resolved),"mapped":sum(x["code"] is not None for x in resolved),
                    "review_required":len(unmapped),"exhaustive_catalog_verified":False},
        "platforms":sorted(supported_platforms),"excluded_platforms":sorted(platforms-supported_platforms),
        "platform_evidence":platform_evidence,
        "recommendable":bool(supported_platforms) and steam.get("type") == "game",
        "eligibility_reason":"pc_console_game" if supported_platforms and steam.get("type") == "game" else
                             "mobile_only" if platforms == {"mobile"} else "non_game_or_unknown_platform",
        "price":{"currency":price.get("currency"),"amount":price_value,"source":"steam","raw":price,
                 "is_free":steam.get("is_free"),"country":payload.get("country")},
        "requirements":steam.get("pc_requirements") or {},
        "requirements_by_os":{os:steam.get(os+"_requirements") for os in ("pc","mac","linux")},
        "completion_hours":times,"completion_seconds_raw":igdb.get("time_to_beat_seconds"),
        "session_minutes":None,"hardware_tier":None,
        "ratings":{"igdb_user":game.get("rating"),"igdb_user_count":game.get("rating_count"),
                   "igdb_total":game.get("total_rating"),"igdb_total_count":game.get("total_rating_count"),
                   "steam_reviews":summary,
                   "steam_positive_ratio":positive/denominator if denominator and denominator > 0 else None},
        "languages_raw":{"steam":steam.get("supported_languages"),"igdb":game.get("language_supports")},
        "age_ratings_raw":{"steam_required_age":steam.get("required_age"),"igdb":game.get("age_ratings")},
        "controller_support_raw":steam.get("controller_support"),
        "release_raw":{"steam":steam.get("release_date"),"igdb":game.get("first_release_date")},
        "source_status":{"steam":"ok" if steam else "missing","igdb":igdb.get("status","missing"),
                         "steam_tags":record(payload.get("steam_tags")).get("status","missing")},
        "unknown_fields":["session_minutes","hardware_tier","motion_intensity","monetization_pressure","complexity"],
    }
