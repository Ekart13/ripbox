#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from .input_sources import choose_input

from .formats import choose_formats
from .ytdlp_opts import build_base_opts, build_opts_for_format, cookie_sources
from .url_checks import quick_url_check, is_networkish_error, is_permanent_unavailable_error


# ----------------------------
# CLI input
# ----------------------------
def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""
 # ----------------------------
# tct file read
# ----------------------------       
def read_text_from_prompt() -> str:
    print("→ Paste text / URLs (empty line to start):")
    lines: list[str] = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line)
    return "\n".join(lines)


def read_text_from_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found in project root.")
    return path.read_text(encoding="utf-8", errors="ignore")


# ----------------------------
# Output directory
# ----------------------------
def resolve_output_dir(user_input: str) -> Path:
    base = Path.home() / "Downloads"
    if not user_input:
        out_dir = base
    else:
        sub = Path(user_input)
        if sub.is_absolute():
            raise ValueError("Absolute paths are not allowed. Use subfolders only.")
        out_dir = base / sub

    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


# ----------------------------
# yt-dlp logger capture
# ----------------------------
class CaptureLogger:
    def __init__(self) -> None:
        self.last_error: str | None = None

    def debug(self, msg: str) -> None:
        # yt-dlp često šalje normalne poruke kao "debug" koje počinju s "[youtube]"
        if msg:
            print(msg)

    def warning(self, msg: str) -> None:
        if msg:
            print(f"WARNING: {msg}")

    def error(self, msg: str) -> None:
        self.last_error = msg
        if msg:
            print(f"ERROR: {msg}")


def _existing_path(p: str | None) -> str | None:
    if not p:
        return None
    try:
        pp = Path(p)
        return str(pp) if pp.exists() else None
    except Exception:
        return None


def _collect_candidate_outputs(info: dict, ydl: YoutubeDL) -> list[str]:
    """
    Try multiple known places where yt-dlp stores the final output path.
    We treat download as success ONLY if at least one candidate exists on disk.
    """
    candidates: list[str] = []

    # Common: final path stored here
    candidates.append(info.get("_filename"))

    # prepare_filename usually yields the output path for the main file
    try:
        candidates.append(ydl.prepare_filename(info))
    except Exception:
        pass

    # Sometimes yt-dlp keeps requested_downloads with filepath entries
    rd = info.get("requested_downloads")
    if isinstance(rd, list):
        for item in rd:
            if isinstance(item, dict):
                candidates.append(item.get("filepath"))
                candidates.append(item.get("filename"))

    # Playlist case: entries may contain filenames
    entries = info.get("entries")
    if isinstance(entries, list):
        for e in entries[:5]:  # don't blow up on huge playlists
            if isinstance(e, dict):
                candidates.append(e.get("_filename"))
                try:
                    candidates.append(ydl.prepare_filename(e))
                except Exception:
                    pass

    # Dedup + keep only existing
    seen: set[str] = set()
    existing: list[str] = []
    for c in candidates:
        ec = _existing_path(c)
        if ec and ec not in seen:
            seen.add(ec)
            existing.append(ec)

    return existing


# ----------------------------
# yt-dlp wrapper (success + real error string)
# ----------------------------
def run_download(url: str, ydl_opts: dict) -> tuple[bool, str | None]:
    cf = ydl_opts.get("cookiefile")
    cb = ydl_opts.get("cookiesfrombrowser")
    print(f"[dbg] cookiefile={cf!r} cookiesfrombrowser={cb!r}")

    logger = CaptureLogger()

    opts = dict(ydl_opts)
    opts["logger"] = logger

    # CRITICAL: do NOT let yt-dlp silently "succeed" on errors
    opts["ignoreerrors"] = False
    # vrati verbose output
    opts["quiet"] = False
    opts["no_warnings"] = False
    #max verbose
    #opts["verbose"] = True


    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # If yt-dlp returned nothing, that's not success
            if not isinstance(info, dict):
                return (False, logger.last_error or "No info extracted (download did not complete).")

            existing = _collect_candidate_outputs(info, ydl)
            if existing:
                # Real success: at least one output file exists
                return (True, None)

            # No file created => treat as failure (even if yt-dlp didn't raise)
            return (
                False,
                logger.last_error
                or "No output file was created (treating as failure).",
            )

    except DownloadError as e:
        return (False, logger.last_error or str(e))
    except Exception as e:
        return (False, logger.last_error or str(e))


def build_cookie_attempts(base_with_cookies: dict) -> list[tuple[str, dict]]:
    attempts: list[tuple[str, dict]] = []

    if "cookiefile" in base_with_cookies:
        attempts.append(("cookiefile", dict(base_with_cookies)))
        return attempts

    for src in cookie_sources():
        o = dict(base_with_cookies)
        o["cookiesfrombrowser"] = src
        attempts.append((f"browser:{src[0]}", o))

    return attempts

def normalize_url(raw: str) -> str:
    s = (raw or "").strip()

    # If terminal escape junk or other prefix exists, salvage first http(s)
    for proto in ("https://", "http://"):
        idx = s.find(proto)
        if idx > 0:
            s = s[idx:]
            break

    # Strip common trailing punctuation from copy/paste
    s = s.rstrip(" \t\r\n.!,);]>'\"")

    return s

