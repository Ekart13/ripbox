from typing import List

FORMAT_MENU = {
    1: ("mp4", "Video MP4 (default)"),
    2: ("mkv", "Video MKV"),
    3: ("mov", "Video MOV"),
    4: ("mp3", "Audio MP3 (audio-only)"),
}


def choose_formats(ask) -> List[str]:
    """
    Ask user which formats to export.
    - Enter => default mp4
    - multiple choices allowed: "1 4"
    Returns list like ["mp4", "mp3"] in the given order (deduped).
    """
    print("\nExport formats:")
    for k in sorted(FORMAT_MENU.keys()):
        ext, desc = FORMAT_MENU[k]
        default_tag = " (default)" if k == 1 else ""
        print(f"  {k}) {desc}{default_tag}")

    raw = ask("→ Choose format(s) by number (e.g. 1 4). Enter = default MP4: ")
    if not raw:
        return ["mp4"]

    picked: List[str] = []
    for token in raw.replace(",", " ").split():
        try:
            n = int(token)
        except ValueError:
            continue
        if n in FORMAT_MENU:
            ext = FORMAT_MENU[n][0]
            if ext not in picked:
                picked.append(ext)

    return picked if picked else ["mp4"]
