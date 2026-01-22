
# ripbox

Universal interactive **video & audio downloader** written in **Python**, powered by **yt-dlp**.

Downloads from **YouTube, X (Twitter), Instagram, TikTok, Facebook**, and many other supported sites — including playlists — with automatic format selection, merging, and audio extraction.

Designed as a **clean Python CLI tool** focused on reliability and real-world yt-dlp behavior (not marketing promises).

---

## Features

- Interactive CLI (no long command-line flags)
- Multiple export formats in a single run:
  - **MP4** (default)
  - **MKV**
  - **MOV** (best-effort)
  - **MP3** (audio-only)
- Best available **video + audio** merge via **ffmpeg**
- Playlist support (when supported by the platform)
- Predictable output location:
  - Always uses the system **Downloads** directory
  - Optional subfolders are created automatically
- Automatic cookie handling:
  - Uses `cookies.txt` if present
  - Falls back to Firefox browser cookies
- Hardened YouTube setup:
  - Avoids the broken WEB client
  - Uses `tv`, `mweb`, `tv_embedded` clients
  - JS challenge solving via **EJS** (Node.js)
  - Optional PO token support for some mweb formats
- Safe filenames + long-title trimming
- Resume support + retry logic

---

## Important Notes About Formats

Not all platforms provide all formats equally.

- **MP4** is the most reliable format across services
- **MKV** usually works where MP4 works
- **MOV** is best-effort:
  - Some platforms (especially YouTube) do not provide MOV-friendly streams
  - MOV export may fail (ffmpeg conversion limitations / container constraints)
- **MP3** works reliably as audio-only extraction

If a format fails for a specific platform, it’s often a **source/container limitation**, not necessarily a bug in ripbox.

---

## Requirements

- **Python** 3.10+
- **ffmpeg**
- **yt-dlp**
- *(Optional)* **Node.js** — only needed for some YouTube JS challenges (EJS)

---

## Installation (Arch Linux)

```bash
sudo pacman -S ffmpeg nodejs
````

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/Ekart13/ripbox.git
cd ripbox

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Usage

### Recommended (installed CLI inside venv)

From inside the virtual environment:

```bash
pip install -e .
ripbox
```

### Direct run (without installing)

```bash
python -m ripbox.cli
```

You will be prompted for:

1. Video or playlist URL
2. Output subfolder (relative to Downloads)
3. Export format(s)

---

## Output Directory Behavior

* **Empty input** → uses `~/Downloads`
* `yt` → `~/Downloads/yt`
* `yt/music` → `~/Downloads/yt/music`

Subfolders are created automatically.

---

## Export Format Selection

```
1 = MP4 (default)
2 = MKV
3 = MOV
4 = MP3 (audio-only)
```

Examples:

* Press **Enter** → MP4
* Type `4` → MP3 only
* Type `1 4` → MP4 and MP3

Each format is processed independently to avoid conflicts.

---

## Cookies & Authentication

Cookie handling is automatic:

1. If `cookies.txt` exists next to the script/package, it is used.
2. Otherwise, cookies are read directly from **Firefox**.

This enables access to:

* Age-restricted content
* Login-required videos
* Region-locked content (where cookies allow)

### Creating `cookies.txt` manually (optional)

In most cases, no manual setup is required.
If downloads fail due to login, age, or region restrictions, you can create `cookies.txt` yourself.

**Method 1: Using yt-dlp (recommended)**

```bash
yt-dlp --cookies-from-browser firefox --cookies cookies.txt
```

This reads cookies from your Firefox profile and saves them to `cookies.txt`.

**Method 2: Browser extension**

You can export cookies using a browser extension such as:

* **Get cookies.txt** (Firefox / Chromium)

Steps:

1. Log in to the website in your browser
2. Export cookies using the extension
3. Save as `cookies.txt`
4. Place it in the project root (same level as `pyproject.toml`)

> Never commit `cookies.txt`.
> It is intentionally ignored via `.gitignore`.

---

## YouTube Notes

YouTube changes frequently:

* The standard WEB client may be broken or SABR-only
* JS challenges may be required
* Some mweb formats require a PO token

ripbox:

* Avoids the WEB client
* Enables **EJS + Node.js** when available
* Supports optional PO token injection

### Optional PO Token

```bash
export YTDLP_PO_TOKEN="mweb.gvs+YOUR_TOKEN_HERE"
```

Only required for specific YouTube formats.

---

## Output Filename Format

Files are saved as:

```
Title [VideoID].ext
```

* Safe filenames enabled
* Title length trimmed automatically
* No overwrites between different export formats

---

## Code Structure

```
ripbox/
  __init__.py
  cli.py          # Main CLI entrypoint (ripbox command)
  formats.py      # Format menu + format selection logic
  ytdlp_opts.py   # yt-dlp base configuration (cookies, extractors, runtimes)
```

---

## Troubleshooting

* **ffmpeg not found** → install `ffmpeg`
* **Node errors** → ensure `node` is in PATH (only needed for some YouTube cases)
* **403 / login errors** → provide cookies
* **Format fails on specific platform** → expected in some cases (try MP4)
* **Playlist item failures** → expected; script continues

---

## Security

* No telemetry
* No background services
* No credentials stored
* Cookies are read locally only

Transparent and auditable by design.

---

## License

MIT License

---

## Author

**Galeb**
GitHub: [https://github.com/Ekart13](https://github.com/Ekart13)


