# ripbox/url_checks.py
from __future__ import annotations

from urllib.parse import urlparse
import socket
import ssl
import urllib.request


def _maybe_youtube_typo(host: str) -> str | None:
    """
    Cheap typo hints for common YouTube mistakes.
    """
    h = (host or "").lower()

    real = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
    if h in real:
        return None

    if "yout" in h and "youtube" not in h:
        return f"Host looks like a typo. Did you mean 'youtube.com' or 'youtu.be'? (got '{host}')"

    return None


def quick_url_check(url: str, timeout_s: float = 3.0) -> tuple[bool, str | None]:
    """
    Fast sanity + reachability checks to avoid spinning yt-dlp/cookies for garbage URLs.
    Conservative: some sites block probes; in that case we allow yt-dlp to decide.
    """
    try:
        p = urlparse(url)
    except Exception:
        return (False, "URL parse failed.")

    if p.scheme not in ("http", "https"):
        return (False, "URL must start with http:// or https://")

    if not p.netloc:
        return (False, "URL is missing host (netloc).")

    host = p.netloc.split("@")[-1].split(":")[0].strip()
    if not host:
        return (False, "URL host is empty.")

    typo_hint = _maybe_youtube_typo(host)
    if typo_hint:
        return (False, typo_hint)

    # DNS check (fast)
    try:
        socket.getaddrinfo(host, 443 if p.scheme == "https" else 80)
    except socket.gaierror:
        return (False, f"Host does not resolve (DNS): '{host}'")

    # Small probe (Range GET) - if it fails, we still usually let yt-dlp try.
    try:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Range": "bytes=0-0",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            code = getattr(resp, "status", None) or 200
            if 200 <= code < 400:
                return (True, None)
            return (False, f"URL responded with HTTP {code}")
    except ssl.SSLError as e:
        return (False, f"SSL error: {e}")
    except Exception:
        # Some platforms block this probe; don't false-negative.
        return (True, None)


def is_networkish_error(err: str | None) -> bool:
    """
    Timeout / DNS / SSL handshake / connect-type failures.
    Cookies won't help -> don't spin cookie sources.
    """
    if not err:
        return False
    s = err.lower()
    needles = [
        "timed out",
        "handshake",
        "name or service not known",
        "temporary failure in name resolution",
        "nodename nor servname provided",
        "connection refused",
        "connection reset",
        "ssl",
        "certificate verify failed",
        "transporterror",
    ]
    return any(n in s for n in needles)


def is_permanent_unavailable_error(err: str | None) -> bool:
    """
    Dead link / removed / private / unavailable.
    Cookies typically won't help -> fail fast.
    """
    if not err:
        return False
    s = err.lower()
    needles = [
        "video unavailable",
        "this video is unavailable",
        "private video",
        "has been removed",
        "video has been removed",
        "does not exist",
        "content is not available",
        "content unavailable",
        "http error 404",
        "unsupported url",
        "url is invalid",
    ]
    return any(n in s for n in needles)
