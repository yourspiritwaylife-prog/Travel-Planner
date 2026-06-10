#!/usr/bin/env python3
"""
viator.py — РЕАЛЬНІ тури Viator + перевірка НАЯВНОСТІ НА ДАТУ (Affiliate API).

Навіщо: щоб тревел-агент пропонував лише тури, які СПРАВДІ доступні на дату
користувача, з реальним рейтингом/ціною й партнерським лінком (комісія).

Ключ читається з env VIATOR_API_KEY (або з .env профілю на 4 рівні вище).
Тільки Python stdlib.

Команди:
  search       --query "<що>" [--limit N]            топ турів за рейтингом
  availability --product <code> --date YYYY-MM-DD     чи вільний тур на дату
  find         --query "<що>" --date YYYY-MM-DD [--limit N]
               пошук + лишити ЛИШЕ доступні на дату (найкращі першими) — головна команда

Приклади:
  python3 viator.py find --query "Ubud waterfalls tour" --date 2026-06-20
  python3 viator.py availability --product 59225P46 --date 2026-06-20
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date as Date

API = "https://api.viator.com/partner"
WEEKDAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY",
            "FRIDAY", "SATURDAY", "SUNDAY"]


def _key() -> str:
    k = os.environ.get("VIATOR_API_KEY", "").strip()
    if k:
        return k
    here = os.path.dirname(os.path.abspath(__file__))
    envp = os.path.abspath(os.path.join(here, "..", "..", "..", "..", ".env"))
    try:
        with open(envp, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("VIATOR_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    sys.exit("ERROR: немає VIATOR_API_KEY (ні в env, ні в .env профілю)")


def _req(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={
            "exp-api-key": _key(),
            "Accept": "application/json;version=2.0",
            "Accept-Language": "en-US",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        sys.exit(f"ERROR: Viator {e.code}: {detail}")
    except Exception as e:  # noqa: BLE001
        sys.exit(f"ERROR: {type(e).__name__}: {e}")


_FLAG_UA = {
    "FREE_CANCELLATION": "безкоштовне скасування",
    "PRIVATE_TOUR": "приватний тур",
    "SKIP_THE_LINE": "без черги",
    "SPECIAL_OFFER": "акція",
    "LIKELY_TO_SELL_OUT": "швидко розкуповують",
}


def search(query: str, limit: int = 5, currency: str = "USD") -> list[dict]:
    body = {
        "searchTerm": query,
        "searchTypes": [{"searchType": "PRODUCTS",
                         "pagination": {"start": 1, "count": max(1, min(limit, 20))}}],
        "currency": currency,
    }
    d = _req("POST", "/search/freetext", body)
    out = []
    for p in d.get("products", {}).get("results", []):
        rv = p.get("reviews", {}) or {}
        pr = p.get("pricing", {}) or {}
        rating = rv.get("combinedAverageRating")
        out.append({
            "code": p.get("productCode"),
            "title": p.get("title"),
            "rating": round(rating, 2) if rating else None,
            "reviews": rv.get("totalReviews"),
            "from_price": (pr.get("summary", {}) or {}).get("fromPrice"),
            "currency": pr.get("currency"),
            "url": p.get("productUrl"),
            "flags": [_FLAG_UA.get(f, f) for f in (p.get("flags") or [])],
        })
    return out


def availability(product_code: str, date_str: str) -> dict:
    """Чи доступний тур на конкретну дату (із content-розкладу, Basic Access)."""
    try:
        target = Date.fromisoformat(date_str)
    except ValueError:
        return {"status": "BAD_DATE", "available": False, "times": []}
    weekday = WEEKDAYS[target.weekday()]
    d = _req("GET", f"/availability/schedules/{product_code}")

    operating = False
    times: set[str] = set()
    for item in d.get("bookableItems", []):
        for season in item.get("seasons", []):
            sd, ed = season.get("startDate"), season.get("endDate")
            if sd and target < Date.fromisoformat(sd):
                continue
            if ed and target > Date.fromisoformat(ed):
                continue
            for rec in season.get("pricingRecords", []):
                if weekday not in rec.get("daysOfWeek", []):
                    continue
                operating = True
                for te in rec.get("timedEntries", []):
                    blocked = {u.get("date") for u in te.get("unavailableDates", [])}
                    if date_str not in blocked:
                        times.add(te.get("startTime") or "")

    if times:
        status = "AVAILABLE"
    elif operating:
        status = "SOLD_OUT"        # цього дня працює, але місць немає
    else:
        status = "NOT_OPERATING"   # цього дня тур узагалі не їздить
    return {"status": status, "available": bool(times),
            "times": sorted(t for t in times if t)}


def find(query: str, date_str: str, limit: int = 6) -> list[dict]:
    """Пошук + лишити ЛИШЕ доступні на дату тури (найкращі першими)."""
    avail = []
    for it in search(query, limit=limit):
        if not it["code"]:
            continue
        a = availability(it["code"], date_str)
        it["availability"] = a
        if a["available"]:
            avail.append(it)
    avail.sort(key=lambda x: (x.get("rating") or 0, x.get("reviews") or 0), reverse=True)
    return avail


def main() -> None:
    ap = argparse.ArgumentParser(description="Viator tours + date availability")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search")
    s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=5)

    a = sub.add_parser("availability")
    a.add_argument("--product", required=True)
    a.add_argument("--date", required=True, help="YYYY-MM-DD")

    f = sub.add_parser("find")
    f.add_argument("--query", required=True)
    f.add_argument("--date", required=True, help="YYYY-MM-DD")
    f.add_argument("--limit", type=int, default=6)

    args = ap.parse_args()
    if args.cmd == "search":
        print(json.dumps(search(args.query, args.limit), ensure_ascii=False, indent=2))
    elif args.cmd == "availability":
        print(json.dumps(availability(args.product, args.date), ensure_ascii=False, indent=2))
    elif args.cmd == "find":
        r = find(args.query, args.date, args.limit)
        print(json.dumps({"date": args.date, "count": len(r), "tours": r},
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
