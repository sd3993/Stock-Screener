"""The Google Sheet "Stock Screener" through the official Google API Python client (google-api-python-client); not run
by itself. Used by kite_holdings.py and, through wf_lib.sheets_mod(), by run.py, sheet_write.py and sheet_layout.py.

sheets_call(method, body=None, **params): one Sheets API v4 spreadsheets method on SHEET, e.g. 'get',
  'batchUpdate', 'values.batchGet', 'values.batchUpdate', 'values.batchClear'; returns the answer as a dict.
sheet_get(ranges, render): the values of each range (values.batchGet), a list of 2-D lists.
Login: tokens/google/token.json from web_get_google_token.py, loaded and refreshed without any interactive step; a
  missing token or a failed refresh raises SheetError("Google login needed: run python scripts/web_get_google_token.py").
Errors: every failure (login, HTTP, network) raises SheetError; callers print "SHEET NOT UPDATED" or exit 2 as their
  --help says. Google's per-minute quota: an HTTP 429 answer is retried after 65 seconds, up to 3 times.
Test override: env SHEETS_STUB=<path to a .py file> whose call(method, params, body) answers instead of Google.
"""
import os, time

SHEET = '1yBV2fZiIR9xgZ3r-5feDKF_urqXspkPLLG9wPDoPtDU'
_SERVICE = None


class SheetError(Exception):
    pass


def _service():
    global _SERVICE
    if _SERVICE is None:
        try:
            from google.auth.exceptions import GoogleAuthError
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from web_get_google_token import SCOPES, TOKEN_PATH
        except ImportError as e:
            raise SheetError(f'Google API libraries missing ({e}); pip install google-api-python-client google-auth '
                             'google-auth-oauthlib')
        need = 'Google login needed: run python scripts/web_get_google_token.py'
        if not os.path.exists(TOKEN_PATH):
            raise SheetError(f'{need} (no token yet)')
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            if not creds.valid:
                if not creds.refresh_token:
                    raise SheetError(f'{need} (token has no refresh token)')
                creds.refresh(Request())
                with open(TOKEN_PATH, 'w', encoding='utf-8') as f:
                    f.write(creds.to_json())
        except (GoogleAuthError, ValueError) as e:
            raise SheetError(f'{need} ({type(e).__name__}: {str(e)[:200]})')
        _SERVICE = build('sheets', 'v4', credentials=creds, cache_discovery=False)
    return _SERVICE


def _stub():
    p = os.environ.get('SHEETS_STUB')
    if not p:
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location('sheets_stub', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sheets_call(method, body=None, **params):
    params = {'spreadsheetId': SHEET, **params}
    stub = _stub()
    if stub:
        return stub.call(method, params, body)
    from googleapiclient.errors import HttpError
    node = _service().spreadsheets()
    *path, name = method.split('.')
    for p in path:
        node = getattr(node, p)()
    kw = dict(params, body=body) if body is not None else params
    for wait in (65, 65, 65, 0):  # Google's per-minute quota (HTTP 429): wait a minute and retry, up to 3 times
        try:
            return getattr(node, name)(**kw).execute()
        except HttpError as e:
            status = getattr(e.resp, 'status', None)
            if status == 429 and wait:
                time.sleep(wait)
                continue
            raise SheetError(f'Sheets API {method} HTTP {status}: {str(e)[:300]}')
        except SheetError:
            raise
        except Exception as e:  # network, auth refresh during the call
            raise SheetError(f'Sheets API {method} failed ({type(e).__name__}: {str(e)[:300]})')


def sheet_get(ranges, render='UNFORMATTED_VALUE'):
    d = sheets_call('values.batchGet', ranges=ranges, valueRenderOption=render)
    return [vr.get('values', []) for vr in d.get('valueRanges', [])]
