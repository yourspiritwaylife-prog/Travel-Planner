# 🧭 Travel-Planner

Окремий Telegram-бот, який складає детальний план подорожі по днях (куди піти,
де поїсти, як дістатись) і малює гарні **картки-картинки** на кожен день.

«Мозок» — це **існуючий Hermes Agent**, який викликається через CLI. Бот працює
**незалежно** від інших ботів (напр. AI-News) і має **власний** Telegram-токен.

---

## 🧩 Архітектура

```
Travel Planner Telegram Bot        (власний TRAVEL_TELEGRAM_BOT_TOKEN)
        │  місто, дні, інтереси, бюджет
        ▼
Travel Planner backend (Python)    bot/  +  planner/
        │  структурований промпт
        ▼
Hermes CLI client                  planner/hermes_client.py
        │  hermes -z "<prompt>"
        ▼
існуючий Hermes Agent              (на сервері DigitalOcean)
        │  JSON-план
        ▼
дані + картки                      planner/enrich.py  +  cards/
        │
        ▼
Travel Planner bot надсилає користувачу картки по днях
```

**Hermes — це CLI, а не HTTP-сервіс.** Жодних URL чи API-ключів. Один Hermes
може обслуговувати кілька ботів — цей бот спроєктований так, щоб згодом легко
вписатися в багатоагентний Telegram-воркспейс.

---

## 📁 Структура (розділення відповідальностей)

| Файл / папка | Що робить |
|---|---|
| `bot/` | **Telegram-інтерфейс**: діалог, кнопки, обробники |
| `planner/brain/` | **Логіка агента**: промпт, розбір відповіді, адаптер мозку |
| `planner/hermes_client.py` | **Hermes CLI-клієнт**: запуск `hermes -z`, таймаут, помилки, логування |
| `planner/enrich.py` | Реальні дані: OpenStreetMap + Wikipedia (без ключів) |
| `planner/pipeline.py` | Конвеєр: мозок → дані → картки |
| `cards/` | Генерація PNG-карток з HTML-шаблону |
| `config.py` | **Конфіг** (читає `.env`) |
| `main.py` | Запуск бота |
| `demo.py` | Офлайн-демо карток без Hermes (`BRAIN=mock`) |

---

## ⚙️ Налаштування (`.env`)

Скопіюй `.env.example` → `.env` і заповни:

```
TRAVEL_TELEGRAM_BOT_TOKEN = <токен НОВОГО бота від @BotFather>
BRAIN = hermes
HERMES_BIN = hermes
HERMES_FLAG = -z
HERMES_TIMEOUT = 180
HERMES_SSH =            # див. нижче
```

### Два режими виклику Hermes

| Де працює бот | `HERMES_SSH` | Як кличе Hermes |
|---|---|---|
| **На сервері** (поряд із Hermes) — рекомендовано | порожньо | `hermes -z "..."` напряму |
| **На іншій машині** (розробка) | `root@144.126.206.226` | `ssh … "hermes -z '...'"` |

> Для SSH-режиму потрібен **passwordless SSH-ключ** (бо пароль вводити нікому).

---

## 🚀 Запуск

### Варіант A — на сервері (продакшн, рекомендовано)
```bash
# у папці проєкту на сервері, де встановлений hermes:
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
# .env: HERMES_SSH лишити порожнім
python main.py
```

### Варіант B — локально (Windows, розробка)
```powershell
pip install -r requirements.txt
playwright install chromium
# .env: HERMES_SSH = root@144.126.206.226 (потрібен SSH-ключ)
python main.py
```

### Перевірити картки без Hermes
```powershell
python demo.py     # BRAIN=mock усередині; згенерує приклад у output/
```

Далі відкрий свого бота в Telegram і напиши **/start**. 🎉

---

## 🛡️ Що цей бот НЕ робить
- не змінює інший (AI-News) бот і його налаштування Hermes;
- не використовує токен іншого бота — лише власний `TRAVEL_TELEGRAM_BOT_TOKEN`;
- не звертається до Hermes по HTTP — лише через CLI.

---

## 💰 Вартість
| Що | Ціна |
|---|---|
| Telegram-бот | безкоштовно |
| Hermes (мозок) | вже працює на твоєму сервері |
| OpenStreetMap, Wikipedia | безкоштовно |
| Хостинг | наявний DigitalOcean |
