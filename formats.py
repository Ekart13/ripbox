from typing import List

# ------------------------------------------------------------
# Export format menu
# ------------------------------------------------------------
# Maps numeric user input -> (file extension, human-readable description)
#
# The numeric keys are what the user types in the CLI.
# The extension string is later used to configure yt-dlp output.
#
FORMAT_MENU = {
    1: ("mp4", "Video MP4 (default)"),
    2: ("mkv", "Video MKV"),
    3: ("mov", "Video MOV"),
    4: ("mp3", "Audio MP3 (audio-only)"),
}


def choose_formats(ask) -> List[str]:
    """
    Interactively ask the user which export formats to use.

    Behavior:
    - Displays a numbered list of available formats
    - Accepts multiple selections in one line (e.g. "1 4")
    - Accepts commas or spaces as separators
    - Pressing Enter with no input selects the default format (MP4)
    - Invalid input is ignored safely
    - Duplicate selections are removed
    - Always returns at least one format

    Parameters:
    - ask: a callable used to prompt user input
      (passed in from main code to keep this function testable and decoupled)

    Returns:
    - List[str]: ordered list of selected format extensions
      Example: ["mp4"] or ["mp4", "mp3"]
    """

    # --------------------------------------------------------
    # Print available formats to the user
    # --------------------------------------------------------
    print("\nExport formats:")

    # Sort keys so menu order is predictable (1, 2, 3, 4)
    for k in sorted(FORMAT_MENU.keys()):
        ext, desc = FORMAT_MENU[k]

        # Mark MP4 as the default choice in the UI
        default_tag = " (default)" if k == 1 else ""

        print(f"  {k}) {desc}{default_tag}")

    # --------------------------------------------------------
    # Read user input
    # --------------------------------------------------------
    raw = ask(
        "→ Choose format(s) by number (e.g. 1 4). Enter = default MP4: "
    )

    # If user just presses Enter, return the default format
    if not raw:
        return ["mp4"]

    # --------------------------------------------------------
    # Parse user input
    # --------------------------------------------------------
    picked: List[str] = []

    # Replace commas with spaces so both "1,4" and "1 4" work
    for token in raw.replace(",", " ").split():
        try:
            # Convert token to integer menu key
            n = int(token)
        except ValueError:
            # Ignore anything that is not a number
            continue

        # Check if the number exists in FORMAT_MENU
        if n in FORMAT_MENU:
            ext = FORMAT_MENU[n][0]

            # Avoid duplicates while preserving order
            if ext not in picked:
                picked.append(ext)

    # --------------------------------------------------------
    # Final safety fallback
    # --------------------------------------------------------
    # If user entered only invalid input, fall back to default MP4
    #
    return picked if picked else ["mp4"]
