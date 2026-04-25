"""Тест HTML письма с кодом (как в проде). Запуск: cd api && .venv/bin/python scripts/send_test_email.py [email] [код_опционально]"""

from __future__ import annotations

import asyncio
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

from app.otp_util import generate_otp_code  # noqa: E402
from app.services.mail import send_otp_email  # noqa: E402


async def main() -> None:
    to = sys.argv[1] if len(sys.argv) > 1 else "factiosi@gmail.com"
    code = sys.argv[2] if len(sys.argv) > 2 else generate_otp_code()
    await send_otp_email(to, code)
    print("sent_ok", to)


if __name__ == "__main__":
    asyncio.run(main())
