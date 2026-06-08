#!/usr/bin/env python3
"""
dayplan.py — побудувати ІНТЕРАКТИВНУ сторінку плану дня і надіслати в Telegram.

Працює БЕЗ браузера (легко для маленького сервера): тягне з Google Places реальні
фото (вшиває їх у файл як base64), рейтинги, години, ціни; будує HTML без JS
(тап на картку -> розгортається з деталями); надсилає документом у чат і ВИДАЛЯЄ
тимчасовий файл (нічого не зберігається).

Виклик:
  python3 dayplan.py --data /tmp/day.json [--chat <id>] [--caption "..."]

JSON одного дня:
{
  "city": "Рим", "day_label": "День 1 / 3",
  "day_title": "Давній Рим", "summary": "...",
  "foot": "Транспорт: пішки",
  "stops": [
    {"time":"Сніданок","name":"Caffè Oppio","query":"Caffe Oppio, Rome",
     "desc":"...","dish":"Карбонара","why":"...","travel":"метро 5 хв"}, ...
  ]
}
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
import subprocess
import urllib.request


def _env(keys):
    vals = {k: os.environ.get(k, "").strip() for k in keys}
    missing = [k for k in keys if not vals[k]]
    if missing:
        here = os.path.dirname(os.path.abspath(__file__))
        for up in ("../../../../.env", "../../../.env", "../../.env"):
            p = os.path.abspath(os.path.join(here, up))
            if not os.path.exists(p):
                continue
            try:
                with open(p, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        for k in missing:
                            if line.startswith(k + "="):
                                vals[k] = line.split("=", 1)[1].strip().strip('"').strip("'")
            except OSError:
                pass
            break
    return vals


ENV = _env(["GOOGLE_PLACES_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_HOME_CHANNEL"])
KEY = ENV["GOOGLE_PLACES_API_KEY"]
PRICE = {"PRICE_LEVEL_INEXPENSIVE": "€", "PRICE_LEVEL_MODERATE": "€€",
         "PRICE_LEVEL_EXPENSIVE": "€€€", "PRICE_LEVEL_VERY_EXPENSIVE": "€€€€"}


def esc(s):
    return html.escape(str(s or ""))


def num(n):
    return f"{n:,}".replace(",", " ") if n else "0"


def fetch(query):
    if not KEY:
        return {}
    body = {"textQuery": query, "languageCode": "uk", "pageSize": 1}
    req = urllib.request.Request(
        "https://places.googleapis.com/v1/places:searchText",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": KEY,
                 "X-Goog-FieldMask": ("places.rating,places.userRatingCount,"
                 "places.priceLevel,places.currentOpeningHours.weekdayDescriptions,"
                 "places.photos,places.formattedAddress,places.websiteUri")},
        method="POST")
    try:
        p = (json.loads(urllib.request.urlopen(req, timeout=25).read().decode())
             .get("places") or [{}])[0]
    except Exception:  # noqa: BLE001
        p = {}
    photos = p.get("photos") or []
    purl = (f"https://places.googleapis.com/v1/{photos[0]['name']}/media"
            f"?maxWidthPx=520&maxHeightPx=420&key={KEY}") if photos else ""
    hrs = (p.get("currentOpeningHours") or {}).get("weekdayDescriptions") or []
    return {"rating": p.get("rating"), "reviews": p.get("userRatingCount"),
            "price": PRICE.get(p.get("priceLevel"), ""),
            "hours": (hrs[0].split(": ", 1)[-1] if hrs else ""),
            "addr": p.get("formattedAddress", ""),
            "website": p.get("websiteUri", ""), "purl": purl}


def photo_data(url):
    if not url:
        return ""
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            ct = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
            raw = r.read()
        return f"data:{ct};base64," + base64.b64encode(raw).decode()
    except Exception:  # noqa: BLE001
        return ""


CSS = """*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,'Segoe UI',system-ui,Arial,sans-serif;background:#f1ecff;color:#232838;padding-bottom:26px}
.hero{background:linear-gradient(135deg,#ff7a59,#fc5c8d 45%,#7c5cff);color:#fff;padding:24px 20px 20px;border-radius:0 0 26px 26px}
.hero .city{letter-spacing:5px;font-size:13px;opacity:.9;text-transform:uppercase}
.hero .day{font-size:34px;font-weight:800;line-height:1.05;margin-top:6px}
.hero .ttl{font-size:20px;font-weight:700;margin-top:11px}
.hero .sum{font-size:14px;opacity:.95;margin-top:6px;line-height:1.4}
.list{padding:15px}
.stop{background:#fff;border-radius:18px;box-shadow:0 6px 16px rgba(80,60,160,.12);overflow:hidden;margin-bottom:13px}
.stop>summary{list-style:none;display:flex;cursor:pointer;align-items:stretch}
.stop>summary::-webkit-details-marker{display:none}
.th{width:110px;min-width:110px;height:116px;object-fit:cover;background:#e7e2f5}
.in{padding:11px 13px;flex:1;min-width:0}
.when{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;color:#7c5cff;background:rgba(124,92,255,.12);padding:3px 10px;border-radius:999px}
.nm{font-size:17px;font-weight:700;margin-top:6px;line-height:1.2}
.mt{font-size:13px;color:#888;margin-top:5px}
.star{color:#f5a623;font-weight:700}
.tap{font-size:12px;color:#fc5c8d;margin-top:7px;font-weight:700}
.stop[open] .tap{color:#aaa}
.more{padding:2px 16px 18px;border-top:1px solid #f0ecf8}
.more .r{margin-top:12px;font-size:15px;line-height:1.5}
.more .r b{color:#7c5cff}
.chip{display:inline-block;background:#fff0f5;color:#fc5c8d;font-weight:700;font-size:14px;padding:6px 13px;border-radius:10px;margin-top:7px}
.more .addr{color:#9a93a8;font-size:13px;margin-top:12px}
.more .site{margin-top:12px;font-size:14px}
.more .site a{color:#7c5cff;font-weight:700;text-decoration:none}
.more .bk{margin-top:12px;background:#f3f0ff;border-radius:10px;padding:10px 12px;font-size:14px;line-height:1.5}
.more .bk a{color:#7c5cff;font-weight:700;text-decoration:none}
.more .alt{margin-top:12px;background:#eef6ff;border-radius:10px;padding:9px 12px;font-size:14px;line-height:1.5;color:#2a6da7}
.more .alt b{color:#2a6da7}
.more .ahead{margin-top:9px;color:#d12b2b;font-weight:800;font-size:14px;background:#ffe8e8;border-radius:9px;padding:8px 11px}
.alert{margin:13px 15px 0;background:#ffe8e8;color:#d12b2b;border:1.6px solid #ff9b9b;border-radius:13px;padding:12px 14px;font-weight:800;font-size:14px;line-height:1.4;animation:pulse 1.6s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
.badge-book{display:inline-block;background:#ffe1e1;color:#d12b2b;font-size:11px;font-weight:800;padding:3px 9px;border-radius:999px;margin-left:6px;border:1px solid #ffb3b3;vertical-align:middle}
.dur{font-size:11px;color:#9a93a8;margin-left:8px;font-weight:600}
.info{margin:13px 15px 0;background:#fff;border-radius:16px;box-shadow:0 5px 14px rgba(80,60,160,.10);overflow:hidden}
.info>summary{list-style:none;display:flex;align-items:center;justify-content:space-between;cursor:pointer;padding:14px 15px}
.info>summary::-webkit-details-marker{display:none}
.info h3{font-size:14px;font-weight:800;color:#7c5cff}
.info.cult h3{color:#e0683f}
.info.tips h3{color:#2aa775}
.info .arr{color:#c3bdd4;font-size:13px;font-weight:700;margin-left:10px}
.info[open] .arr{color:#7c5cff}
.info .ibody{padding:0 15px 14px}
.info .li{font-size:14px;line-height:1.5;color:#3a3f4b;padding-left:18px;position:relative;margin-top:6px}
.info .li::before{content:"•";position:absolute;left:4px;color:#fc5c8d;font-weight:700}
.trip{margin:13px 15px 0;background:#fff;border-radius:16px;padding:13px 15px;box-shadow:0 5px 14px rgba(80,60,160,.10)}
.trip h3{font-size:14px;font-weight:800;color:#4bb6d8;margin-bottom:9px}
.trip .t{padding:9px 0;border-top:1px solid #f0ecf8}
.trip .t:first-of-type{border-top:none}
.trip .t .tn{font-size:15px;font-weight:700}
.trip .t .td{font-size:13px;color:#515767;line-height:1.45;margin-top:3px}
.trip .t a{display:inline-block;margin-top:6px;color:#7c5cff;font-weight:700;font-size:13px;text-decoration:none}
.foot{margin:14px 20px 0;font-size:13px;color:#7a7488;text-align:center}"""


def stop_block(s):
    star = (f'<span class="star">★ {s["rating"]}</span> ({num(s["reviews"])})'
            if s.get("rating") else '<span style="color:#aaa">рейтинг уточнюється</span>')
    price = f' · {s["price"]}' if s.get("price") else ""
    rows = ""
    if s.get("hours"):
        rows += f'<div class="r">🕐 <b>Працює:</b> {esc(s["hours"])}</div>'
    if s.get("desc"):
        rows += f'<div class="r">{esc(s["desc"])}</div>'
    if s.get("dish"):
        rows += f'<div class="r">🍽 <b>Що замовити:</b></div><span class="chip">{esc(s["dish"])}</span>'
    if s.get("why"):
        rows += f'<div class="r">✨ <b>Чому варто:</b> {esc(s["why"])}</div>'
    if s.get("alt"):
        rows += f'<div class="r alt">🏨 <b>Альтернатива:</b> {esc(s["alt"])}</div>'
    if s.get("travel"):
        rows += f'<div class="r">🚕 <b>Як дістатись:</b> {esc(s["travel"])}</div>'
    if s.get("booking"):
        b = s["booking"]
        lbl = esc(b.get("label") or "Тур / квиток")
        link = (f' <a href="{esc(b["link"])}" target="_blank" rel="noopener">'
                f'забронювати →</a>') if b.get("link") else ""
        note = f'<br>{esc(b["note"])}' if b.get("note") else ""
        rows += f'<div class="r bk">🎟 <b>{lbl}:</b>{link}{note}</div>'
    if s.get("book_ahead"):
        rows += ('<div class="r ahead">⏳ Бронюй заздалегідь — місця/квитки '
                 'часто розкуповують наперед</div>')
    if s.get("website"):
        rows += (f'<div class="r site">🔗 <a href="{esc(s["website"])}" '
                 f'target="_blank" rel="noopener">Офіційний сайт</a></div>')
    if s.get("addr"):
        rows += f'<div class="addr">📍 {esc(s["addr"])}</div>'
    # час доби + (опц.) точний час старту та тривалість
    when = f'{esc(s["start"])} · {esc(s["time"])}' if s.get("start") else esc(s["time"])
    dur = f'<span class="dur">⏱ {esc(s["duration"])}</span>' if s.get("duration") else ""
    badge = '<span class="badge-book">🎟 заздалегідь</span>' if s.get("book_ahead") else ""
    img = s.get("photo") or ""
    return (f'<details class="stop"><summary><img class="th" src="{img}">'
            f'<div class="in"><span class="when">{when}</span>{dur}{badge}'
            f'<div class="nm">{esc(s["name"])}</div><div class="mt">{star}{price}</div>'
            f'<div class="tap">↓ натисни для деталей</div></div></summary>'
            f'<div class="more">{rows}</div></details>')


def info_box(title, items, cls=""):
    """Згортний блок-список (транспорт / культура / поради): тап -> розгортається.
    items — рядок або список рядків."""
    if not items:
        return ""
    if isinstance(items, str):
        items = [items]
    lis = "".join(f'<div class="li">{esc(it)}</div>' for it in items if it)
    if not lis:
        return ""
    return (f'<details class="info {cls}"><summary><h3>{esc(title)}</h3>'
            f'<span class="arr">натисни ↓</span></summary>'
            f'<div class="ibody">{lis}</div></details>')


def daytrips_box(trips):
    """Секція «Виїзди поряд» з перевіреними посиланнями."""
    if not trips:
        return ""
    rows = ""
    for t in trips:
        if not t.get("name"):
            continue
        link = (f'<a href="{esc(t["link"])}" target="_blank" rel="noopener">'
                f'Детальніше / забронювати →</a>' if t.get("link") else "")
        why = f' {esc(t["why"])}' if t.get("why") else ""
        rows += (f'<div class="t"><div class="tn">{esc(t["name"])}</div>'
                 f'<div class="td">{esc(t.get("desc", ""))}{why}</div>{link}</div>')
    return f'<div class="trip"><h3>🌋 Виїзди поряд</h3>{rows}</div>' if rows else ""


def build_html(day):
    stops = day.get("stops", [])
    for s in stops:
        g = fetch(s.get("query", s.get("name", "")))
        for k, v in g.items():
            if k != "purl" and not s.get(k):
                s[k] = v
        s["photo"] = photo_data(g.get("purl"))
    blocks = "\n".join(stop_block(s) for s in stops)
    needs_book = any(s.get("book_ahead") for s in stops)
    alert = ('<div class="alert">⚠️ У ЦЕЙ ДЕНЬ є що бронювати ЗАЗДАЛЕГІДЬ — '
             'шукай позначки 🎟 нижче</div>') if needs_book else ""
    around = info_box("🚕 Пересування сьогодні", day.get("getting_around"))
    culture = info_box("🛕 Культура й традиції", day.get("culture"), "cult")
    tips = info_box("💡 Корисно знати", day.get("tips"), "tips")
    trips = daytrips_box(day.get("daytrips"))
    foot = esc(day.get("foot", "")) or "Гарної подорожі! 🎒"
    return f"""<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(day.get('city',''))} — план</title><style>{CSS}</style></head><body>
<div class="hero"><div class="city">{esc(day.get('city',''))}</div>
<div class="day">{esc(day.get('day_label',''))} · {esc(day.get('day_title',''))}</div>
<div class="sum">{esc(day.get('summary',''))}</div></div>
{alert}{around}{culture}{tips}
<div class="list">{blocks}</div>
{trips}
<div class="foot">{foot}</div></body></html>"""


def send(path, chat, caption, filename=""):
    token = ENV.get("TELEGRAM_BOT_TOKEN")
    chat = chat or ENV.get("TELEGRAM_HOME_CHANNEL")
    if not (token and chat):
        return "NO_TOKEN_OR_CHAT"
    doc = f"document=@{path};type=text/html"
    if filename:
        doc += f";filename={filename}"
    cmd = ["curl", "-sS", "-F", f"chat_id={chat}", "-F", doc]
    if caption:
        cmd += ["-F", f"caption={caption}"]
    cmd.append(f"https://api.telegram.org/bot{token}/sendDocument")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        return "SENT_OK" if '"ok":true' in r.stdout else f"SEND_FAIL: {r.stdout[:200]}"
    except Exception as e:  # noqa: BLE001
        return f"SEND_ERROR: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--chat", default="")
    ap.add_argument("--caption", default="")
    ap.add_argument("--keep", action="store_true", help="не видаляти файл (для дебагу)")
    args = ap.parse_args()
    with open(args.data, encoding="utf-8") as fh:
        day = json.load(fh)
    page = build_html(day)
    safe = "".join(c if c.isalnum() else "_" for c in day.get("city", "trip"))[:20]
    out = f"/tmp/plan_{safe}_{os.getpid()}.html"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    # Зрозуміла назва документа в Telegram: «План — Убуд, День 1 з 7 (12 червня).html»
    label = (day.get("day_label") or "").replace(" / ", " з ").replace("/", "-")
    date = (day.get("date") or "").strip()
    pretty = f"План — {day.get('city', 'подорож')}"
    if label:
        pretty += f", {label}"
    if date:
        pretty += f" ({date})"
    pretty = pretty.replace(";", " ").strip() + ".html"
    print("BUILT:", out, f"({os.path.getsize(out)//1024} KB)")
    print(send(out, args.chat, args.caption, pretty))
    if not args.keep:
        # Прибираємо і згенерований HTML, і ВХІДНИЙ JSON дня — щоб старі дні
        # не лишались у /tmp і не надсилались повторно (захист від дублів).
        for path in (out, args.data):
            try:
                os.remove(path)
            except OSError:
                pass
        print("CLEANED: temp html + input json deleted")


if __name__ == "__main__":
    main()
