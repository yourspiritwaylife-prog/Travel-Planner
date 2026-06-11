"""
Промпт для мозку: просимо повернути СТРОГО JSON у потрібній формі.
Тримаємо окремо, щоб легко покращувати текст без зміни логіки.

Ключова ідея багатомовності: ЛЮДСЬКИЙ текст (intro, title, summary, name,
note, підказки) — мовою користувача; а МАШИННІ коди (kind, time_of_day) —
завжди фіксовані англійські ключі. Так план будь-якою мовою лишається
розбірним для коду й коректно малюється на картках.
"""
from __future__ import annotations

from planner.i18n import (
    budget_label,
    english_language_name,
    interest_label,
)
from planner.models import PlaceKind, TimeOfDay, TripRequest

# Допустимі англійські коди для машинних полів (із Enum-ів).
_KIND_CODES = " | ".join(k.value for k in PlaceKind)
_TIME_CODES = " | ".join(t.value for t in TimeOfDay)

# Описуємо очікувану структуру простими словами для будь-якого LLM.
_JSON_SHAPE = f"""
{{
  "intro": "1-2 warm sentences about the trip (in the user's language)",
  "days": [
    {{
      "day_number": 1,
      "title": "short day theme, e.g. 'Old Town' (user's language)",
      "summary": "1 sentence — the essence of the day (user's language)",
      "transport_hint": "how to get around that day (user's language)",
      "places": [
        {{
          "name": "exact real place name (keep original/local spelling)",
          "kind": "ONE English code: {_KIND_CODES}",
          "time_of_day": "ONE English code: {_TIME_CODES}",
          "note": "1 sentence: why it's worth it (user's language)",
          "travel_hint": "how to get here from the previous point (user's language)"
        }}
      ]
    }}
  ]
}}
"""


def build_planning_prompt(req: TripRequest) -> str:
    lang = req.language or "uk"
    language_name = english_language_name(lang)
    interests = (
        ", ".join(interest_label(i, lang) for i in req.interests)
        or "general highlights"
    )
    budget = budget_label(req.budget, lang)

    return f"""You are an experienced travel guide. Build a detailed trip plan.

INPUT:
- City/destination: {req.city}
- Number of days: {req.days}
- Traveller interests: {interests}
- Budget: {budget}
- RESPONSE LANGUAGE: {language_name}

LANGUAGE RULES (important):
- Write ALL human-readable text (intro, title, summary, note, transport_hint,
  travel_hint) in {language_name}.
- Keep real place names in their original/local spelling inside "name".
- The fields "kind" and "time_of_day" MUST be one of the fixed ENGLISH codes
  listed below — never translate these two fields.

PLAN REQUIREMENTS:
1. Exactly {req.days} day(s). Each day is a logical route across nearby spots
   (avoid criss-crossing the whole city).
2. Start EACH day with breakfast (time_of_day="breakfast", a café or bakery),
   then 4-6 stops, always including lunch and dinner (real venues).
3. Respect the interests ({interests}) and the budget ({budget}).
4. For every stop give a real name, the time of day and a short reason to go.
5. In "name" write ONLY the clean place name without parenthetical notes
   (right: "Town Hall"; wrong: "Town Hall (viewpoint)").
6. Add a transport hint between points.

ALLOWED CODES:
- kind: {_KIND_CODES}
- time_of_day: {_TIME_CODES}

RESPONSE FORMAT — ONLY valid JSON (no explanations, no markdown),
exactly this structure:
{_JSON_SHAPE}

Return only the JSON object."""