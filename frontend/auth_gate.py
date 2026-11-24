"""
Login gate for every dashboard page.

Call require_login() right after st.set_page_config() and before
loading any data. Pages stop rendering until the visitor signs in.
"""

import threading
import time

import streamlit as st

from backend.auth import REVIEWER_ROLES, authenticate

SESSION_KEY = "auth_user"

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 5 * 60


@st.cache_resource
def _failed_attempts():
    # Shared across all browser sessions of this server process,
    # so refreshing the page does not reset the lockout.
    return {"lock": threading.Lock(), "by_user": {}}


def _locked_out_for(username):
    store = _failed_attempts()

    with store["lock"]:
        count, last_failure = store["by_user"].get(username, (0, 0.0))

    remaining = LOCKOUT_SECONDS - (time.time() - last_failure)

    if count >= MAX_FAILED_ATTEMPTS and remaining > 0:
        return int(remaining)

    return 0


def _record_failure(username):
    store = _failed_attempts()

    with store["lock"]:
        count, last_failure = store["by_user"].get(username, (0, 0.0))

        if time.time() - last_failure > LOCKOUT_SECONDS:
            count = 0

        store["by_user"][username] = (count + 1, time.time())


def _clear_failures(username):
    store = _failed_attempts()

    with store["lock"]:
        store["by_user"].pop(username, None)


def _load_users():
    try:
        users = st.secrets["auth"]["users"]
    except (KeyError, FileNotFoundError):
        return {}

    return {name.lower(): dict(record) for name, record in users.items()}


def _logout():
    st.session_state.pop(SESSION_KEY, None)


def _render_login_form(users):
    st.title("🎓 Coursera Intelligence Platform")
    st.subheader("Sign in")

    if not users:
        st.error(
            "No users are configured. In a terminal opened at the "
            "project root, run this command and enter a password "
            "(10+ characters) when prompted:"
        )
        st.code(
            '.venv\\Scripts\\python.exe -m backend.auth add-user admin '
            '--role admin --name "Admin"',
            language="powershell"
        )
        st.caption(
            "Then refresh this page. The command must print "
            "\"Saved user 'admin'\"; if it shows an error, the user "
            "was not created."
        )
        return

    with st.form("login_form"):
        username = st.text_input("Username", autocomplete="username")
        password = st.text_input(
            "Password", type="password", autocomplete="current-password"
        )
        submitted = st.form_submit_button("Sign in", type="primary")

    if not submitted:
        return

    username = username.strip().lower()

    if not username or not password:
        st.warning("Enter your username and password.")
        return

    wait = _locked_out_for(username)

    if wait:
        st.error(
            f"Too many failed attempts. Try again in "
            f"{wait // 60 + 1} minute(s)."
        )
        return

    user = authenticate(username, password, users)

    if user is None:
        _record_failure(username)
        st.error("Invalid username or password.")
        return

    _clear_failures(username)
    st.session_state[SESSION_KEY] = user
    st.rerun()


def require_login():
    """Return the signed-in user, or show the login form and stop."""
    user = st.session_state.get(SESSION_KEY)
    users = _load_users()

    # Sign out users who were removed from secrets.toml
    if user is not None and user["username"] not in users:
        _logout()
        user = None

    if user is None:
        _render_login_form(users)
        st.stop()

    # "Signed in as" and "Sign out" live in the top navbar
    # (frontend/ui/components.py navbar()).
    return user


def current_user():
    """The signed-in user's profile, or None. Does not enforce login."""
    return st.session_state.get(SESSION_KEY)


def sign_out():
    """Button callback that ends the session."""
    _logout()


def can_review(user):
    return user["role"] in REVIEWER_ROLES
