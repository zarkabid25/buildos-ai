"""Create (or reset) a BuildOS platform admin in the database configured in backend/.env.

There is no self-registration for platform admins by design: a Platform Super Admin
account can see across every tenant company, so the only way in is this script,
run by whoever already has shell access to the server. The password is typed at a
hidden prompt; it is never printed or logged.

    cd backend
    .venv\\Scripts\\python.exe scripts\\create_platform_admin.py you@buildos.ai "Your Name"
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.platform_admin import PlatformAdmin  # noqa: E402


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit('Usage: python scripts/create_platform_admin.py <email> "<full name>"')
    email = sys.argv[1].strip().lower()
    full_name = sys.argv[2].strip()

    password = getpass.getpass(f"Password for platform admin {email}: ")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters. Nothing changed.")
    if getpass.getpass("Repeat it: ") != password:
        sys.exit("Passwords didn't match. Nothing changed.")

    with SessionLocal() as db:
        existing = db.query(PlatformAdmin).filter(PlatformAdmin.email == email).first()
        if existing:
            existing.hashed_password = hash_password(password)
            existing.full_name = full_name
            existing.is_active = True
            db.commit()
            print(f"Updated existing platform admin {email}.")
        else:
            admin = PlatformAdmin(email=email, full_name=full_name, hashed_password=hash_password(password))
            db.add(admin)
            db.commit()
            print(f"Created platform admin {email}.")


if __name__ == "__main__":
    main()
