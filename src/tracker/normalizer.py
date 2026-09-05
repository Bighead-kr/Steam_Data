from __future__ import annotations

import datetime as dt
import re

_OWNERS_RE = re.compile(r"([\d,]+)\s*\.\.\s*([\d,]+)")


def _parse_owners(owners: str | None) -> tuple[int | None, int | None]:
    if not owners:
        return None, None
    match = _OWNERS_RE.search(owners)
    if not match:
        return None, None
    low, high = match.groups()
    return int(low.replace(",", "")), int(high.replace(",", ""))


def _parse_release_date(appdetails: dict) -> dt.date | None:
    release = appdetails.get("release_date") or {}
    if release.get("coming_soon"):
        return None
    raw_date = release.get("date")
    if not raw_date:
        return None
    try:
        return dt.datetime.strptime(raw_date, "%d %b, %Y").date()
    except ValueError:
        return None


def _genres(appdetails: dict, steamspy: dict) -> list[str]:
    appdetails_genres = [g["description"] for g in appdetails.get("genres", [])]
    if appdetails_genres:
        return appdetails_genres
    genre_str = steamspy.get("genre") or ""
    return [g.strip() for g in genre_str.split(",") if g.strip()]


def _tags(steamspy: dict) -> list[str]:
    tags = steamspy.get("tags") or {}
    return [tag for tag, _count in sorted(tags.items(), key=lambda kv: kv[1], reverse=True)]


def normalize_game(app_id: int, raw: dict) -> dict | None:
    """Turn a merged appdetails+steamspy raw record into a `games` row dict.

    Returns None when the game has no parseable release date (skipped —
    counted as a data-quality issue by the pipeline caller).
    """
    appdetails = raw.get("appdetails", {})
    steamspy = raw.get("steamspy", {})

    release_date = _parse_release_date(appdetails)
    if release_date is None:
        return None

    is_free = appdetails.get("is_free", False)
    price_cents = 0 if is_free else appdetails.get("price_overview", {}).get("final")

    positive = steamspy.get("positive")
    negative = steamspy.get("negative")
    review_count = None
    review_score_pct = None
    if positive is not None and negative is not None:
        review_count = positive + negative
        if review_count > 0:
            review_score_pct = positive / review_count * 100

    owners_low, owners_high = _parse_owners(steamspy.get("owners"))
    genres = _genres(appdetails, steamspy)

    return {
        "app_id": app_id,
        "name": appdetails.get("name") or steamspy.get("name") or f"Unknown ({app_id})",
        "genres": genres,
        "tags": _tags(steamspy),
        "release_date": release_date,
        "price_cents": price_cents,
        "is_dlc": appdetails.get("type") == "dlc",
        "review_score_pct": review_score_pct,
        "review_count": review_count,
        "owners_low": owners_low,
        "owners_high": owners_high,
        "avg_playtime_min": steamspy.get("average_forever"),
        "cohort_genre": genres[0].lower() if genres else "unknown",
        "cohort_year": release_date.year,
    }
