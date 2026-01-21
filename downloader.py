#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Universal video downloader powered by yt-dlp.

What it does:
- Prompts for a URL and a target folder.
- Prompts for export format(s):
  - 1 = MP4 (default on Enter)
  - 2 = MKV
  - 3 = MOV
  - 4 = MP3 (audio-only)
  - You can type multiple like: 1 4  (downloads both mp4 and mp3)
- Creates the target folder if it doesn't exist.
- Downloads best available quality (best video + best audio when possible),
  then merges using ffmpeg.
- Works for single videos and playlists (when supported by the site).
- Uses cookies automatically:
  - If a `cookies.txt` file exists next to this script, it will use it.
  - Otherwise, it will read cookies from your Firefox profile.

YouTube notes (current reality):
- WEB client can be SABR-only / broken depending on rollout.
- JS challenge solving can be required -> we enable EJS + node runtime.
- mweb may require a PO token for some https formats (optional env var YTDLP_PO_TOKEN).
"""

from __future__ import annotations

from formats import choose_formats
from ytdlp_opts import build_base_opts
from pathlib import Path
import shutil
from yt_dlp import YoutubeDL


# ----------------------------
# Helpers
# ----------------------------

def ask(prompt: str) -> str:
    """Read user input safely (handles Ctrl+C / Ctrl+D)."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""

def resolve_output_dir(user_input: str) -> Path:
    """
    Resolve output directory relative to ~/Downloads.
    Empty input => ~/Downloads
    Subfolders allowed (e.g. yt/music)
    Absolute paths are rejected.
    """
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




def build_opts_for_format(base_opts: dict, export_ext: str) -> dict:
    """
    Return a COPY of base_opts customized for the requested export_ext.
    We run yt-dlp once per export format (most stable, avoids conflicts).
    """
    opts = dict(base_opts)  # shallow copy is enough (we'll replace nested keys we touch)

    # Make sure different exports don't overwrite each other:
    # For video exports, final ext comes from merge_output_format.
    # For mp3, final ext comes from postprocessor.
    if export_ext in ("mp4", "mkv", "mov"):
        opts["merge_output_format"] = export_ext
        opts["format"] = "bv*+ba/b"
        # Force filename extension to be the container we asked for
        opts["outtmpl"] = opts["outtmpl"].replace("%(ext)s", export_ext)

        # No special postprocessing required beyond merge (ffmpeg does it)
        opts.pop("postprocessors", None)

    elif export_ext == "mp3":
        # Audio-only best available, then transcode to mp3
        opts["format"] = "bestaudio/best"
        opts.pop("merge_output_format", None)

        # Ensure output ends with .mp3
        opts["outtmpl"] = opts["outtmpl"].replace("%(ext)s", "mp3")

        # Extract audio via ffmpeg
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",  # best VBR
            }
        ]

    else:
        # Unknown -> fallback to mp4
        opts["merge_output_format"] = "mp4"
        opts["format"] = "bv*+ba/b"
        opts["outtmpl"] = opts["outtmpl"].replace("%(ext)s", "mp4")
        opts.pop("postprocessors", None)

    return opts
# ----------------------------
# Main
# ----------------------------

def main() -> None:
    print("=== Universal video downloader (YouTube / X / Instagram / TikTok / Facebook) ===")
    print("Empty URL -> exit.\n")

    while True:
        url = ask("→ Paste URL: ")
        if not url:
            print("Done. Bye!")
            return

        target = ask("→ Output subfolder (relative to Downloads, empty = Downloads): ")

        try:
            out_dir = resolve_output_dir(target)
        except ValueError as e:
            print(f"❌ {e}")
            continue

        print(f"[i] Saving to: {out_dir}")

        exports = choose_formats(ask)
        print(f"[i] Export(s): {', '.join(exports)}")

        base_opts = build_base_opts(out_dir)

        any_fail = False
        for export_ext in exports:
            print(f"\n=== Export: {export_ext} ===")
            ydl_opts = build_opts_for_format(base_opts, export_ext)

            try:
                with YoutubeDL(ydl_opts) as ydl:
                    result = ydl.download([url])  # 0 on success
                    if result == 0:
                        print(f"✅ Done: {export_ext}")
                    else:
                        any_fail = True
                        print(f"⚠️ Some items failed for export {export_ext}. Check logs above.")
            except Exception as e:
                any_fail = True
                print(f"❌ Error on export {export_ext}: {e}")

        if any_fail:
            print("\n⚠️ Finished with some errors.\n")
        else:
            print("\n✅ All exports complete.\n")


if __name__ == "__main__":
    main()