def main() -> None:
    print("=== Universal video downloader (YouTube / X / Instagram / TikTok / Facebook) ===")
    print("Empty input -> exit.\n")

    last_out_dir: Path | None = None
    last_exports: list[str] | None = None

    while True:
        # ---------------------------------------------------------
        # Input source + URL extraction
        # ---------------------------------------------------------
        inp = choose_input(ask)

        if getattr(inp, "reset", False):
            last_out_dir = None
            last_exports = None
            print("[i] Reset done. Next run will ask for folder and format again.\n")
            continue

        if inp.source == "file" and not inp.text:
            print("❌ links.txt not found in project root.")
            continue

        if not inp.text:
            print("Done. Bye!")
            return

        if not inp.urls:
            print("❌ No URLs found in input.")
            continue

        urls = inp.urls
        total = len(urls)
        print(f"[i] Found {total} URL(s).")

        # ---------------------------------------------------------
        # Output dir (sticky)
        # ---------------------------------------------------------
        if last_out_dir is None:
            target = ask("→ Output subfolder (relative to Downloads, empty = Downloads): ")
            try:
                last_out_dir = resolve_output_dir(target)
            except ValueError as e:
                print(f"❌ {e}")
                last_out_dir = None
                continue
            print(f"[i] Saving to: {last_out_dir}")
        else:
            print(f"[i] Using previous folder: {last_out_dir}")

        out_dir = last_out_dir

        # ---------------------------------------------------------
        # Exports (sticky)
        # ---------------------------------------------------------
        if last_exports is None:
            last_exports = choose_formats(ask)
            print(f"[i] Export(s): {', '.join(last_exports)}")
        else:
            print(f"[i] Using previous export(s): {', '.join(last_exports)}")

        exports = last_exports

        # ---------------------------------------------------------
        # Batch state (cookies lock stays per batch-run)
        # ---------------------------------------------------------
        chosen_cookie_mode: str | None = None
        chosen_cookie_base: dict | None = None

        ok_urls: list[str] = []
        fail_urls: list[str] = []
        invalid_urls: list[tuple[str, str]] = []  # (url, reason)

        # ---------------------------------------------------------
        # Bulk loop
        # ---------------------------------------------------------
        for idx, url in enumerate(urls, start=1):
            print(f"\n=== [{idx}/{total}] URL ===\n{url}")

            ok_url, why = quick_url_check(url)
            if not ok_url:
                print(f"❌ Invalid/unreachable URL (fast check): {why}")
                invalid_urls.append((url, why))
                continue

            url_failed = False

            for export_ext in exports:
                print(f"\n--- Export: {export_ext} ---")

                # 1) Try without cookies
                base_no = build_base_opts(out_dir, enable_cookies=False)
                ydl_no = build_opts_for_format(base_no, export_ext)

                ok0, err0 = run_download(url, ydl_no)
                if ok0:
                    print("[i] Cookies: none")
                    print(f"✅ Done: {export_ext}")
                    continue

                # fail-fast cases
                if is_permanent_unavailable_error(err0):
                    url_failed = True
                    print(f"❌ Failed: {export_ext}: {err0}")
                    print("[i] Link/content appears unavailable — skipping cookie attempts.")
                    continue

                if is_networkish_error(err0):
                    url_failed = True
                    print(f"❌ Failed: {export_ext}: {err0}")
                    print("[i] Looks like a network/SSL/DNS issue — skipping cookie attempts.")
                    continue

                # 2) Reuse locked cookie mode if we have one
                if chosen_cookie_base is not None:
                    ydl_locked = build_opts_for_format(chosen_cookie_base, export_ext)
                    ok1, err1 = run_download(url, ydl_locked)
                    if ok1:
                        print(f"✅ Done ({chosen_cookie_mode}): {export_ext}")
                        continue

                    if is_permanent_unavailable_error(err1) or is_networkish_error(err1):
                        url_failed = True
                        print(f"❌ Failed: {export_ext}: {err1}")
                        print("[i] Skipping further cookie attempts.")
                        continue

                # 3) Try cookie sources (and lock the first one that works)
                base_yes = build_base_opts(out_dir, enable_cookies=True)
                attempts = build_cookie_attempts(base_yes)

                success = False
                last_err: str | None = err0

                for mode, cookie_base in attempts:
                    ydl_try = build_opts_for_format(cookie_base, export_ext)
                    ok2, err2 = run_download(url, ydl_try)
                    if ok2:
                        chosen_cookie_mode = mode
                        chosen_cookie_base = cookie_base
                        print(f"[i] Cookies mode locked: {mode}")
                        print(f"✅ Done ({mode}): {export_ext}")
                        success = True
                        break

                    last_err = err2

                    if is_permanent_unavailable_error(err2) or is_networkish_error(err2):
                        break

                if not success:
                    url_failed = True
                    if last_err:
                        print(f"❌ Failed: {export_ext}: {last_err}")
                    else:
                        print(f"❌ Failed: {export_ext}")

            if url_failed:
                fail_urls.append(url)
            else:
                ok_urls.append(url)

        # ---------------------------------------------------------
        # Summary
        # ---------------------------------------------------------
        print("\n=== Summary ===")
        print(f"✅ OK: {len(ok_urls)}/{total}")
        print(f"❌ Failed: {len(fail_urls)}/{total}")
        print(f"⚠️ Invalid: {len(invalid_urls)}/{total}")

        if invalid_urls:
            print("\nInvalid URLs:")
            for u, reason in invalid_urls:
                print(f"- {u}\n  -> {reason}")

        if fail_urls:
            print("\nFailed URLs (copy/paste):")
            for u in fail_urls:
                print(f"- {u}")

        print("\n✅ Batch complete.\n")

if __name__ == "__main__":
    main()
