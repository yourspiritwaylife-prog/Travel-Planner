---
name: viator-tours
description: Real Viator tours + REAL availability-by-date check (Affiliate API). Use when the user wants a tour/excursion/activity for specific dates — verify it is bookable on their date and give an affiliate link.
version: 1.0.0
author: Hermes Travel profile
license: MIT
metadata:
  hermes:
    tags: [travel, tours, activities, availability, viator, tickets, excursion]
    category: productivity
    requires_toolsets: [terminal]
---

# Viator tours + availability-by-date

Real tours from Viator with REAL availability per date — NO scraping, NO anti-bot,
NO CAPTCHA. Affiliate links carry the user's tracking (she earns commission).
API key in profile `.env`: `VIATOR_API_KEY`.

Script: `/root/.hermes/profiles/travel/skills/productivity/viator/scripts/viator.py`

## Commands

**find** — search + keep ONLY tours AVAILABLE on the date (best rated first). MAIN one:
```
python3 /root/.hermes/profiles/travel/skills/productivity/viator/scripts/viator.py find --query "Ubud waterfalls tour" --date 2026-06-20 [--limit 6]
```

**search** — top tours by rating (no date filter):
```
python3 .../viator.py search --query "Ubud waterfalls" [--limit 5]
```

**availability** — is ONE tour available on a date:
```
python3 .../viator.py availability --product 59225P46 --date 2026-06-20
```

Each tour returns: `code`, `title`, `rating`, `reviews`, `from_price` (USD), `url`
(affiliate link), `flags` (free cancellation / private / skip-the-line / acція),
`availability` = {`status`, `available`, `times`}.
`status`: AVAILABLE | SOLD_OUT | NOT_OPERATING.

## How to use when planning

When the user wants a tour/excursion/activity for a date — run `find` with THEIR date.
- Recommend ONLY tours with `availability.available = true`. NEVER recommend SOLD_OUT.
- Put the affiliate `url` into that stop's `booking.link`.
- In `booking.note` write honestly, e.g.: «✅ перевірено: доступно на 20.06 (07:00/08:00),
  ★4.98 (563), від $39, приватний + free cancellation».
- If `find` returns 0 — say honestly there are no spots for that date; offer another date
  or a different tour.
