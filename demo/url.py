"""Pure URL normalization for fictional, reserved .example hosts only."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def normalize_url(raw: str) -> str:
    try:
        parts = urlsplit((raw or "").strip())
        host = parts.hostname
        if (
            parts.scheme.lower() != "https" or not host or not host.endswith(".example")
            or parts.username or parts.password or parts.port is not None
            or len(raw) > 500
        ):
            return ""
        query = urlencode(
            [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if key.casefold() != "ref" and not key.casefold().startswith("utm_")]
        )
        return urlunsplit(("https", host.lower(), parts.path.rstrip("/"), query, ""))
    except (ValueError, UnicodeError):
        return ""
