from __future__ import annotations

from getpass import getpass

from argon2 import PasswordHasher


def main() -> None:
    password = getpass("Admin password: ")
    confirmation = getpass("Confirm admin password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")
    print(PasswordHasher().hash(password))


if __name__ == "__main__":
    main()
