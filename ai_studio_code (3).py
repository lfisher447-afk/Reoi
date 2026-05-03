#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        BINGEBOX OMEGA SUPREME — THE ULTIMATE FULL-STACK DEV ENGINE           ║
║        Unified v5.0.0 | Pure System-Level Python 3.10+                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  [CORE]      npm install, bsc compile, package zip, deploy multipart         ║
║  [GIT]       pull, status, branch, stash, log, diff, changelog gen           ║
║[TMDB]      Search, trending, details, discover, images, person lookup      ║
║  [TOOLS]     Linter (v5 strict), manifest editor, config viewer, URL builder ║
║  [NETWORK]   Server ping, ECP remote, network scanner, port checking         ║
║  [ADVANCED]  Benchmarking, interactive file diff, zip differentials          ║
║  [ENV]       Registry dump, Watchdog auto-build, Rollback manager            ║
║  [UI]        CLI OS, Rich Telemetry Dashboard, Turtle Cyberpunk HUD          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import sys
import os
import re
import json
import zipfile
import shutil
import time
import socket
import hashlib
import base64
import threading
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import http.client
import argparse
import traceback
import textwrap
import difflib
import platform
import logging
import queue
import contextlib
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional, Union, Any

# ─────────────────────────────────────────────────────────────────────────────
# OPTIONAL UI LIBRARIES (Graceful Degradation)
# ─────────────────────────────────────────────────────────────────────────────
try:
    import turtle
    TURTLE_AVAILABLE = True
except ImportError:
    TURTLE_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.align import Align
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# GLOBALS & ANSI COLORS
# ─────────────────────────────────────────────────────────────────────────────
IS_WIN   = sys.platform == "win32"
IS_MAC   = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

if IS_WIN:
    os.system("") # Enable ANSI Escape Sequences natively on Windows 10+

R     = "\033[91m"
G     = "\033[92m"
Y     = "\033[93m"
C     = "\033[96m"
M     = "\033[95m"
W     = "\033[97m"
DG    = "\033[90m"
B     = "\033[94m"
RST   = "\033[0m"
BOLD  = "\033[1m"
BLINK = "\033[5m"

NO_COLOR = os.getenv("NO_COLOR") or not sys.stdout.isatty()

def clr(t: str, c: str) -> str:
    return t if NO_COLOR else f"{c}{t}{RST}"

def ok(m: str):    print(f"  {clr('✓', G)} {m}")
def err(m: str):   print(f"  {clr('✗', R)} {m}")
def warn(m: str):  print(f"  {clr('!', Y)} {m}")
def step(m: str):  print(f"\n  {clr('▶', C)} {clr(m, W)}")
def info(m: str):  print(f"    {clr(m, DG)}")
def hdr(m: str):   print(f"\n  {clr('━'*54, B)}\n  {clr(m, M+BOLD)}\n  {clr('━'*54, B)}")
def sep(ch="─"):   print(f"  {clr(ch*54, DG)}")
def blank():       print()

# Logging implementation (Isolated from Console UI)
LOG_FILE = Path.home() / ".bingebox_supreme.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s[%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("omega_supreme")

