import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

from app.config import settings  # noqa: E402

print("smtp_user_len", len((settings.smtp_user or "").strip()))
print("smtp_password_len", len((settings.smtp_password or "").strip()))
