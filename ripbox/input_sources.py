# ripbox/input_sources.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


# Regex: pokupi http/https linkove do prvog whitespace-a ili navodnika
_URL_RE = re.compile(r"https?://[^\s<>\"]+")


def normalize_url(raw: str) -> str:
    """
    Make pasted URLs robust:
    - trim whitespace
    - salvage if junk exists before http(s)
    - strip trailing punctuation from copy/paste (.,); etc)
    - if multiple URLs are stuck together, keep only the first one
    """
    s = (raw or "").strip()

    # salvage first http(s) if there's junk before it
    first_https = s.find("https://")
    first_http = s.find("http://")
    firsts = [i for i in (first_https, first_http) if i != -1]
    if firsts:
        s = s[min(firsts):]

    # cut at second url if pasted without whitespace
    second_https = s.find("https://", 1)
    second_http = s.find("http://", 1)
    seconds = [i for i in (second_https, second_http) if i != -1]
    if seconds:
        s = s[: min(seconds)]

    # strip common trailing punctuation
    s = s.rstrip(" \t\r\n.!,);]>'\"")

    return s


def extract_urls(text: str) -> list[str]:
    """
    Extract all http(s) URLs from arbitrary text (multi-line, prose, comments, etc).
    - ignores comment-only lines (starting with #)
    - strips trailing punctuation
    - dedups while preserving order
    """
    if not text:
        return []

    lines = text.splitlines()
    filtered = []
    for ln in lines:
        if ln.lstrip().startswith("#"):
            continue
        filtered.append(ln)

    blob = "\n".join(filtered)

    found = _URL_RE.findall(blob)
    out: list[str] = []
    seen: set[str] = set()

    for u in found:
        nu = normalize_url(u)
        if not nu:
            continue
        if nu in seen:
            continue
        seen.add(nu)
        out.append(nu)

    return out


def read_text_from_prompt() -> str:
    """
    Multi-line paste mode. Empty line starts processing.
    """
    print("→ Paste text / URLs (empty line to start):")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            line = ""
        if not line.strip():
            break
        lines.append(line)
    return "\n".join(lines).strip()


def read_text_from_file(path: Path) -> str:
    """
    Read text blob from file (UTF-8, ignore errors).
    """
    return path.read_text(encoding="utf-8", errors="ignore").strip()


@dataclass(frozen=True)
class InputResult:
    source: str           # "paste" or "file"
    text: str
    urls: list[str]
    reset: bool = False

def choose_input(ask) -> InputResult:
    """
    Paste anything containing URLs.
    Press ENTER immediately to load links.txt from project root.
    """
    print("Paste URL(s) or text containing links.")
    print("(Press ENTER to read from links.txt, type 'reset' or 'r' to re-pick folder/format)")
    first = ask("→ ")
    cmd = first.strip().lower()
    if cmd in {"reset", "r"}:
        return InputResult("cmd", first, [], reset=True)

    # ENTER = file mode
    if not first.strip():
        project_root = Path(__file__).resolve().parent.parent
        links_path = project_root / "links.txt"
        if not links_path.exists():
            return InputResult("file", "", [])
        text = read_text_from_file(links_path)
        urls = extract_urls(text)
        return InputResult("file", text, urls)

    # otherwise paste mode (multi-line)
    lines = [first]
    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        if not line.strip():
            break
        lines.append(line)

    text = "\n".join(lines).strip()
    urls = extract_urls(text)
    return InputResult("paste", text, urls)

