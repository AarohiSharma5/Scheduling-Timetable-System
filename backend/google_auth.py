"""Google Sign-In credential verification.

The frontend uses Google Identity Services (GIS) to obtain an ID token
("credential"). We verify it server-side against our OAuth client id and only
trust the claims after verification. If GOOGLE_CLIENT_ID is unset, Google
sign-in is disabled and the API reports it as unconfigured so the UI can fall
back to password-based flows.
"""
import os

GOOGLE_CLIENT_ID = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()


def google_enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID)


def verify_google_credential(credential: str) -> dict:
    """Verify a GIS ID token. Returns claims dict or {"error": "..."}.

    Claims of interest: sub (stable Google account id), email,
    email_verified, name, picture.
    """
    if not google_enabled():
        return {"error": "Google sign-in is not configured on this server"}
    if not credential:
        return {"error": "Missing Google credential"}
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        claims = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ImportError:
        return {"error": "google-auth library is not installed on the server"}
    except ValueError as exc:
        # Covers bad signature, wrong audience, expired token, malformed JWT.
        return {"error": f"Invalid Google credential: {exc}"}

    if not claims.get("email"):
        return {"error": "Google account has no email"}
    if not claims.get("email_verified", False):
        return {"error": "Google account email is not verified"}
    return claims
