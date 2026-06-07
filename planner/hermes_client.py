"""
Hermes CLI-клієнт.

Єдина відповідальність цього модуля — викликати ВСТАНОВЛЕНИЙ Hermes Agent
через командний рядок:

    hermes -z "<prompt>"

і повернути його текстову відповідь. Це НЕ HTTP-API: ні URL, ні ключів.

Два режими роботи (визначається конфігом, код однаковий):
  • локально  — бот працює на тому ж сервері, що й Hermes  →  `hermes -z "..."`
  • через SSH — бот працює на іншій машині (розробка)       →  `ssh user@host "hermes -z '...'"`

Клас спроєктований так, щоб його легко було перевикористати в майбутньому
багатоагентному Telegram-воркспейсі (одна точка виклику Hermes).
"""
from __future__ import annotations

import asyncio
import logging
import shlex
import time

from config import settings

logger = logging.getLogger(__name__)


class HermesError(RuntimeError):
    """Будь-яка проблема під час виклику Hermes CLI."""


class HermesTimeout(HermesError):
    """Hermes не відповів за відведений час."""


class HermesNotFound(HermesError):
    """Команду `hermes` не знайдено там, де запущено бота."""


class HermesCLIClient:
    """Тонкий асинхронний обгортка над `hermes -z "<prompt>"`."""

    def __init__(
        self,
        binary: str | None = None,
        flag: str | None = None,
        timeout: int | None = None,
        ssh: str | None = None,
        ssh_key: str | None = None,
    ) -> None:
        self.binary = binary or settings.hermes_bin
        self.flag = flag or settings.hermes_flag
        self.timeout = timeout or settings.hermes_timeout
        # ssh="" означає локальний режим; None → беремо з конфіга
        self.ssh = settings.hermes_ssh if ssh is None else ssh
        self.ssh_key = settings.hermes_ssh_key if ssh_key is None else ssh_key

    # ------------------------------------------------------------------ #
    def _build_argv(self, prompt: str) -> list[str]:
        """Зібрати команду для запуску (локально або через SSH)."""
        if self.ssh:
            # На віддаленій стороні команду виконує shell — акуратно екрануємо.
            remote_cmd = f"{self.binary} {self.flag} {shlex.quote(prompt)}"
            argv = [
                "ssh",
                "-o", "BatchMode=yes",            # без інтерактивного пароля → не зависне
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ConnectTimeout=15",
            ]
            if self.ssh_key:
                argv += ["-i", self.ssh_key]
            argv += [self.ssh, remote_cmd]
            return argv
        # Локально — без shell, аргументи передаємо напряму (безпечно).
        return [self.binary, self.flag, prompt]

    # ------------------------------------------------------------------ #
    async def run(self, prompt: str) -> str:
        """Надіслати prompt у Hermes і повернути текст відповіді (stdout)."""
        argv = self._build_argv(prompt)
        where = f"ssh:{self.ssh}" if self.ssh else "local"
        logger.info(
            "Hermes CLI [%s]: %s %s, prompt=%d симв., timeout=%ss",
            where, self.binary, self.flag, len(prompt), self.timeout,
        )
        started = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            cmd = "ssh" if self.ssh else self.binary
            raise HermesNotFound(
                f"Не знайдено команду '{cmd}'. "
                f"{'Перевір SSH-клієнт.' if self.ssh else 'Чи встановлений Hermes CLI на цій машині?'}"
            ) from exc

        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise HermesTimeout(
                f"Hermes не відповів за {self.timeout}с (prompt={len(prompt)} симв.)."
            ) from exc

        elapsed = time.monotonic() - started
        stdout = (stdout_b or b"").decode("utf-8", "replace").strip()
        stderr = (stderr_b or b"").decode("utf-8", "replace").strip()

        if proc.returncode != 0:
            logger.error(
                "Hermes CLI помилка: exit=%s, stderr=%s",
                proc.returncode, stderr[:600],
            )
            raise HermesError(
                f"Hermes завершився з кодом {proc.returncode}. "
                f"Деталі: {stderr[:300] or '(stderr порожній)'}"
            )

        if not stdout:
            raise HermesError(
                f"Hermes повернув порожню відповідь за {elapsed:.1f}с. "
                f"stderr: {stderr[:300] or '(порожній)'}"
            )

        logger.info(
            "Hermes CLI ✓ за %.1fс, відповідь=%d симв.", elapsed, len(stdout)
        )
        return stdout
