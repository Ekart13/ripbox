from pathlib import Path
import shutil
import os


def build_base_opts(out_dir: Path) -> dict:
    """
    Build BASE yt-dlp options (shared for all formats).
    """
    cookie_path = Path(__file__).with_name("cookies.txt")

    po_token = os.environ.get("YTDLP_PO_TOKEN", "").strip()

    extractor_args = {
        "youtube": {
            "player_client": ["tv", "mweb", "tv_embedded"],
        }
    }
    if po_token:
        extractor_args["youtube"]["po_token"] = [po_token]

    opts = {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": str(out_dir / "%(title)s [%(id)s].%(ext)s"),

        "noprogress": False,
        "ignoreerrors": True,
        "continuedl": True,
        "concurrent_fragment_downloads": 4,
        "retries": 10,
        "fragment_retries": 10,
        "nopart": False,

        "http_headers": {"User-Agent": "Mozilla/5.0"},
        "restrictfilenames": True,
        "trim_file_name": 200,

        "extractor_args": extractor_args,
        "remote_components": ["ejs:github"],
    }

    node_path = shutil.which("node")
    if node_path:
        opts["js_runtimes"] = {"node": {"path": node_path}}

    if cookie_path.exists():
        opts["cookiefile"] = str(cookie_path)
    else:
        opts["cookiesfrombrowser"] = ("firefox",)

    return opts
