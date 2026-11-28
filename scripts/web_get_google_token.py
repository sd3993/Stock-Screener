#!/usr/bin/env python3
"""Google OAuth2 credential manager for this project (Sheets scope only; standard: ~/.common-ai/tools/google.md).

CLI:     python scripts/web_get_google_token.py [--force]
         Generates, verifies or refreshes tokens/google/token.json. With no token (or --force) it prints an authorization
         URL and waits for the browser sign-in on a local callback port; the user signs in, never the agent.
         Prints "Google OAuth token ready at <path> (valid=True)" and exits 0; a missing client secret raises.
Library: from web_get_google_token import get_google_credentials (google_sheets.py loads the token without the
         interactive login and tells the user to run this script when it is missing or can't be refreshed).
"""

import argparse
import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLIENT_SECRET_PATH = r"H:\My Drive\secrets\google\G3_google-api-python-client.json"
TOKEN_PATH = os.path.join(PROJECT_ROOT, "tokens", "google", "token.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_google_credentials(force_reauth: bool = False) -> Credentials:
    """Load, refresh, or interactively generate Google OAuth2 credentials."""
    creds = None
    if not force_reauth and os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if not force_reauth and creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_PATH):
                raise FileNotFoundError(
                    f"Master OAuth client secret not found at {CLIENT_SECRET_PATH}"
                )
            with open(CLIENT_SECRET_PATH, "r", encoding="utf-8-sig") as secret_file:
                client_config = json.load(secret_file)
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=False)

        os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
        with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return creds


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore existing tokens/google/token.json and run interactive OAuth login",
    )
    args = parser.parse_args()

    creds = get_google_credentials(force_reauth=args.force)
    print(f"Google OAuth token ready at {TOKEN_PATH} (valid={creds.valid}).")


if __name__ == "__main__":
    main()
