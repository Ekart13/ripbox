from pathlib import Path
import shutil
import os


def build_base_opts(out_dir: Path) -> dict:
    """
    Build BASE yt-dlp options shared across all export formats.

    This function defines:
    - global yt-dlp behavior
    - YouTube client selection
    - cookie handling strategy
    - JS challenge runtime (Node/EJS)
    - reliability and safety options

    Per-format overrides (mp4 / mkv / mov / mp3) are applied later
    in build_opts_for_format().
    """

    # ------------------------------------------------------------
    # Cookies
    # ------------------------------------------------------------
    # Look for cookies.txt next to this file.
    # If present, it will be used explicitly.
    # Otherwise we fall back to reading cookies from Firefox.
    #
    # This enables:
    # - age-restricted videos
    # - login-required content
    # - region-locked videos (where cookies allow)
    #
    cookie_path = Path(__file__).with_name("cookies.txt")

    # ------------------------------------------------------------
    # Optional YouTube PO token (for some mweb formats)
    # ------------------------------------------------------------
    # This token is NOT required in most cases.
    # It can be provided via environment variable:
    #
    #   export YTDLP_PO_TOKEN="mweb.gvs+TOKEN"
    #
    # Used only if present.
    #
    po_token = os.environ.get("YTDLP_PO_TOKEN", "").strip()

    # ------------------------------------------------------------
    # YouTube extractor configuration
    # ------------------------------------------------------------
    # Avoid the default WEB client because it is often:
    # - SABR-only
    # - broken
    # - throttled
    #
    # We prefer stable non-WEB clients instead.
    #
    extractor_args = {
        "youtube": {
            "player_client": [
                "tv",           # stable, simple responses
                "mweb",         # mobile web client
                "tv_embedded",  # embedded TV client
            ],
        }
    }

    # Inject PO token only if provided
    if po_token:
        extractor_args["youtube"]["po_token"] = [po_token]

    # ------------------------------------------------------------
    # Base yt-dlp options
    # ------------------------------------------------------------
    opts = {
        # --------------------------------------------------------
        # Format selection
        # --------------------------------------------------------
        # Default: best video + best audio, fallback to best
        # Actual container is set per export (mp4/mkv/mov/mp3)
        #
        "format": "bv*+ba/b",

        # Default merge container (overridden later if needed)
        "merge_output_format": "mp4",

        # Output filename template
        # Title + video ID ensures uniqueness and avoids overwrites
        #
        "outtmpl": str(out_dir / "%(title)s [%(id)s].%(ext)s"),

        # --------------------------------------------------------
        # Reliability / stability
        # --------------------------------------------------------
        # Do not abort entire run if a single item fails
        #
        "ignoreerrors": True,

        # Resume partially downloaded files
        #
        "continuedl": True,

        # Retry logic for unstable connections
        #
        "retries": 10,
        "fragment_retries": 10,

        # Download multiple fragments in parallel
        #
        "concurrent_fragment_downloads": 4,

        # Keep .part files until download is complete
        #
        "nopart": False,

        # --------------------------------------------------------
        # Progress / logging
        # --------------------------------------------------------
        # Show progress output (CLI-friendly)
        #
        "noprogress": False,

        # --------------------------------------------------------
        # HTTP / filename safety
        # --------------------------------------------------------
        # Explicit user-agent avoids some platform blocks
        #
        "http_headers": {
            "User-Agent": "Mozilla/5.0"
        },

        # Restrict filenames to safe characters only
        #
        "restrictfilenames": True,

        # Trim very long titles to avoid filesystem limits
        #
        "trim_file_name": 200,

        # --------------------------------------------------------
        # Extractor configuration
        # --------------------------------------------------------
        "extractor_args": extractor_args,

        # --------------------------------------------------------
        # JS challenge solver
        # --------------------------------------------------------
        # Enable EJS (External JavaScript solver)
        # Used when platforms require JS execution
        #
        "remote_components": ["ejs:github"],
    }

    # ------------------------------------------------------------
    # Node.js runtime (portable)
    # ------------------------------------------------------------
    # Instead of hardcoding /usr/bin/node, we locate node
    # via PATH to support:
    # - Linux
    # - macOS
    # - Windows
    #
    node_path = shutil.which("node")
    if node_path:
        opts["js_runtimes"] = {
            "node": {
                "path": node_path
            }
        }

    # ------------------------------------------------------------
    # Cookie handling strategy
    # ------------------------------------------------------------
    if cookie_path.exists():
        # Explicit cookie file takes precedence
        opts["cookiefile"] = str(cookie_path)
    else:
        # Fallback to Firefox browser cookies
        opts["cookiesfrombrowser"] = ("firefox",)

    return opts

def build_opts_for_format(base_opts: dict, export_ext: str) -> dict:
    """
    Customize yt-dlp options for a specific export format.

    This function takes the shared BASE options and applies
    format-specific behavior:

    - mp4 / mkv / mov:
        * download best video + best audio
        * merge streams into the selected container via ffmpeg

    - mp3:
        * download best audio-only stream
        * transcode to MP3 using ffmpeg

    Each export is executed in a separate yt-dlp run to avoid
    format collisions and ensure stability.
    """

    # Create a shallow copy so we don't mutate base options
    opts = dict(base_opts)

    # ------------------------------------------------------------
    # Video formats (container merge)
    # ------------------------------------------------------------
    if export_ext in ("mp4", "mkv", "mov"):
        # Tell ffmpeg which container to merge into
        opts["merge_output_format"] = export_ext

        # Best video + best audio, fallback to best
        opts["format"] = "bv*+ba/b"

        # Force output filename extension to match container
        # Prevents mismatches like .webm inside .mp4 name
        opts["outtmpl"] = opts["outtmpl"].replace("%(ext)s", export_ext)

        # Ensure no audio-only postprocessors leak in
        opts.pop("postprocessors", None)

    # ------------------------------------------------------------
    # Audio-only export (MP3)
    # ------------------------------------------------------------
    elif export_ext == "mp3":
        # Download best available audio stream
        opts["format"] = "bestaudio/best"

        # No container merge for audio-only mode
        opts.pop("merge_output_format", None)

        # IMPORTANT:
        # We intentionally DO NOT force ".mp3" in outtmpl.
        # ffmpeg will generate the final .mp3 filename.
        # Forcing it would result in ".mp3.mp3".
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",  # best VBR quality
            }
        ]

    # ------------------------------------------------------------
    # Unknown format -> safe fallback to MP4
    # ------------------------------------------------------------
    else:
        opts["merge_output_format"] = "mp4"
        opts["format"] = "bv*+ba/b"
        opts["outtmpl"] = opts["outtmpl"].replace("%(ext)s", "mp4")
        opts.pop("postprocessors", None)

    return opts
