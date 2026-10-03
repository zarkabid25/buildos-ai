"""Set a new password for a user in the database configured in backend/.env.

There's no "forgot password" email flow yet, and stored passwords are one-way
hashes that can't be read back, so this is the way back in on a dev machine.
The new password is typed at a hidden prompt; it is never printed or logged.

    cd backend
    .venv\\Scripts\\python.exe scripts\\reset_password.py you@example.com
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/reset_password.py <email>")
    email = sys.argv[1].strip().lower()

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            sys.exit(f"No user with email {email}")

        password = getpass.getpass(f"New password for {user.full_name} ({email}): ")
        if len(password) < 8:
            sys.exit("Password must be at least 8 characters. Nothing changed.")
        if getpass.getpass("Repeat it: ") != password:
            sys.exit("Passwords didn't match. Nothing changed.")

        user.hashed_password = hash_password(password)
        user.is_active = True
        db.commit()
    print(f"Password updated for {email}. Log in at http://localhost:3000/login")


if __name__ == "__main__":
    main()
