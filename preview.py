"""
Локальний перегляд сторінки дня — БЕЗ сервера й БЕЗ надсилання в Telegram.

Бере JSON дня (за замовчуванням samples/ubud_day1.json), будує таку саму HTML-
сторінку, як на сервері, і зберігає в output/ — відкрий її у браузері.

Запуск:
  python preview.py                      # приклад Убуду
  python preview.py samples/ubud_day1.json
  python preview.py шлях\до\свого\day.json

Фото/рейтинги тут будуть порожні (вони підтягуються Google-ключем на сервері),
але всі НОВІ блоки — транспорт, культура, виїзди, час і тривалість — видно.
Якщо хочеш і фото локально — поклади GOOGLE_PLACES_API_KEY у файл .env.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent
DEFAULT = ROOT / "samples" / "ubud_day1.json"


def _load_generator():
    """Підвантажити серверний генератор сторінки (_dayplan_server.py)."""
    spec = importlib.util.spec_from_file_location(
        "dayplan_local", ROOT / "_dayplan_server.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not src.exists():
        print(f"Не знайдено файл: {src}")
        sys.exit(1)

    day = json.loads(src.read_text(encoding="utf-8"))
    generator = _load_generator()
    html = generator.build_html(day)

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"preview_{src.stem}.html"
    out.write_text(html, encoding="utf-8")

    print(f"Готово! Сторінка: {out.resolve()}")
    print("Відкриваю у браузері…")
    webbrowser.open(out.resolve().as_uri())


if __name__ == "__main__":
    main()
