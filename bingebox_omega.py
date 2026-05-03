#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║        BingeBox Omega — ALL-IN-ONE Python Dev Tool          ║
║        Roku v3.0  |  python bingebox_omega.py               ║
╠══════════════════════════════════════════════════════════════╣
║  • Auto-installs Node.js deps (npm install)                 ║
║  • Compiles BrighterScript  (npm run build / bsc)           ║
║  • Packages .zip for Roku sideload                          ║
║  • Deploys to Roku over LAN  (HTTP multipart upload)        ║
║  • TMDB API live tester                                     ║
║  • Project linter / inspector                               ║
║  • Streaming server URL builder                             ║
║  • Manifest editor                                          ║
║  • GitHub pull (git pull)                                   ║
║  • Full pipeline  (pull → install → build → zip → deploy)  ║
╚══════════════════════════════════════════════════════════════╝

Zero pip dependencies — pure Python 3.10+ stdlib only.
Run:  python bingebox_omega.py
      python bingebox_omega.py C:\\path\\to\\BingeBox-Roku-v2
"""

import sys, os, re, json, zipfile, shutil, time, subprocess
import urllib.request, urllib.parse, urllib.error
import http.client, mimetypes
from pathlib import Path
from datetime import datetime

# ── ANSI colours (Windows 10+ VT100) ─────────────────────────────────────────
if sys.platform == "win32":
    os.system("")          # enable VT sequences

R   = "\033[91m"
G   = "\033[92m"
Y   = "\033[93m"
C   = "\033[96m"
M   = "\033[95m"
W   = "\033[97m"
DG  = "\033[90m"
B   = "\033[94m"
RST = "\033[0m"
BOLD= "\033[1m"

def clr(t, c):   return f"{c}{t}{RST}"
def ok(m):       print(f"  {clr('✓', G)} {m}")
def err(m):      print(f"  {clr('✗', R)} {m}")
def warn(m):     print(f"  {clr('!', Y)} {m}")
def step(m):     print(f"\n  {clr('▶', C)} {clr(m, W)}")
def info(m):     print(f"    {clr(m, DG)}")
def sep(ch="─"): print(f"  {clr(ch*52, DG)}")
def blank():     print()

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

TMDB_KEY_DEFAULT = "15d2ea6d0dc1d476efbca3eba2b9bbfb"
TMDB_BASE        = "https://api.themoviedb.org/3"

SERVERS = [
    {"id":"vidlink",   "name":"VidLink Pro",  "badge":"⚡",
     "movieBase":"https://vidlink.pro/movie/",              "tvBase":"https://vidlink.pro/tv/"},
    {"id":"vidsrcpro", "name":"VidSrc PRO",   "badge":"🔥",
     "movieBase":"https://vidsrc.pro/embed/movie/",         "tvBase":"https://vidsrc.pro/embed/tv/"},
    {"id":"videasy",   "name":"Videasy",       "badge":"🎬",
     "movieBase":"https://player.videasy.net/movie/",       "tvBase":"https://player.videasy.net/tv/"},
    {"id":"vidsrccc",  "name":"VidSrc CC",     "badge":"🌐",
     "movieBase":"https://vidsrc.cc/v2/embed/movie/",       "tvBase":"https://vidsrc.cc/v2/embed/tv/"},
    {"id":"autoembed", "name":"AutoEmbed",     "badge":"🤖",
     "movieBase":"https://player.autoembed.cc/embed/movie/","tvBase":"https://player.autoembed.cc/embed/tv/"},
    {"id":"2embed",    "name":"2Embed",        "badge":"✨",
     "movieBase":"https://www.2embed.cc/embed/",            "tvBase":"https://www.2embed.cc/embedtv/"},
    {"id":"vidsrcme",  "name":"VidSrc.ME",     "badge":"💾",
     "movieBase":"https://vidsrc.me/embed/movie?tmdb=",     "tvBase":"https://vidsrc.me/embed/tv?tmdb="},
]

# ═══════════════════════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════════════════════

def banner():
    os.system("cls" if sys.platform == "win32" else "clear")
    print(clr("""
  ██████╗ ██╗███╗   ██╗ ██████╗ ███████╗██████╗  ██████╗ ██╗  ██╗
  ██╔══██╗██║████╗  ██║██╔════╝ ██╔════╝██╔══██╗██╔═══██╗╚██╗██╔╝
  ██████╔╝██║██╔██╗ ██║██║  ███╗█████╗  ██████╔╝██║   ██║ ╚███╔╝
  ██╔══██╗██║██║╚██╗██║██║   ██║██╔══╝  ██╔══██╗██║   ██║ ██╔██╗
  ██████╔╝██║██║ ╚████║╚██████╔╝███████╗██████╔╝╚██████╔╝██╔╝ ██╗
  ╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝""", R))
    print(clr("  OMEGA  ROKU v3.0  —  All-In-One Python Dev Tool", Y))
    print(clr("  ──────────────────────────────────────────────────", DG))
    blank()

# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════════

def find_project() -> Path | None:
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if (p / "package.json").exists():
            return p.resolve()

    candidates = [
        Path.cwd() / "BingeBox-Roku-v2",
        Path.cwd() / "BingeBox_Omega_Roku_v3",
        Path.cwd(),
        Path.home() / "Desktop"  / "BingeBox-Roku-v2",
        Path.home() / "Downloads"/ "BingeBox-Roku-v2",
        Path.home() / "Documents"/ "BingeBox-Roku-v2",
        Path.home() / "Desktop"  / "Reoi" / "BingeBox-Roku-v2",
        Path.home() / "Downloads"/ "Reoi" / "BingeBox-Roku-v2",
    ]
    for c in candidates:
        if (c / "package.json").exists():
            return c.resolve()
    return None

def prompt_project() -> Path | None:
    warn("Project folder not found automatically.")
    p = input("  Enter full path to BingeBox-Roku-v2 (or Enter to skip): ").strip().strip('"')
    if p and (Path(p) / "package.json").exists():
        return Path(p).resolve()
    warn("No valid project path. Some features disabled.")
    return None

def read_config(root: Path) -> dict:
    cfg = root / "src" / "source" / "Services" / "Config.bs"
    result = {"tmdb_key": TMDB_KEY_DEFAULT}
    if not cfg.exists():
        return result
    text = cfg.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'TMDB_KEY:\s*"([a-f0-9]+)"', text)
    if m:
        result["tmdb_key"] = m.group(1)
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def check_node() -> bool:
    step("Checking Node.js / npm...")
    node = shutil.which("node")
    npm  = shutil.which("npm")
    if not node:
        err("Node.js not found!")
        warn("Install from https://nodejs.org  (LTS version)")
        warn("Or via winget:  winget install OpenJS.NodeJS.LTS")
        return False
    ver = subprocess.check_output(["node", "--version"], text=True).strip()
    ok(f"Node.js {ver}")
    if not npm:
        err("npm not found (should ship with Node.js)")
        return False
    nver = subprocess.check_output(["npm", "--version"], text=True).strip()
    ok(f"npm v{nver}")
    return True

def check_git() -> bool:
    return shutil.which("git") is not None

# ═══════════════════════════════════════════════════════════════════════════════
# NPM INSTALL
# ═══════════════════════════════════════════════════════════════════════════════

def npm_install(root: Path) -> bool:
    step("Installing npm dependencies (brighterscript + roku-deploy)...")
    if not check_node():
        return False
    result = subprocess.run(
        ["npm", "install"],
        cwd=root,
        capture_output=False,   # let output stream live
        text=True
    )
    if result.returncode != 0:
        err("npm install FAILED")
        return False
    ok("Dependencies installed")
    return True

# ═══════════════════════════════════════════════════════════════════════════════
# COMPILE  (bsc via npm run build)
# ═══════════════════════════════════════════════════════════════════════════════

def compile_project(root: Path) -> bool:
    step("Compiling BrighterScript (bsc)...")

    node_modules = root / "node_modules"
    if not node_modules.exists():
        warn("node_modules not found — running npm install first...")
        if not npm_install(root):
            return False

    # Try npm run build first
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=root,
        text=True,
        capture_output=False
    )

    if result.returncode != 0:
        # Fallback: try npx bsc directly
        warn("npm run build failed — trying npx bsc directly...")
        result2 = subprocess.run(
            ["npx", "bsc"],
            cwd=root,
            text=True,
            capture_output=False
        )
        if result2.returncode != 0:
            err("Compilation FAILED. Check BrightScript syntax errors above.")
            return False

    staging = root / "out" / ".roku-deploy-staging"
    if staging.exists():
        file_count = sum(1 for _ in staging.rglob("*") if _.is_file())
        ok(f"Compiled successfully → out/.roku-deploy-staging/ ({file_count} files)")
    else:
        warn("Staging dir not created — build may have partially failed.")
    return True

# ═══════════════════════════════════════════════════════════════════════════════
# PACKAGE ZIP
# ═══════════════════════════════════════════════════════════════════════════════

def package_zip(root: Path, use_staging=True) -> Path | None:
    step("Packaging .zip for Roku sideload...")

    ts = datetime.now().strftime("%Y%m%d-%H%M")
    zip_name = f"BingeBox-Omega-v3-{ts}.zip"
    zip_path = root / zip_name

    staging = root / "out" / ".roku-deploy-staging"
    src_dir  = root / "src"

    if use_staging and staging.exists():
        base = staging
        ok(f"Using compiled staging dir")
    elif src_dir.exists():
        base = src_dir
        warn("Staging dir not found — packaging raw src/ (uncompiled)")
    else:
        err("Neither staging nor src/ found. Run compile first.")
        return None

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(base.rglob("*")):
            if f.is_file():
                arc = f.relative_to(base)
                zf.write(f, arc)
                info(f"  + {arc}")

    size_kb = zip_path.stat().st_size // 1024
    ok(f"Package ready: {zip_path.name}  ({size_kb} KB)")
    info(f"Full path: {zip_path}")
    return zip_path

# ═══════════════════════════════════════════════════════════════════════════════
# DEPLOY TO ROKU  (HTTP multipart — no roku-deploy CLI needed)
# ═══════════════════════════════════════════════════════════════════════════════

def deploy_to_roku(zip_path: Path, roku_ip: str, roku_pass: str) -> bool:
    step(f"Deploying to Roku at {roku_ip}...")

    url = f"http://{roku_ip}/plugin_install"

    # Build multipart body manually (stdlib only)
    boundary = "BingeBoxOmegaBoundary42"
    body_parts = []

    # mysubmit field
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="mysubmit"\r\n\r\n'
        f"Install\r\n"
    )

    # archive field (the zip file)
    zip_data = zip_path.read_bytes()
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="archive"; filename="{zip_path.name}"\r\n'
        f"Content-Type: application/zip\r\n\r\n"
    )

    body = (
        "".join(body_parts).encode("utf-8")
        + zip_data
        + f"\r\n--{boundary}--\r\n".encode("utf-8")
    )

    # Basic auth
    import base64
    credentials = base64.b64encode(f"rokudev:{roku_pass}".encode()).decode()

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Basic {credentials}")
    req.add_header("Content-Length", str(len(body)))

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8", errors="replace")
            if "Install Success" in resp_body or resp.status == 200:
                ok(f"Deployed successfully to Roku at {roku_ip}!")
                return True
            else:
                warn(f"Unexpected response (HTTP {resp.status})")
                info(resp_body[:200])
                return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            err("Authentication failed — wrong password?")
        else:
            err(f"HTTP error {e.code}: {e.reason}")
        return False
    except Exception as e:
        err(f"Deploy failed: {e}")
        warn("Check: Roku IP correct? Dev mode enabled? Same WiFi network?")
        return False

def deploy_interactive(root: Path, zip_path: Path | None = None):
    blank()
    print(clr("  ┌─ ROKU DEVICE DEPLOY ──────────────────────────────────┐", M))
    print(clr("  │  Roku must be in DEV MODE:                            │", M))
    print(clr("  │  Settings → System → Advanced → Developer mode        │", M))
    print(clr("  └───────────────────────────────────────────────────────┘", M))
    blank()

    roku_ip = input("  Roku device IP (e.g. 192.168.1.50) or Enter to cancel: ").strip()
    if not roku_ip:
        warn("Deploy cancelled.")
        return

    roku_pass = input("  Roku dev password (default: rokudev): ").strip() or "rokudev"

    if zip_path is None or not zip_path.exists():
        warn("No zip found — packaging now...")
        zip_path = package_zip(root)
        if zip_path is None:
            return

    deploy_to_roku(zip_path, roku_ip, roku_pass)

# ═══════════════════════════════════════════════════════════════════════════════
# GIT PULL
# ═══════════════════════════════════════════════════════════════════════════════

def git_pull(root: Path):
    step("Pulling latest from GitHub...")
    if not check_git():
        err("git not found. Install from https://git-scm.com")
        return

    # Try parent in case root is the extracted subfolder inside the repo
    repo_root = root
    if not (root / ".git").exists():
        if (root.parent / ".git").exists():
            repo_root = root.parent
        else:
            warn("No .git directory found. Is this a cloned repo?")
            warn("If you downloaded the zip manually, use GitHub to pull.")
            return

    result = subprocess.run(
        ["git", "pull"],
        cwd=repo_root,
        text=True,
        capture_output=False
    )
    if result.returncode == 0:
        ok("Git pull complete")
    else:
        err("Git pull failed. Check your remote/branch.")

# ═══════════════════════════════════════════════════════════════════════════════
# FULL PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def full_pipeline(root: Path):
    blank()
    print(clr("  ════════ FULL PIPELINE ════════", Y))
    print("  Pull → Install → Compile → Package → Deploy")
    sep()

    steps_done = []

    # 1. Git pull
    git_pull(root)
    steps_done.append("git pull")

    # 2. npm install
    if not npm_install(root):
        err("Pipeline stopped at npm install.")
        return
    steps_done.append("npm install")

    # 3. Compile
    if not compile_project(root):
        err("Pipeline stopped at compile.")
        return
    steps_done.append("bsc compile")

    # 4. Package
    zip_path = package_zip(root)
    if zip_path is None:
        err("Pipeline stopped at packaging.")
        return
    steps_done.append("package zip")

    # 5. Deploy
    blank()
    do_deploy = input("  Deploy to Roku now? [Y/n]: ").strip().lower()
    if do_deploy != "n":
        deploy_interactive(root, zip_path)
        steps_done.append("deploy")

    blank()
    sep("═")
    ok(f"Pipeline complete: {' → '.join(steps_done)}")
    sep("═")

# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT LINTER / INSPECTOR
# ═══════════════════════════════════════════════════════════════════════════════

def inspect_project(root: Path):
    step("Inspecting & linting project...")
    sep()
    issues = []

    # Manifest
    manifest = root / "src" / "manifest"
    if manifest.exists():
        ok("manifest found")
        for line in manifest.read_text().splitlines():
            info(line)
    else:
        err("manifest MISSING — Roku will reject the package!")
        issues.append("manifest missing")

    sep()

    # Components
    comp_dir = root / "src" / "components"
    if comp_dir.exists():
        xml_files = sorted(comp_dir.glob("*.xml"))
        bs_stems  = {f.stem for f in comp_dir.glob("*.bs")}
        ok(f"Components: {len(xml_files)} .xml files")
        for xf in xml_files:
            if xf.stem in bs_stems:
                ok(f"  {xf.stem}.xml ↔ {xf.stem}.bs")
            else:
                warn(f"  {xf.stem}.xml — NO matching .bs!")
                issues.append(f"Missing .bs for {xf.stem}.xml")
    else:
        err("src/components/ missing!")
        issues.append("components dir missing")

    sep()

    # Services / Utils
    for sub in ["Services", "Utils"]:
        d = root / "src" / "source" / sub
        if d.exists():
            files = [f.name for f in d.glob("*.bs")]
            ok(f"{sub}/: {files}")
        else:
            err(f"src/source/{sub}/ MISSING!")
            issues.append(f"{sub} dir missing")

    sep()

    # package.json
    pkg = root / "package.json"
    if pkg.exists():
        data = json.loads(pkg.read_text())
        deps = data.get("devDependencies", {})
        ok("package.json devDependencies:")
        for k, v in deps.items():
            info(f"  {k}: {v}")
        if "brighterscript" not in deps:
            warn("brighterscript not in devDependencies!")
            issues.append("brighterscript missing from package.json")
    else:
        err("package.json not found!")
        issues.append("package.json missing")

    sep()

    # Scan .bs files
    step("Scanning all .bs files...")
    all_bs = list((root / "src").rglob("*.bs"))
    ok(f"{len(all_bs)} .bs files found")
    for f in all_bs:
        text = f.read_text(encoding="utf-8", errors="replace")
        rel  = f.relative_to(root)
        if "console.log" in text:
            warn(f"JS console.log in {rel}")
            issues.append(f"console.log in {rel}")
        if "localhost" in text:
            warn(f"Hardcoded localhost in {rel}")
        if "sandbox=" in text.lower():
            warn(f"sandbox attribute in {rel}")

    sep()
    blank()
    if issues:
        err(f"{len(issues)} issue(s) found:")
        for i in issues:
            info(f"  • {i}")
    else:
        ok("All checks passed — project looks clean!")
    blank()

# ═══════════════════════════════════════════════════════════════════════════════
# TMDB TESTER
# ═══════════════════════════════════════════════════════════════════════════════

def tmdb_fetch(endpoint: str, api_key: str) -> dict | None:
    sep_char = "&" if "?" in endpoint else "?"
    url = f"{TMDB_BASE}{endpoint}{sep_char}api_key={api_key}&language=en-US"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BingeBoxOmega/3.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        err(f"TMDB error: {e}")
        return None

def tmdb_tester(api_key: str):
    step("TMDB API Live Tester")
    info(f"Key: {api_key[:8]}...{api_key[-4:]}")
    sep()

    data = tmdb_fetch("/configuration", api_key)
    if data:
        ok("API key VALID — connection successful")
    else:
        err("API key failed or no internet"); return

    blank()
    print(f"  {clr('[1]', C)} Search movie/show by name")
    print(f"  {clr('[2]', C)} Test a home row endpoint")
    print(f"  {clr('[3]', C)} Trending this week")
    print(f"  {clr('[4]', C)} Get details by TMDB ID")
    print(f"  {clr('[B]', DG)} Back")
    blank()
    c = input("  Choose: ").strip().upper()

    if c == "1":
        q = input("  Search: ").strip()
        data = tmdb_fetch(f"/search/multi?query={urllib.parse.quote(q)}", api_key)
        if not data: return
        sep()
        for r in data.get("results", [])[:8]:
            title  = r.get("title") or r.get("name") or "?"
            mid    = r.get("id", "?")
            mtype  = r.get("media_type", "?")
            year   = (r.get("release_date") or r.get("first_air_date") or "")[:4]
            rating = r.get("vote_average", 0)
            print(f"  {clr(str(mid).ljust(9), Y)}{clr(title.ljust(42), W)}{mtype.ljust(7)}{year}  ⭐{rating:.1f}")

    elif c == "2":
        endpoints = [
            ("/trending/all/week",                                              "Trending"),
            ("/movie/popular",                                                  "Popular Movies"),
            ("/movie/now_playing",                                              "Now Playing"),
            ("/tv/top_rated",                                                   "Top Rated TV"),
            ("/discover/movie?with_genres=28&sort_by=popularity.desc",         "Action"),
            ("/discover/movie?with_genres=27&sort_by=popularity.desc",         "Horror"),
            ("/discover/tv?with_genres=16&sort_by=popularity.desc",            "Anime"),
        ]
        for i, (ep, label) in enumerate(endpoints, 1):
            print(f"  {clr(f'[{i}]', C)} {label}")
        idx = input("  Choose: ").strip()
        try:
            ep, label = endpoints[int(idx)-1]
        except:
            warn("Invalid"); return
        data = tmdb_fetch(ep, api_key)
        if not data: return
        ok(f"{len(data.get('results',[]))} items in '{label}'")
        sep()
        for item in data.get("results", [])[:10]:
            title  = item.get("title") or item.get("name") or "?"
            mid    = item.get("id", "?")
            rating = item.get("vote_average", 0)
            print(f"  {clr(str(mid).ljust(9), Y)}{title.ljust(44)} ⭐{rating:.1f}")

    elif c == "3":
        data = tmdb_fetch("/trending/all/week", api_key)
        if not data: return
        ok("Trending this week:")
        sep()
        for i, r in enumerate(data.get("results", [])[:10], 1):
            title = r.get("title") or r.get("name") or "?"
            mtype = r.get("media_type", "?")
            print(f"  {clr(str(i).rjust(2), M)}.  {clr(title.ljust(44), W)}[{mtype}]")

    elif c == "4":
        mid   = input("  TMDB ID: ").strip()
        mtype = input("  Type [movie/tv]: ").strip() or "movie"
        data  = tmdb_fetch(f"/{mtype}/{mid}", api_key)
        if not data: return
        sep()
        title   = data.get("title") or data.get("name") or "?"
        tagline = data.get("tagline", "")
        rating  = data.get("vote_average", 0)
        votes   = data.get("vote_count", 0)
        overview= data.get("overview", "")[:160]
        year    = (data.get("release_date") or data.get("first_air_date") or "")[:4]
        ok(f"{title} ({year})")
        if tagline: info(f'"{tagline}"')
        info(f"⭐ {rating:.1f} / 10  ({votes:,} votes)")
        info(f"Overview: {overview}...")

# ═══════════════════════════════════════════════════════════════════════════════
# SERVER URL BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_embed_url(tmdb_id: str, mtype: str, srv: dict, s=1, e=1) -> str:
    if mtype == "movie":
        url = srv["movieBase"] + tmdb_id
        if srv["id"] == "vidlink":
            url += "?primaryColor=E50914&autoplay=true"
    else:
        url = srv["tvBase"] + tmdb_id + f"/{s}/{e}"
        if srv["id"] == "vidsrcme":
            url = srv["tvBase"] + tmdb_id + f"&season={s}&episode={e}"
    return url

def server_url_builder():
    step("Streaming Server URL Builder")
    sep()
    tmdb_id = input("  TMDB ID (e.g. 550 for Fight Club): ").strip()
    if not tmdb_id: return
    mtype = input("  Type [movie/tv] (default: movie): ").strip() or "movie"
    s = e = "1"
    if mtype == "tv":
        s = input("  Season  (default: 1): ").strip() or "1"
        e = input("  Episode (default: 1): ").strip() or "1"
    blank()
    ok(f"Embed URLs for TMDB:{tmdb_id} ({mtype})")
    sep()
    for srv in SERVERS:
        url = build_embed_url(tmdb_id, mtype, srv, s, e)
        print(f"  {clr(srv['badge'], W)} {clr(srv['name'].ljust(14), C)} {url}")
    blank()

# ═══════════════════════════════════════════════════════════════════════════════
# MANIFEST EDITOR
# ═══════════════════════════════════════════════════════════════════════════════

def edit_manifest(root: Path):
    mp = root / "src" / "manifest"
    if not mp.exists():
        err("manifest not found!"); return
    step("Manifest Editor")
    sep()
    lines = mp.read_text().splitlines()
    for i, line in enumerate(lines, 1):
        print(f"  {clr(str(i).rjust(2), DG)}  {line}")
    sep()
    blank()
    edit = input("  Edit field (e.g.  title=My App)  or Enter to cancel: ").strip()
    if not edit or "=" not in edit:
        warn("Cancelled."); return
    key, val = edit.split("=", 1)
    key = key.strip(); val = val.strip()
    new_lines = []
    replaced = False
    for line in lines:
        if line.startswith(key + "="):
            new_lines.append(f"{key}={val}")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f"{key}={val}")
    mp.write_text("\n".join(new_lines) + "\n")
    ok(f"Updated: {key}={val}")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG VIEWER
# ═══════════════════════════════════════════════════════════════════════════════

def show_config(root: Path):
    step("Config viewer — servers & rows from Config.bs")
    cfg_path = root / "src" / "source" / "Services" / "Config.bs"
    if not cfg_path.exists():
        err("Config.bs not found!"); return
    text = cfg_path.read_text(encoding="utf-8", errors="replace")

    # Servers
    servers = re.findall(r'id:\s*"([^"]+)",\s*name:\s*"([^"]+)"', text)
    sep()
    ok(f"Servers ({len(servers)}):")
    for sid, sname in servers:
        print(f"    {clr(sid.ljust(14), Y)} {sname}")

    # Rows
    rows = re.findall(r'title:\s*"([^"]+)"[^}]+?endpoint:\s*"([^"]+)"', text, re.S)
    blank()
    ok(f"Content rows ({len(rows)}):")
    for title, ep in rows:
        print(f"    {clr(title.ljust(26), M)} {clr(ep, C)}")

    # Feature flags
    flags = re.findall(r'(Enable\w+|BandwidthSaver):\s*(true|false)', text)
    blank()
    ok(f"Feature flags:")
    for flag, val in flags:
        colour = G if val == "true" else DG
        print(f"    {flag.ljust(24)} {clr(val, colour)}")
    blank()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN MENU
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    banner()

    project_root = find_project()
    if project_root:
        ok(f"Project: {project_root}")
        cfg     = read_config(project_root)
        api_key = cfg.get("tmdb_key", TMDB_KEY_DEFAULT)
    else:
        project_root = prompt_project()
        api_key = TMDB_KEY_DEFAULT
        if project_root:
            cfg     = read_config(project_root)
            api_key = cfg.get("tmdb_key", TMDB_KEY_DEFAULT)

    last_zip: Path | None = None

    while True:
        blank()
        print(clr("  ╔═══════════════════════════════════════════════════╗", C))
        print(clr("  ║         BingeBox Omega — Dev Menu                 ║", C))
        print(clr("  ╠═══════════════════════════════════════════════════╣", C))
        print(  f"  ║  {clr('[1]', G)} Install npm deps (npm install)             ║")
        print(  f"  ║  {clr('[2]', G)} Compile BrighterScript (bsc)              ║")
        print(  f"  ║  {clr('[3]', G)} Package .zip for Roku sideload            ║")
        print(  f"  ║  {clr('[4]', G)} Deploy to Roku device (over LAN)          ║")
        print(  f"  ║  {clr('[5]', G)} Git pull (update from GitHub)             ║")
        print(  f"  ║  {clr('[6]', C)} TMDB API live tester                      ║")
        print(  f"  ║  {clr('[7]', C)} Server URL builder (all 7 servers)        ║")
        print(  f"  ║  {clr('[8]', C)} Inspect & lint project                    ║")
        print(  f"  ║  {clr('[9]', C)} Edit manifest                             ║")
        print(  f"  ║  {clr('[0]', C)} View config (servers, rows, flags)        ║")
        print(  f"  ║  {clr('[P]', Y)} ★ FULL PIPELINE (pull→install→build→zip→deploy) ║")
        print(  f"  ║  {clr('[Q]', DG)} Quit                                      ║")
        print(clr("  ╚═══════════════════════════════════════════════════╝", C))
        blank()

        if project_root:
            print(f"  {clr('Project:', DG)} {clr(str(project_root), W)}")
        else:
            print(f"  {clr('Project: NOT FOUND', R)}")
        if last_zip:
            print(f"  {clr('Last zip:', DG)} {clr(last_zip.name, G)}")
        blank()

        choice = input("  Choose: ").strip().upper()

        if not project_root and choice not in ("Q", "6", "7"):
            project_root = prompt_project()
            if not project_root:
                continue

        if   choice == "1": npm_install(project_root)
        elif choice == "2": compile_project(project_root)
        elif choice == "3":
            z = package_zip(project_root)
            if z: last_zip = z
        elif choice == "4": deploy_interactive(project_root, last_zip)
        elif choice == "5": git_pull(project_root)
        elif choice == "6": tmdb_tester(api_key)
        elif choice == "7": server_url_builder()
        elif choice == "8": inspect_project(project_root)
        elif choice == "9": edit_manifest(project_root)
        elif choice == "0": show_config(project_root)
        elif choice == "P": full_pipeline(project_root)
        elif choice == "Q":
            blank()
            ok("Goodbye!")
            sys.exit(0)
        else:
            warn("Invalid option.")

if __name__ == "__main__":
    main()
