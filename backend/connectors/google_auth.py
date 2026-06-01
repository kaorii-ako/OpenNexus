from __future__ import annotations
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
]


def authorize_google(data_dir: Path) -> Credentials:
    """Run OAuth2 flow. Opens browser for consent. Saves token to data_dir/gmail_token.json."""
    creds_path = data_dir / "gmail_credentials.json"
    token_path = data_dir / "gmail_token.json"

    if not creds_path.exists():
        raise FileNotFoundError(
            f"Gmail credentials not found at {creds_path}\n"
            "Download OAuth2 credentials from https://console.cloud.google.com/ "
            "and save as ~/.nexus/gmail_credentials.json"
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return creds


# Legacy alias used by old connect stub
run_google_oauth = authorize_google
