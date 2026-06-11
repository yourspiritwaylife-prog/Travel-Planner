# 🧭 Travel Agent — джерело правди для живого Hermes-агента

Цей репозиторій тримає **артефакти живого тревел-бота** — Telegram
**@travelplanner_robot**, який працює як **Hermes-агент** (профіль `travel`)
на сервері DigitalOcean і крутиться 24/7 як `hermes-gateway-travel.service`.

> Сам бот — це НЕ Python-застосунок у цьому репо. Це Hermes-агент (мозок
> gpt-5.5), якого описує `_soul_final.md` і обслуговують скрипти-навички.
> Тут ми редагуємо ці файли локально, тестуємо й деплоїмо на сервер.
>
> Ранній Python-прототип бота (`bot/ planner/ cards/ main.py …`) **видалено** —
> він був застарілий і нікого не обслуговував. Історія лишилась у git.

---

## 📁 Що є що

| Файл | Роль |
|---|---|
| `_soul_final.md` | **SOUL** агента: характер, інтейк (куди/дні/інтереси/бюджет/де живе/темп), як планувати, правила турів і посилань. → деплоїться як `SOUL.md`. |
| `_dayplan_server.py` | **Будівник сторінки дня**: тягне з Google Places реальні фото/рейтинги/години/ціни, будує інтерактивний HTML (тап-розгортання, фото в base64), шле документом у Telegram і видаляє тимчасовий файл. → `dayplan.py` (навичка). |
| `_viator_server.py` / `_viator_skill.md` | **Тури/квитки** через Viator Affiliate API (реальна доступність). |
| `preview.py` | **Локальне прев'ю** сторінки дня у браузері (без сервера й Telegram). |
| `samples/` | Приклади JSON одного дня — вхід для `preview.py` / `dayplan.py`. |
| `.env.example` | Локальні ключі для прев'ю/тестів (на сервері — свій .env профілю). |

---

## 👀 Локальне прев'ю сторінки дня

```bash
python preview.py samples/ubud_day1.json
# або свій файл:
python preview.py шлях\до\day.json
```

Будує таку саму HTML-сторінку, як на сервері, і відкриває в браузері.
(Фото/рейтинги порожні без `GOOGLE_PLACES_API_KEY` у `.env` — решта блоків видно.)

---

## 🚀 Деплой на сервер (профіль `travel` — і ТІЛЬКИ він)

SSH-ключ: `C:/Users/Acer/.ssh/hermes_planner` → `root@144.126.206.226`.

1. Перед заливкою: завантаж поточний живий файл, звір із локальним
   (чи різниця — саме твоя зміна), зроби бекап `*.bak-<дата>`.
2. `scp` у профіль:
   - `_soul_final.md` → `/root/.hermes/profiles/travel/SOUL.md`
   - `_dayplan_server.py` → `/root/.hermes/profiles/travel/skills/productivity/dayplan/scripts/dayplan.py`
3. Перезапуск **лише** travel-шлюзу:
   `systemctl restart hermes-gateway-travel.service`
   (НІКОЛИ не чіпати дефолтний `hermes-gateway.service` — це AI-News бот.)

---

## 🌍 Мови та голос

- Мозок (gpt-5.5) відповідає **будь-якою мовою**; **голос увімкнено**
  (локальний Whisper, який ще й визначає мову).
- Багатомовність ведеться в `_soul_final.md` (визначити мову користувача й
  вести інтейк/план/дані тією ж мовою) + локалізованих підписах
  `_dayplan_server.py`.

## 📱 Канали

Hermes-шлюз нативно підтримує **Telegram + WhatsApp** (+Discord/Weixin) на
одному профілі. WhatsApp під'єднується через `hermes whatsapp` (QR-парування).
