#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from yt_dlp import YoutubeDL

from .formats import choose_formats
from .ytdlp_opts import build_base_opts, build_opts_for_format


# ----------------------------
# Helpers (CLI input + output dir)
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
    Absolute paths are rejected (safety + predictable behavior).
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


# ----------------------------
# Main (CLI program loop)
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