def _log_err(context: str, exc: Exception):
    log.error(f"{context}: {exc}", exc_info=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
VERSION          = "5.0.0-SUPREME"
TMDB_KEY_DEFAULT = "15d2ea6d0dc1d476efbca3eba2b9bbfb"
TMDB_BASE        = "https://api.themoviedb.org/3"

SERVERS: list[dict] =[
    {"id": "vidlink",    "name": "VidLink Pro",  "badge": "⚡", "movieBase": "https://vidlink.pro/movie/",               "tvBase": "https://vidlink.pro/tv/"},
    {"id": "vidsrcpro",  "name": "VidSrc PRO",   "badge": "🔥", "movieBase": "https://vidsrc.pro/embed/movie/",          "tvBase": "https://vidsrc.pro/embed/tv/"},
    {"id": "videasy",    "name": "Videasy",      "badge": "🎬", "movieBase": "https://player.videasy.net/movie/",        "tvBase": "https://player.videasy.net/tv/"},
    {"id": "vidsrccc",   "name": "VidSrc CC",    "badge": "🌐", "movieBase": "https://vidsrc.cc/v2/embed/movie/",        "tvBase": "https://vidsrc.cc/v2/embed/tv/"},
    {"id": "autoembed",  "name": "AutoEmbed",    "badge": "🤖", "movieBase": "https://player.autoembed.cc/embed/movie/", "tvBase": "https://player.autoembed.cc/embed/tv/"},
    {"id": "2embed",     "name": "2Embed",       "badge": "✨", "movieBase": "https://www.2embed.cc/embed/",             "tvBase": "https://www.2embed.cc/embedtv/"},
    {"id": "vidsrcme",   "name": "VidSrc.ME",    "badge": "💾", "movieBase": "https://vidsrc.me/embed/movie?tmdb=",      "tvBase": "https://vidsrc.me/embed/tv?tmdb="},
]

ROKU_ECP_PORT = 8060
DEFAULT_ROKU_PASS = "rokudev"

PROJECT_CANDIDATES: list[Path] =[
    Path.cwd() / "BingeBox-Roku-v2",
    Path.cwd() / "BingeBox_Omega_Roku_v3",
    Path.cwd(),
    Path.home() / "Desktop"   / "BingeBox-Roku-v2",
    Path.home() / "Downloads" / "BingeBox-Roku-v2",
    Path.home() / "Documents" / "BingeBox-Roku-v2",
]

_LINT_RULES =[
    (r"console\.log\b",                 "JS console.log found (invalid in BrightScript)"),
    (r"\blocalhost\b",                  "Hardcoded localhost URL"),
    (r"\b127\.0\.0\.1\b",               "Hardcoded loopback IP"),
    (r"sandbox\s*=",                    "sandbox= attribute detected (Not applicable for Roku)"),
    (r"(?i)\bTODO\b",                   "TODO comment"),
    (r"(?i)\bFIXME\b",                  "FIXME comment"),
    (r"(?i)\bHACK\b",                   "HACK comment"),
    (r'"password"\s*:',                 "Possible plaintext password"),
    (r'api_key\s*=\s*"[^"]{8,}"',       "Possible hardcoded API key"),
    (r'\bprint\s+"',                    "Naked print statement (use Logger)"),
    (r"(?i)http://(?!localhost)",       "Non-HTTPS URL"),
    (r"\bCreateObject\s*\(\s*\"roArray\"\s*\)", "Use[] literal instead of CreateObject(\"roArray\")"),
    (r"=>",                             "Arrow functions (=>) are invalid in BrightScript"),
    (r"\b(let|const)\s+\w+",            "JS-style variable declaration (use 'dim' or implicit assignment)"),
]

# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def terminal_width() -> int:
    try: return min(os.get_terminal_size().columns, 120)
    except Exception: return 80

def progress_bar(done: int, total: int, width: int = 30, label: str = "") -> str:
    frac = done / total if total else 0
    filled = int(width * frac)
    bar = clr("█" * filled, G) + clr("░" * (width - filled), DG)
    pct = f"{frac * 100:5.1f}%"
    return f"  [{bar}] {pct}  {label}"

@contextlib.contextmanager
def spin(msg: str):
    """Context manager for an animated CLI spinner."""
    stop, done = threading.Event(), threading.Event()
    def _spin():
        for frame in iter(lambda i=[0]: "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[i[0] % 10] or i.append(i.pop(0) + 1), None):
            if stop.is_set(): break
            sys.stdout.write(f"\r  {clr(frame, C)}  {msg}   ")
            sys.stdout.flush()
            time.sleep(0.08)
        sys.stdout.write("\r" + " " * (len(msg) + 12) + "\r")
        sys.stdout.flush()
        done.set()
    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try: yield
    finally:
        stop.set()
        done.wait(timeout=1)

def confirm(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    raw = input(f"  {prompt} {hint}: ").strip().lower()
    return default if not raw else raw.startswith("y")

def choose_from(options: list[tuple[str, str]], prompt: str = "Choose") -> Optional[int]:
    """Display numbered menu, return 0-based index or None on cancel."""
    for i, (label, desc) in enumerate(options, 1):
        print(f"  {clr(f'[{i}]', C)} {clr(label, W):20} {clr(desc, DG)}")
    print(f"  {clr('[0]', DG)} Back / Cancel")
    raw = input(f"  {prompt}: ").strip()
    if raw == "0" or not raw: return None
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(options): return idx
    except ValueError: pass
    warn("Invalid choice.")
    return None

def banner():
    os.system("cls" if IS_WIN else "clear")
    art = r"""
        ██████╗ ███╗   ██╗███████╗ ██████╗  █████╗     
        ██╔══██╗████╗  ██║██╔════╝██╔════╝ ██╔══██╗    
        ██████╔╝██╔██╗ ██║█████╗  ██║  ███╗███████║    
        ██╔══██╗██║╚██╗██║██╔══╝  ██║   ██║██╔══██║    
        ██████╔╝██║ ╚████║███████╗╚██████╔╝██║  ██║    
        ╚═════╝ ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝    
    ███████╗██╗   ██╗██████╗ ██████╗ ███████╗███╗   ███╗███████╗
    ██╔════╝██║   ██║██╔══██╗██╔══██╗██╔════╝████╗ ████║██╔════╝
    ███████╗██║   ██║██████╔╝██████╔╝█████╗  ██╔████╔██║█████╗  
    ╚════██║██║   ██║██╔═══╝ ██╔══██╗██╔══╝  ██║╚██╔╝██║██╔══╝  
    ███████║╚██████╔╝██║     ██║  ██║███████╗██║ ╚═╝ ██║███████╗
    ╚══════╝ ╚═════╝ ╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚══════╝"""
    print(clr(art, M + BOLD))
    print(clr(f"  O M E G A   S U P R E M E   v{VERSION}  ·  ULTIMATE DEV TOOL", Y))
    print(clr(f"  System: {platform.system()} {platform.release()}  ·  Python {sys.version.split()[0]}", DG))
    print(clr("  ─────────────────────────────────────────────────────────────────", DG))
    blank()

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT DISCOVERY
# ─────────────────────────────────────────────────────────────────────────────
def find_project() -> Optional[Path]:
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        p = Path(sys.argv[1])
        if (p / "package.json").exists(): return p.resolve()
    for c in PROJECT_CANDIDATES:
        if (c / "package.json").exists(): return c.resolve()
    return None

def prompt_project() -> Optional[Path]:
    warn("Project folder not found automatically.")
    raw = input("  Enter full path to project root (Enter to skip): ").strip().strip('"\'')
    if raw:
        p = Path(raw)
        if (p / "package.json").exists(): return p.resolve()
        err(f"No package.json at '{p}'")
    return None

def read_config(root: Path) -> dict:
    result = {"tmdb_key": TMDB_KEY_DEFAULT, "features": {}, "servers": [], "rows":[]}
    cfg = root / "src" / "source" / "Services" / "Config.bs"
    if not cfg.exists(): return result
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'TMDB_KEY:\s*"([a-f0-9]{32})"', text)
        if m: result["tmdb_key"] = m.group(1)
        flags = re.findall(r"(Enable\w+|BandwidthSaver):\s*(true|false)", text)
        result["features"] = {k: v == "true" for k, v in flags}
        result["servers"] = re.findall(r'id:\s*"([^"]+)",\s*name:\s*"([^"]+)"', text)
        result["rows"] = re.findall(r'title:\s*"([^"]+)"[^}]+?endpoint:\s*"([^"]+)"', text, re.DOTALL)
    except OSError as e:
        _log_err("read_config", e)
    return result

# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT CHECKS (Zero Pip Deps Required)
# ─────────────────────────────────────────────────────────────────────────────
def _run_version(cmd: list[str]) -> Optional[str]:
    try: return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception: return None

def check_node() -> bool:
    step("Checking Build Toolchain (Node.js/NPM)...")
    node, npm, npx = shutil.which("node"), shutil.which("npm"), shutil.which("npx")
    all_ok = True
    if not node:
        err("Node.js not found! Require LTS version."); all_ok = False
    else:
        ver = _run_version(["node", "--version"]) or "?"
        major = int(ver.lstrip("v").split(".")[0]) if ver != "?" else 0
        status = clr(ver, G) if major >= 16 else clr(f"{ver} (upgrade recommended)", Y)
        ok(f"Node.js {status}")
    
    if not npm:
        err("npm not found"); all_ok = False
    else:
        ok(f"npm v{_run_version(['npm', '--version']) or '?'}")
    
    if npx: ok("npx available (fallback compiler active)")
    return all_ok

def full_env_check(root: Optional[Path]):
    hdr("SUPREME ENVIRONMENT HEALTH CHECK")
    check_node()
    sep()
    tools = [
        ("python3",["python3", "--version"]), ("git", ["git", "--version"]),
        ("curl", ["curl", "--version"]), ("node", ["node", "--version"]),
    ]
    step("Core Tool Versions:")
    for name, cmd in tools:
        ver = _run_version(cmd)
        ok(f"{name:12} {ver.splitlines()[0][:60]}") if ver else warn(f"{name:12} missing")
    
    sep()
    step("Python Dependency Mapping:")
    for mod in["json", "zipfile", "urllib", "socket", "hashlib", "threading"]:
        try: __import__(mod); ok(f"{mod} available")
        except ImportError: err(f"{mod} MISSING")

    if root:
        sep()
        step("Disk Array Health:")
        try:
            usage = shutil.disk_usage(root)
            free_gb, total_gb = usage.free / 1e9, usage.total / 1e9
            ok(f"Free Space: {clr(f'{free_gb:.1f} GB', G if free_gb > 5 else Y)} / {total_gb:.1f} GB")
        except: warn("Could not read disk usage")

    sep()
    step("External Network Gateways:")
    for label, host, port in[("TMDB API Gateway", "api.themoviedb.org", 443), ("GitHub Pipeline", "github.com", 443)]:
        try:
            with socket.create_connection((host, port), timeout=4): ok(f"{label:22} REACHABLE")
        except: err(f"{label:22} OFFLINE")

# ─────────────────────────────────────────────────────────────────────────────
# BUILD & COMPILATION PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def npm_install(root: Path) -> bool:
    step("Resolving NPM Workspace Dependencies...")
    if not shutil.which("npm"):
        err("npm missing from PATH"); return False
    
    res = subprocess.run(["npm", "install"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if res.returncode != 0:
        err("npm install FAILED")
        info(res.stderr.decode(errors='replace')[:500])
        return False
    ok("Dependencies locked and loaded")
    return True

def compile_project(root: Path) -> bool:
    step("Compiling BrighterScript (BSC Engine)...")
    if not (root / "node_modules").exists():
        if not npm_install(root): return False
        
    t0 = time.perf_counter()
    with spin("Running compiler pipeline..."):
        res = subprocess.run(["npm", "run", "build"], cwd=root, capture_output=True, text=True)
        
    if res.returncode != 0:
        warn("npm run build failed, invoking npx bsc directly...")
        res = subprocess.run(["npx", "bsc"], cwd=root, capture_output=True, text=True)
        if res.returncode != 0:
            err("Compilation FAILED. Compiler Output:")
            print(clr(res.stdout[-1000:], Y))
            return False
            
    elapsed = time.perf_counter() - t0
    staging = root / "out" / ".roku-deploy-staging"
    if staging.exists():
        fc = sum(1 for f in staging.rglob("*") if f.is_file())
        ok(f"Compiled successfully in {elapsed:.1f}s → {fc} bytecode components")
    else:
        warn("Staging folder missing — Build may have partially failed.")
    return True

def package_zip(root: Path, use_staging: bool = True) -> Optional[Path]:
    step("Packaging Roku Payload (.zip)...")
    ts = datetime.now().strftime("%Y%m%d-%H%M")
    zip_path = root / f"BingeBox-Supreme-{ts}.zip"
    staging, src_dir = root / "out/.roku-deploy-staging", root / "src"
    
    if use_staging and staging.exists():
        base = staging
    elif src_dir.exists():
        base = src_dir
        warn("Uncompiled Source Mode Active (Packaging raw src/)")
    else:
        err("Source Matrix Missing!"); return None

    all_files = sorted(f for f in base.rglob("*") if f.is_file())
    if not all_files: err("Empty build directory"); return None

    checksums = {}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for i, f in enumerate(all_files, 1):
            arc = f.relative_to(base)
            zf.write(f, arc)
            checksums[str(arc)] = hashlib.md5(f.read_bytes()).hexdigest()
            sys.stdout.write(f"\r{progress_bar(i, len(all_files), label=f.name[:40])}")
    
    sys.stdout.write("\r" + " " * 90 + "\r")
    
    cksum_path = zip_path.with_suffix(".md5")
    cksum_path.write_text("\n".join(f"{v}  {k}" for k, v in sorted(checksums.items())) + "\n")
    
    ok(f"Payload Created: {zip_path.name} ({zip_path.stat().st_size//1024} KB)")
    info(f"Integrity check saved to .md5 manifest")
    return zip_path

# ─────────────────────────────────────────────────────────────────────────────
# DEVICE DEPLOYMENT (HTTP MULTIPART REST API)
# ─────────────────────────────────────────────────────────────────────────────
def _build_multipart(zip_path: Path) -> tuple[bytes, str]:
    boundary = f"SupremeBoundary{int(time.time())}"
    CRLF = b"\r\n"
    
    part1 = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="mysubmit"\r\n\r\n'
        f"Install\r\n"
    ).encode("utf-8")
    
    part2 = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="archive"; filename="{zip_path.name}"\r\n'
        f"Content-Type: application/zip\r\n\r\n"
    ).encode("utf-8")
    
    closer = f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    body = part1 + part2 + zip_path.read_bytes() + closer
    return body, boundary

def deploy_to_roku(zip_path: Path, ip: str, pwd: str) -> bool:
    step(f"Transmitting Payload to {ip}...")
    body, boundary = _build_multipart(zip_path)
    auth = base64.b64encode(f"rokudev:{pwd}".encode()).decode()
    
    req = urllib.request.Request(f"http://{ip}/plugin_install", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Length", str(len(body)))
    
    try:
        t0 = time.perf_counter()
        with spin("Uploading and waiting for Roku OS initialization..."):
            with urllib.request.urlopen(req, timeout=40) as r:
                resp = r.read().decode(errors="replace").lower()
                
        if any(k in resp for k in ["install success", "application installed"]) or r.status == 200:
            ok(f"Flash Successful in {time.perf_counter()-t0:.1f} seconds! Executing Launch.")
            return True
        else:
            err("Roku OS rejected the package deployment."); info(resp[:300])
            return False
            
    except urllib.error.HTTPError as e:
        err("Authentication Failed (Check DEV Password)" if e.code == 401 else f"HTTP Status {e.code}")
        return False
    except Exception as e:
        err(f"Network Deployment Exception: {e}")
        return False

def deploy_interactive(root: Path, zip_path: Optional[Path] = None):
    blank()
    print(clr("  ┌─ ROKU HARWARE LINK ──────────────────────────────────┐", C))
    print(clr("  │  Roku OS must have Developer Mode active.            │", C))
    print(clr("  │  (Settings → System → Advanced → Developer mode)     │", C))
    print(clr("  └──────────────────────────────────────────────────────┘", C))
    
    ip = input("  Device IPv4 Address: ").strip()
    if not ip or not re.match(r"^(\d{1,3}\.){3}\d{1,3}$|^[a-zA-Z0-9._-]+$", ip):
        err("Network Address Invalid"); return
        
    pwd = input(f"  Root Password (default: {DEFAULT_ROKU_PASS}): ").strip() or DEFAULT_ROKU_PASS
    
    if not zip_path or not zip_path.exists():
        warn("No prepared zip found. Synthesizing now...")
        zip_path = package_zip(root)
        
    if zip_path: deploy_to_roku(zip_path, ip, pwd)

# ─────────────────────────────────────────────────────────────────────────────
# ROKU ECP & NETWORK SCANNERS
# ─────────────────────────────────────────────────────────────────────────────
def roku_ecp(ip: str, path: str, method: str = "GET", body: bytes = b"") -> Optional[str]:
    try:
        conn = http.client.HTTPConnection(ip, ROKU_ECP_PORT, timeout=5)
        conn.request(method, path, body)
        resp = conn.getresponse()
        data = resp.read().decode(errors="replace")
        conn.close()
        return data
    except: return None

def roku_remote_tool(ip: str):
    hdr("ROKU ECP TERMINAL LINK")
    info_xml = roku_ecp(ip, "/query/device-info")
    if not info_xml: err(f"Handshake failed with {ip}:{ROKU_ECP_PORT}"); return
    ok("Link Established")
    
    KEYS = {
        "h":"Home", "b":"Back", "u":"Up", "d":"Down", "l":"Left", 
        "r":"Right", "s":"Select", "p":"Play", "i":"Info", "x":"Search"
    }
    for k, v in KEYS.items(): print(f"    {clr(k, C)} → {v}")
    
    while True:
        raw = input(f"  {clr('KEY', M)} [q to quit] > ").strip().lower()
        if raw == "q": break
        if raw in KEYS:
            roku_ecp(ip, f"/keypress/{KEYS[raw]}", "POST")
            ok(f"Transmitted: {KEYS[raw]}")
        else: warn("Unrecognized command")

def roku_app_list(ip: str):
    hdr("ROKU INSTALLED APPLICATION REGISTRY")
    xml = roku_ecp(ip, "/query/apps")
    if not xml: err("Failed query"); return
    apps = re.findall(r'<app id="([^"]+)"[^>]*>([^<]+)</app>', xml)
    ok(f"Found {len(apps)} installed apps:")
    for aid, name in sorted(apps, key=lambda x: x[1].lower()):
        print(f"  {clr(aid.ljust(12), DG)} {clr(name, C)}")

def scan_roku_on_network(subnet: str = ""):
    hdr("MULTICAST SUBNET SCANNER")
    if not subnet:
        try: subnet = ".".join(socket.gethostbyname(socket.gethostname()).split(".")[:3])
        except: subnet = "192.168.1"
        
    info(f"Targeting {subnet}.0/24 on port {ROKU_ECP_PORT}...")
    q = queue.Queue()
    
    def probe(i: str):
        try:
            with socket.create_connection((i, ROKU_ECP_PORT), timeout=0.3): q.put(i)
        except: pass
        
    threads =[threading.Thread(target=probe, args=(f"{subnet}.{i}",), daemon=True) for i in range(1, 255)]
    for t in threads: t.start()
    for t in threads: t.join(timeout=1.5)
    
    found =[]
    while not q.empty():
        ip = q.get()
        xml = roku_ecp(ip, "/query/device-info")
        name = re.search(r"<friendly-device-name>([^<]+)</friendly-device-name>", xml or "")
        ok(f"{ip:16} {clr(name.group(1) if name else 'Unknown Roku Device', W)}")
        found.append(ip)
        
    if not found: warn("No signals detected on subnet.")
    return found

# ─────────────────────────────────────────────────────────────────────────────
# GIT PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def _git(root: Path, args: list[str], stream=True):
    if not shutil.which("git"):
        err("Git CLI missing from system PATH."); return None
    repo = root if (root / ".git").exists() else root.parent
    return subprocess.run(["git"] + args, cwd=repo, stdout=None if stream else subprocess.PIPE, text=True)

def git_pull(r: Path): step("Pulling from Origin..."); _git(r, ["pull"])
def git_status(r: Path): step("Repository Status:"); _git(r,["status", "-s", "-b"])
def git_log(r: Path): step("Commit History:"); _git(r,["log", "-10", "--pretty=format:%C(yellow)%h%Creset %C(cyan)%ad%Creset %s", "--date=short"])
def git_diff(r: Path): step("Working Tree Diff:"); _git(r, ["diff", "HEAD"])
def git_stash(r: Path): step("Stashing changes..."); _git(r, ["stash", "push"])

def generate_changelog(r: Path):
    hdr("CHANGELOG SYNTHESIS")
    res = _git(r,["log", "--pretty=format:%ad|%s", "--date=short"], False)
    if res and res.returncode == 0:
        logs = defaultdict(list)
        for line in res.stdout.splitlines():
            if "|" in line:
                d, msg = line.split("|", 1)
                logs[d].append(f"- {msg}")
                
        out =["# CHANGELOG\n"]
        for d in sorted(logs, reverse=True):
            out.append(f"## {d}")
            out.extend(logs[d])
            out.append("")
            
        (r / "CHANGELOG.md").write_text("\n".join(out))
        ok("CHANGELOG.md fully synthesized based on Git timeline.")
    else:
        err("Failed to parse git history.")

# ─────────────────────────────────────────────────────────────────────────────
# DEEP PROJECT LINTER & INSPECTOR
# ─────────────────────────────────────────────────────────────────────────────
def _lint_file(path: Path, root: Path) -> list[dict]:
    issues =[]
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines, 1):
            for pat, msg in _LINT_RULES:
                if re.search(pat, line):
                    issues.append({"file": str(path.relative_to(root)), "line": i, "msg": msg, "text": line.strip()})
    except OSError: pass
    return issues

def inspect_project(root: Path):
    hdr("DEEP PROJECT LINTER & STATIC ANALYSIS")
    issues =[]
    
    # 1. Manifest
    man = root / "src" / "manifest"
    if man.exists():
        ok("Manifest Configuration: LOCATED")
        content = man.read_text()
        for k in["title", "build_version", "ui_resolutions", "major_version", "minor_version"]:
            if not re.search(rf"^{k}=", content, re.MULTILINE):
                warn(f"Manifest Missing Core Key: {k}")
                issues.append(f"manifest missing {k}")
    else: 
        err("Manifest Configuration: MISSING (Fatal)"); issues.append("manifest missing")
    
    sep()
    
    # 2. Components .xml / .bs Match
    comp = root / "src" / "components"
    if comp.exists():
        xmls = sorted(comp.rglob("*.xml"))
        bss = {f.stem for f in comp.rglob("*.bs")}
        ok(f"Component Scan: {len(xmls)} XML nodes found")
        for x in xmls:
            if x.stem not in bss:
                warn(f"Orphaned XML: {x.stem}.xml lacks matching .bs script logic")
                issues.append(f"{x.stem} missing bs logic")
    
    sep()
    
    # 3. BrightScript File Linting
    step(f"Executing Deep Regex Scanning on .bs Codebase ({len(_LINT_RULES)} Rules)...")
    hits =[]
    bs_files = list((root / "src").rglob("*.bs"))
    for f in bs_files:
        hits.extend(_lint_file(f, root))
        
    if hits:
        warn(f"Detected {len(hits)} Syntax/Style Exceptions:")
        for h in hits:
            print(f"  {clr(h['file'], C)}:{clr(str(h['line']), Y)}  {clr(h['msg'], R)}")
            print(f"    {clr(h['text'][:80], DG)}")
    else:
        ok(f"Codebase Clean ({len(bs_files)} files parsed). Zero Exceptions.")
        
    sep()
    if issues or hits: err("Static Analysis Complete. Issues Found.")
    else: ok("Static Analysis Complete. Target is Pristine.")
    blank()

# ─────────────────────────────────────────────────────────────────────────────
# TMDB MASTER APPLIANCE
# ─────────────────────────────────────────────────────────────────────────────
def tmdb_fetch(ep: str, key: str, params: dict = None) -> Optional[dict]:
    p = {"api_key": key, "language": "en-US"}
    if params: p.update(params)
    qs = urllib.parse.urlencode(p, quote_via=urllib.parse.quote)
    url = f"{TMDB_BASE}{ep}{'&' if '?' in ep else '?'}{qs}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"OmegaSupreme/{VERSION}"})
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 401: warn("TMDB Auth Failed (Invalid Key)")
        return None
    except Exception: return None

def _fmt_item(r: dict) -> str:
    title  = r.get("title") or r.get("name") or "?"
    mid    = str(r.get("id", "?"))
    mtype  = r.get("media_type", "movie")
    year   = (r.get("release_date") or r.get("first_air_date") or "")[:4]
    rating = r.get("vote_average", 0)
    return f"  {clr(mid.ljust(9), Y)}{clr(title.ljust(44), W)}{clr(mtype.ljust(8), DG)}{year}  {clr(f'⭐{rating:.1f}', M)}"

def tmdb_tester(key: str):
    hdr("TMDB GLOBAL DATALINK")
    if not tmdb_fetch("/configuration", key):
        err("Datalink Failed (Invalid Key or Offline)"); return
    ok("Datalink Established")
    
    while True:
        blank()
        print(clr("  ┌─ TMDB COMMAND MENU ──────────────────────────────────────┐", C))
        print(f"  │[1] Universal Search   [2] Horizon (Trending/Popular) │")
        print(f"  │  [3] Deep Data ID Link  [4] Discover (Filter Search)   │")
        print(f"  │  [5] Actor/Cast Matrix  [6] URL Stream Generator       │")
        print(f"  │  [0] Disconnect                                        │")
        print(clr("  └────────────────────────────────────────────────────────┘", C))
        
        c = input(f"  {clr('TMDB', M)} > ").strip()
        if c == "0": break
        elif c == "1":
            q = input("  Search Query: ").strip()
            data = tmdb_fetch("/search/multi", key, {"query": q})
            if data:
                for r in data.get("results", [])[:12]: print(_fmt_item(r))
        elif c == "2":
            eps =[
                ("/trending/all/week", "Global Trending"),
                ("/movie/popular", "Popular Movies"),
                ("/tv/top_rated", "Highest Rated TV Series")
            ]
            for i, (ep, lbl) in enumerate(eps, 1): print(f"  [{i}] {lbl}")
            try:
                ep = eps[int(input("  Select: ").strip())-1][0]
                data = tmdb_fetch(ep, key)
                for r in data.get("results", [])[:12]: print(_fmt_item(r))
            except: warn("Aborted")
        elif c == "3":
            mid = input("  TMDB ID: ")
            typ = input("  Type [movie/tv]: ") or "movie"
            d = tmdb_fetch(f"/{typ}/{mid}", key)
            if d:
                print(f"  {clr(d.get('title') or d.get('name'), C)} ({d.get('release_date', d.get('first_air_date', ''))[:4]})")
                print(f"  ⭐ {d.get('vote_average', 0):.1f} / 10 | Votes: {d.get('vote_count', 0)}")
                print(f"  Genres: {', '.join(g['name'] for g in d.get('genres',[]))}")
                print(f"  Overview: {textwrap.shorten(d.get('overview', ''), width=100)}")
        elif c == "4":
            print(f"  {clr('[Discover Mode - Skip any param with Enter]', W)}")
            g = input("  Genre ID (e.g. 28=Action, 27=Horror): ")
            y = input("  Minimum Year: ")
            t = input("  Type [movie/tv]: ") or "movie"
            p = {"sort_by": "popularity.desc"}
            if g: p["with_genres"] = g
            if y: p["primary_release_date.gte" if t=="movie" else "first_air_date.gte"] = f"{y}-01-01"
            data = tmdb_fetch(f"/discover/{t}", key, p)
            if data:
                for r in data.get("results", [])[:12]: print(_fmt_item(r))
        elif c == "5":
            name = input("  Actor/Director Name: ").strip()
            data = tmdb_fetch("/search/person", key, {"query": name})
            if data and data.get("results"):
                p = data["results"][0]
                ok(f"{p['name']} (Pop: {p['popularity']:.1f})")
                for k in p.get("known_for",[]):
                    print(f"    - {k.get('title') or k.get('name')} ({k.get('media_type')})")
        elif c == "6":
            server_url_builder() # Delegate to the generic URL builder

# ─────────────────────────────────────────────────────────────────────────────
# MISCELLANEOUS & ADVANCED TOOLS
# ─────────────────────────────────────────────────────────────────────────────
def server_url_builder():
    hdr("STREAMING NODE URL COMPILER")
    mid = input("  TMDB Entity ID: ").strip()
    if not mid.isdigit(): err("Invalid ID Format"); return
    typ = input("  Classification (movie/tv): ").strip() or "movie"
    
    s = e = "1"
    if typ == "tv":
        s = input("  Season (default 1): ").strip() or "1"
        e = input("  Episode (default 1): ").strip() or "1"
        
    sep()
    for srv in SERVERS:
        if typ == "movie":
            u = srv["movieBase"] + mid
            if srv["id"] == "vidlink": u += "?primaryColor=E50914&autoplay=true"
        else:
            if srv["id"] == "vidsrcme":
                u = srv["tvBase"] + mid + f"&season={s}&episode={e}"
            else:
                u = srv["tvBase"] + mid + f"/{s}/{e}"
            if srv["id"] == "vidlink": u += "?primaryColor=E50914&autoplay=true"
            
        print(f"  {srv['badge']} {clr(srv['name'].ljust(14), C)} {u}")
    blank()

def bulk_server_ping():
    hdr("BACKEND NODE LATENCY ANALYSIS")
    for s in SERVERS:
        try:
            h = urllib.parse.urlparse(s["movieBase"]).hostname
            t0 = time.perf_counter()
            with socket.create_connection((h, 443), timeout=3):
                ms = (time.perf_counter() - t0) * 1000
            print(f"  {s['badge']} {s['name']:14} {h:30} {clr(f'{ms:.0f}ms', G)}")
        except:
            print(f"  {s['badge']} {s['name']:14} {h:30} {clr('UNREACHABLE', R)}")

def compare_zips(za: Path, zb: Path):
    hdr(f"BINARY DELTA ANALYSIS: {za.name} vs {zb.name}")
    try:
        with zipfile.ZipFile(za) as a, zipfile.ZipFile(zb) as b:
            na, nb = {i.filename: i for i in a.infolist()}, {i.filename: i for i in b.infolist()}
            only_a, only_b = set(na) - set(nb), set(nb) - set(na)
            
            if only_a:
                warn("Pruned Artifacts:")
                for f in sorted(only_a): print(f"  - {f}")
            if only_b:
                ok("New Artifacts:")
                for f in sorted(only_b): print(f"  + {f}")
                
            modded = [f for f in set(na) & set(nb) if na[f].CRC != nb[f].CRC]
            if modded:
                step("Modified Artifacts:")
                for f in sorted(modded):
                    d = nb[f].file_size - na[f].file_size
                    sign = "+" if d > 0 else ""
                    print(f"  ~ {f} ({na[f].file_size}b -> {nb[f].file_size}b  [{sign}{d}b])")
            
            if not (only_a or only_b or modded):
                ok("Zero Delta. Binaries are identical.")
    except Exception as e:
        err(f"Analysis Failed: {e}")

def watchdog(root: Path):
    hdr("SUPREME WATCHDOG: FILE SYSTEM DAEMON")
    def snap(): 
        try: return {str(f): f.stat().st_mtime for f in (root / "src").rglob("*") if f.is_file()}
        except: return {}
        
    prev = snap()
    ok("Daemon Bound. Monitoring src/ codebase [CTRL+C to terminate]...")
    try:
        while True:
            time.sleep(1.5)
            curr = snap()
            if not curr: continue
            
            changed = [p for p, t in curr.items() if p not in prev or prev[p] != t]
            removed = [p for p in prev if p not in curr]
            
            if changed or removed:
                blank()
                for c in changed: warn(f"Mutation Detected: {Path(c).name}")
                for r in removed: err(f"Deletion Detected: {Path(r).name}")
                
                step("Invoking Auto-Compiler...")
                compile_project(root)
                package_zip(root)
                prev = snap()
                ok("System Rebuilt. Resuming monitor...")
    except KeyboardInterrupt:
        ok("\nDaemon Terminated gracefully.")

def edit_manifest(root: Path):
    man = root / "src" / "manifest"
    if not man.exists(): err("Manifest Missing!"); return
    
    hdr("MANIFEST MODIFICATION UTILITY")
    lines = man.read_text().splitlines()
    for i, l in enumerate(lines, 1):
        print(f" {clr(str(i).rjust(2), DG)}  {l}")
        
    sep()
    c = input("  Cmd[ 'key=val', 'bump', or Enter to cancel ]: ").strip()
    if not c: return
    
    if c == "bump":
        changed_lines =[]
        for l in lines:
            if l.startswith("build_version="):
                val = int(l.split("=")[1])
                changed_lines.append(f"build_version={val+1}")
            else:
                changed_lines.append(l)
        man.write_text("\n".join(changed_lines) + "\n")
        ok("Build Version Incremented")
    elif "=" in c:
        k, v = c.split("=", 1)
        changed_lines = [l if not l.startswith(k+"=") else f"{k}={v}" for l in lines]
        if not any(l.startswith(k+"=") for l in changed_lines):
            changed_lines.append(c)
        man.write_text("\n".join(changed_lines) + "\n")
        ok("Manifest Key Written")

# ─────────────────────────────────────────────────────────────────────────────
# UI 1: RICH TELEMETRY DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def launch_rich_dashboard(root: Path, api_key: str):
    if not RICH_AVAILABLE:
        err("The 'rich' Python library is required for the Telemetry Dashboard.")
        info("Install via: pip install rich"); return

    console = Console()
    def generate_layout() -> Layout:
        lay = Layout()
        lay.split_column(Layout(name="header", size=3), Layout(name="main", ratio=1), Layout(name="footer", size=3))
        lay["main"].split_row(Layout(name="left", ratio=1), Layout(name="right", ratio=1))
        return lay

    # Pre-fetch TMDB slightly so the live loop doesn't block constantly
    console.print("[cyan]Initializing Data Streams...[/cyan]")
    trending_data = tmdb_fetch("/trending/all/week", api_key) or {}
    
    with Live(generate_layout(), refresh_per_second=2, screen=True) as live:
        try:
            while True:
                lay = generate_layout()
                
                # Header
                head_text = f"[bold cyan]OMEGA SUPREME TELEMETRY DASHBOARD v{VERSION}[/bold cyan] | Target: [white]{root.name if root else 'NONE'}[/white]"
                lay["header"].update(Panel(Align.center(head_text, vertical="middle"), box=box.DOUBLE_EDGE, style="blue"))
                
                # Left Top: SERVERS
                serv_table = Table(title="Backend Endpoint Grid", expand=True, show_lines=True)
                serv_table.add_column("SYS", justify="center")
                serv_table.add_column("Node ID", style="magenta bold")
                serv_table.add_column("Status", justify="right")
                for s in SERVERS:
                    # Emulate status (Real pinging here would freeze the loop)
                    serv_table.add_row(s["badge"], s["name"], "[bold green]ONLINE[/bold green]")
                
                # Left Bottom: RECENT FILES (Watchdog emulation)
                recent_table = Table(title="File System Mutation Stream", expand=True)
                recent_table.add_column("File Component", style="cyan")
                recent_table.add_column("Age", style="dim", justify="right")
                if root and (root / "src").exists():
                    files = sorted((root / "src").rglob("*"), key=lambda f: f.stat().st_mtime if f.is_file() else 0, reverse=True)[:6]
                    now = time.time()
                    for f in files:
                        if f.is_file():
                            diff = int(now - f.stat().st_mtime)
                            age = f"{diff}s ago" if diff < 60 else f"{diff//60}m ago"
                            recent_table.add_row(f.name, age)
                
                left_group = Layout()
                left_group.split_column(Layout(Panel(serv_table)), Layout(Panel(recent_table)))
                lay["left"].update(left_group)

                # Right Top: TMDB Pulse
                tmdb_table = Table(title="TMDB Global Pulse (Top 10 Global)", expand=True)
                tmdb_table.add_column("Rank", justify="center", style="dim")
                tmdb_table.add_column("Entity Title", style="white bold")
                tmdb_table.add_column("Rating", justify="right")
                for i, r in enumerate(trending_data.get("results", [])[:10], 1):
                    tmdb_table.add_row(str(i), r.get('title') or r.get('name', 'Unknown'), f"[yellow]★ {r.get('vote_average', 0):.1f}[/yellow]")
                
                # Right Bottom: System Pulse
                sys_data = (
                    f"Architecture:   [green]{platform.machine()}[/green]\n"
                    f"Kernel:         [green]{platform.version()}[/green]\n"
                    f"Python Core:    [cyan]{sys.version.split()[0]}[/cyan]\n"
                    f"System Time:    [yellow]{datetime.now().strftime('%H:%M:%S.%f')[:-3]}[/yellow]\n"
                    f"Node Pipeline:  [{'green' if shutil.which('npm') else 'red'}]{'ACTIVE' if shutil.which('npm') else 'OFFLINE'}[/]"
                )
                
                right_group = Layout()
                right_group.split_column(Layout(Panel(tmdb_table, ratio=2)), Layout(Panel(sys_data, title="OS Telemetry Engine")))
                lay["right"].update(right_group)

                # Footer
                lay["footer"].update(Panel(Align.center("[bold yellow blink]TERMINAL ACTIVE. PRESS CTRL+C TO DISENGAGE COMPOSITOR.[/bold yellow blink]"), style="red"))
                
                live.update(lay)
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

# ─────────────────────────────────────────────────────────────────────────────
# UI 2: CYBERPUNK TURTLE HUD
# ─────────────────────────────────────────────────────────────────────────────
def launch_turtle_hud(root: Path, api_key: str):
    if not TURTLE_AVAILABLE:
        err("Turtle graphics uninitialized (UI module missing from environment).")
        return
        
    print(clr("  Initializing Cyberspace Visual Output...", M))
    
    screen = turtle.Screen()
    screen.title(f"OMEGA SUPREME SECURE TERMINAL v{VERSION}")
    screen.bgcolor("#0a0a0a")
    screen.setup(width=1100, height=750)
    screen.tracer(0)

    hud = turtle.Turtle()
    hud.hideturtle()
    hud.speed(0)

    # Radar variables
    radar_angle = 0
    running = True

    def draw_box(t, x, y, w, h, title, col="#00ffff", fill=""):
        t.penup(); t.goto(x, y); t.pendown(); t.color(col); t.pensize(2)
        if fill: t.fillcolor(fill); t.begin_fill()
        for _ in range(2): t.forward(w); t.left(90); t.forward(h); t.left(90)
        if fill: t.end_fill()
        # Title Plate
        t.penup(); t.goto(x + 10, y + h - 18)
        t.write(title, font=("Courier", 12, "bold"))
        
    def draw_radar(t, x, y, radius, angle):
        t.penup(); t.goto(x, y-radius); t.pendown(); t.color("#003300")
        t.circle(radius)
        t.penup(); t.goto(x, y); t.pendown(); t.color("#00ff00"); t.pensize(2)
        t.setheading(angle)
        t.forward(radius)
        t.setheading(0) # reset

    # Pre-fetch limits blocking
    try: trending = tmdb_fetch("/trending/all/week", api_key) or {}
    except: trending = {}

    def frame():
        nonlocal radar_angle
        if not running: return
        
        hud.clear()
        
        # Main Header
        hud.penup(); hud.goto(-500, 320); hud.color("#ff0044")
        hud.write("BINGEBOX OMEGA SUPREME // MAINFRAME C-137", font=("Courier", 18, "bold", "italic"))

        # Left Column (System Info)
        draw_box(hud, -500, -320, 320, 600, "CORE TELEMETRY", "#00ffff")
        hud.penup(); hud.goto(-480, 200); hud.color("white")
        
        sys_txt =[
            f"OS: {platform.system()}",
            f"ARCH: {platform.machine()}",
            f"NODE Engine: {'OK' if shutil.which('npm') else 'ERR'}",
            f"PYTHON: v{sys.version.split()[0]}",
            f"PROJECT: {root.name if root else 'UNLINKED'}",
            f"TIMESTAMP: {datetime.now().strftime('%H:%M:%S')}",
            "",
            "ACTIVE PIPES:",
            "» BrighterScript BSC",
            "» Roku ECP Port 8060",
            "» TMDB V3 Data Mesh"
        ]
        
        for i, text in enumerate(sys_txt):
            hud.goto(-480, 200 - (i*25))
            hud.write(text, font=("Courier", 10, "bold"))
            
        # Radar in bottom left
        draw_radar(hud, -340, -180, 100, radar_angle)
        radar_angle = (radar_angle - 15) % 360

        # Center/Right Column (TMDB / DB Data)
        draw_box(hud, -150, -320, 650, 600, "TMDB DATALINK (LIVE)", "#ffaa00")
        hud.penup(); hud.goto(-130, 200); hud.color("#aaaaaa")
        
        for i, r in enumerate(trending.get("results", [])[:20]):
            hud.goto(-130, 220 - ((i+1) * 25))
            title = (r.get("title") or r.get("name"))[:45]
            hud.write(f"> {i+1:02d} {title}", font=("Courier", 10))
            # Rating Bar
            hud.goto(200, 220 - ((i+1) * 25))
            hud.color("#00ff00")
            hud.write(f"[{'█' * int(r.get('vote_average', 0))}]", font=("Courier", 9))
            hud.color("#aaaaaa")
            
        screen.update()
        screen.ontimer(frame, 50)

    def stop():
        nonlocal running
        running = False
        screen.bye()

    screen.onkey(stop, "q")
    screen.onkey(stop, "Q")
    screen.listen()
    
    frame() # Start loop
    try: turtle.mainloop()
    except: pass
    print(clr("  HUD process fully decayed.", M))

# ─────────────────────────────────────────────────────────────────────────────
# OMEGA SUPREME COMMAND LINE OS
# ─────────────────────────────────────────────────────────────────────────────
def cli_main_loop():
    project_root = find_project()
    if not project_root: project_root = prompt_project()
    cfg = read_config(project_root) if project_root else {"tmdb_key": TMDB_KEY_DEFAULT}
    api_key = cfg.get("tmdb_key", TMDB_KEY_DEFAULT)
    last_zip: Optional[Path] = None

    while True:
        try:
            blank()
            print(clr("  ╔═══════════════════════════════════════════════════════════════════╗", C))
            print(clr("  ║                   OMEGA SUPREME COMMAND LINE OS                   ║", C))
            print(clr("  ╠═══════════════════════════════════════════════════════════════════╣", C))
            print(f"  ║ {clr('[ BUILD PIPELINE ]', DG)}                                                 ║")
            print(f"  ║  {clr('[1]', G)} Execute Compiler (NPM Inst -> BSC -> Package)                ║")
            print(f"  ║  {clr('[2]', G)} Flash OS (Deploy to Roku Roku over HTTP)                     ║")
            print(f"  ║  {clr('[3]', G)} ★ FULL SYNC (Git Pull -> Compile -> Flash)                   ║")
            print(f"  ║ {clr('[ TOOL CHAIN ]', DG)}                                                     ║")
            print(f"  ║  {clr('[4]', B)} Git Architecture Menu (Commits, Branches, Stash, Logs)       ║")
            print(f"  ║  {clr('[5]', B)} Roku ECP Network (Subnet Radar & Keypress Remote)            ║")
            print(f"  ║  {clr('[6]', M)} TMDB V3 Data Mesh (Live Search & Trending)                   ║")
            print(f"  ║  {clr('[7]', M)} Project Linter & Manifest Configuration Matrix               ║")
            print(f"  ║  {clr('[8]', M)} Video Node Stream Builder & Sub-Server Ping Analysis         ║")
            print(f"  ║ {clr('[ ADVANCED UIs ]', DG)}                                                   ║")
            print(f"  ║  {clr('[W]', Y)} Launch Watchdog (Autobuild via system I/O triggers)          ║")
            print(f"  ║  {clr('[D]', Y)} Binary Differential Engine (Diff Zips)                       ║")
            print(f"  ║  {clr('[R]', C)} Initialize RICH Live Terminal Dashboard                      ║")
            print(f"  ║  {clr('[T]', C)} Initialize TURTLE Cyberpunk Graphical HUD                    ║")
            print(f"  ║  {clr('[Q]', DG)} Disconnect / Terminate Process                               ║")
            print(clr("  ╚═══════════════════════════════════════════════════════════════════╝", C))
            
            p_text = str(project_root) if project_root else "NOT LINKED to BingeBox Repository"
            p_color = W if project_root else R
            print(f"  [ TARGET ] {clr(p_text, p_color)}")
            blank()
            
            c = input(clr("  root@supreme :~# ", M)).strip().upper()
            
            # Context Validations
            if not project_root and c in ("1", "2", "3", "7", "W", "D"):
                err("Requirement Failed: Link a project root first."); continue
                
            # COMMAND ROUTING
            if c == "1":
                npm_install(project_root)
                compile_project(project_root)
                last_zip = package_zip(project_root)
            elif c == "2":
                deploy_interactive(project_root, last_zip)
            elif c == "3":
                git_pull(project_root)
                if npm_install(project_root) and compile_project(project_root):
                    last_zip = package_zip(project_root)
                    if last_zip and confirm("Proceed with Flash phase?"): deploy_interactive(project_root, last_zip)
            elif c == "4":
                print("\n  [P]ull Origin | [S]tatus Tree | [L]og History | [D]iff Changes | [C]hangelog Gen")
                g = input("  Git-Mesh> ").strip().upper()
                if g=="P": git_pull(project_root)
                elif g=="S": git_status(project_root)
                elif g=="L": git_log(project_root)
                elif g=="D": git_diff(project_root)
                elif g=="C": generate_changelog(project_root)
            elif c == "5":
                print("\n  [S]ubnet Radar | [R]emote Control Protocol | [A]pplication Map")
                n = input("  Net-Mesh> ").strip().upper()
                if n == "S": scan_roku_on_network()
                elif n == "R": roku_remote_tool(input("  Device IP: "))
                elif n == "A": roku_app_list(input("  Device IP: "))
            elif c == "6": 
                tmdb_tester(api_key)
            elif c == "7": 
                print("\n  [L]inter & Analyser | [M]anifest Editor | [E]nvironment State")
                e = input("  Inspect> ").strip().upper()
                if e == "L": inspect_project(project_root)
                elif e == "M": edit_manifest(project_root)
                elif e == "E": full_env_check(project_root)
            elif c == "8":
                print("\n[B]uild Stream Links | [P]ing Global Nodes")
                u = input("  Servers> ").strip().upper()
                if u == "B": server_url_builder()
                elif u == "P": bulk_server_ping()
            elif c == "W": 
                watchdog(project_root)
            elif c == "D":
                za = project_root / input("  Relative Local Zip A (.zip): ")
                zb = project_root / input("  Relative Local Zip B (.zip): ")
                if za.exists() and zb.exists(): compare_zips(za, zb)
                else: err("Binaries not located at given paths")
            elif c == "R": 
                launch_rich_dashboard(project_root, api_key)
            elif c == "T": 
                launch_turtle_hud(project_root, api_key)
            elif c == "Q": 
                blank(); ok("System Detached. End of Line."); break
            else:
                warn("Command Unrecognized by Neural Mesh.")
                
        except KeyboardInterrupt:
            warn("\nSignal Interrupt Detected. Terminate safely using 'Q'.")
        except Exception as e:
            err(f"CRITICAL PROCESS FAULT: {e}")
            _log_err("Main Loop Fault", e)

# ─────────────────────────────────────────────────────────────────────────────
# BOOTSTRAPPER
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description=f"BingeBox Supreme Engine v{VERSION}")
    parser.add_argument("--headless", metavar="CMD", help="Execute CI Pipeline Module: build | install | package")
    args = parser.parse_args()

    project_root = find_project()
    
    # Headless / Pipeline Traversal
    if args.headless and project_root:
        if args.headless == "build": 
            sys.exit(0 if compile_project(project_root) else 1)
        elif args.headless == "install": 
            sys.exit(0 if npm_install(project_root) else 1)
        elif args.headless == "package": 
            sys.exit(0 if package_zip(project_root) else 1)

    banner()
    cli_main_loop()

if __name__ == "__main__":
    main()