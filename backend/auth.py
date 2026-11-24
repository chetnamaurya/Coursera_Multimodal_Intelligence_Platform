"""
Password hashing and user management for the dashboard.

Users are stored in .streamlit/secrets.toml (never committed):

    [auth.users.alice]
    display_name = "Alice Smith"
    role = "educator"            # admin | educator | viewer
    password_hash = "pbkdf2_sha256$600000$...$..."

Create or update a user from the project root:

    python -m backend.auth add-user alice --role educator --name "Alice Smith"
"""

import argparse
import base64
import getpass
import hashlib
import hmac
import re
import secrets
import sys
from pathlib import Path

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000
ROLES = ("admin", "educator", "viewer")

# Roles allowed to generate AI reports and save review decisions.
REVIEWER_ROLES = ("admin", "educator")

BASE_DIR = Path(__file__).resolve().parent.parent
SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"

USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]{3,32}$")


def hash_password(password, iterations=ITERATIONS):
    salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )

    return "$".join([
        ALGORITHM,
        str(iterations),
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    ])


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt_b64, digest_b64 = (
            stored_hash.split("$")
        )

        if algorithm != ALGORITHM:
            return False

        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)

        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )

    except (ValueError, TypeError):
        return False

    # Constant-time comparison prevents timing attacks
    return hmac.compare_digest(actual, expected)


# Used when the username does not exist, so a failed lookup
# takes as long as a wrong password and does not reveal
# which usernames are valid.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def authenticate(username, password, users):
    """
    Return the user's profile dict if the credentials are valid,
    otherwise None. `users` is the [auth.users] secrets mapping.
    """
    username = (username or "").strip().lower()
    record = users.get(username) if username else None

    if record is None:
        verify_password(password or "", _DUMMY_HASH)
        return None

    if not verify_password(password or "", record.get("password_hash", "")):
        return None

    role = record.get("role", "viewer")

    if role not in ROLES:
        role = "viewer"

    return {
        "username": username,
        "display_name": record.get("display_name", username),
        "role": role,
    }


def _toml_string(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _user_block(username, display_name, role, password_hash):
    return (
        f"[auth.users.{username}]\n"
        f"display_name = {_toml_string(display_name)}\n"
        f"role = {_toml_string(role)}\n"
        f"password_hash = {_toml_string(password_hash)}\n"
    )


def _upsert_user(path, username, block):
    """Replace the user's block in secrets.toml, or append it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else ""

    pattern = re.compile(
        rf"^\[auth\.users\.{re.escape(username)}\]\n(?:(?!\[).*\n?)*",
        re.MULTILINE,
    )

    if pattern.search(text):
        text = pattern.sub(block + "\n", text, count=1)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += ("\n" if text else "") + block

    path.write_text(text, encoding="utf-8")


def _prompt_password(label, parser):
    # Terminals such as VS Code wrap pasted text in invisible
    # bracketed-paste markers that getpass captures verbatim.
    password = getpass.getpass(label)
    password = password.replace("\x1b[200~", "").replace("\x1b[201~", "")

    if any(ord(ch) < 32 or ord(ch) == 127 for ch in password):
        parser.error(
            "the password contains hidden control characters "
            "(usually from pasting). Type it instead of pasting."
        )

    return password


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Manage dashboard users."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser(
        "add-user", help="Create a user or reset their password"
    )
    add.add_argument("username")
    add.add_argument("--role", choices=ROLES, default="educator")
    add.add_argument("--name", help="Display name (defaults to username)")
    add.add_argument(
        "--print-only",
        action="store_true",
        help="Print the TOML block instead of writing secrets.toml",
    )

    check = commands.add_parser(
        "check-user", help="Test a password against a saved user"
    )
    check.add_argument("username")

    args = parser.parse_args(argv)
    username = args.username.strip().lower()

    if args.command == "check-user":
        import tomllib

        if not SECRETS_PATH.exists():
            parser.error(f"{SECRETS_PATH} does not exist")

        with SECRETS_PATH.open("rb") as file:
            users = tomllib.load(file).get("auth", {}).get("users", {})

        if username not in users:
            parser.error(
                f"no user '{username}'. Saved users: "
                f"{', '.join(users) or 'none'}"
            )

        password = _prompt_password("Password: ", parser)

        if authenticate(username, password, users):
            print(f"OK: password matches user '{username}'")
            return 0

        print(f"NO MATCH: wrong password for '{username}'")
        return 1

    if not USERNAME_PATTERN.match(username):
        parser.error(
            "username must be 3-32 characters: a-z, 0-9, '_', '.', '-'"
        )

    password = _prompt_password("Password: ", parser)

    if len(password) < 10:
        parser.error("password must be at least 10 characters")

    if _prompt_password("Confirm password: ", parser) != password:
        parser.error("passwords do not match")

    block = _user_block(
        username, args.name or username, args.role, hash_password(password)
    )

    if args.print_only:
        print(block)
        return 0

    _upsert_user(SECRETS_PATH, username, block)
    print(f"Saved user '{username}' ({args.role}) to {SECRETS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
