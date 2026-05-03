#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          BingeBox Omega — ULTRA Dev Tool  v4.0                             ║
║          Roku v3.0  |  python bingebox_omega.py [path]                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  BUILD       npm install · bsc compile · .zip package · Roku deploy        ║
║  GIT         pull · status · branch · stash · log · diff                  ║
║  TMDB        search · trending · details · discover · images               ║
║  TOOLS       linter · manifest editor · config viewer · URL builder        ║
║  ADVANCED    health check · diff viewer · env export · watchdog            ║
║              port scanner · telnet ECP · server ping · changelog gen       ║
║              bulk server test · asset validator · bs syntax check          ║
║              registry dump · perf benchmarks · rollback · zip diff         ║
╚══════════════════════════════════════════════════════════════════════════════╝

Requirements: Python 3.10+  (zero pip deps — pure stdlib)
Usage:
  python bingebox_omega.py
  python bingebox_omega.py /path/to/BingeBox-Roku-v2
  python bingebox_omega.py --headless build     (CI mode)
  python bingebox_omega.py --headless pipeline
"""

# ─────────────────────────────────────────────────────────────────────────────
# STDLIB IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import sys
import os
import re
import json
import zipfile
import shutil
import time
import socket
import struct
import hashlib
import base64
import threading
import subprocess
import urllib.request
import urllib.parse
import urllib.error
import http.client
import http.server
import mimetypes
import argparse
import traceback
import textwrap
import difflib
import fnmatch
import logging
import queue
import platform
import tempfile
import contextlib
import signal
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Union, Any
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM / VT100 SETUP
# ─────────────────────────────────────────────────────────────────────────────
IS_WIN  = sys.platform == "win32"
IS_MAC  = sys.platform == "darwin"
IS_LINUX= sys.platform.startswith("linux")

if IS_WIN:
    os.system("")   # enable ANSI on Windows 10+

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────────────────
R    = "\033[91m"
G    = "\033[92m"
Y    = "\033[93m"
C    = "\033[96m"
M    = "\033[95m"
W    = "\033[97m"
DG   = "\033[90m"
B    = "\033[94m"
RST  = "\033[0m"
BOLD = "\033[1m"
ULINE= "\033[4m"
BLINK= "\033[5m"

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

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING (file-based, separate from console output)
# ─────────────────────────────────────────────────────────────────────────────
LOG_FILE = Path.home() / ".bingebox_omega.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("omega")

def _log_err(context: str, exc: Exception):
    log.error(f"{context}: {exc}", exc_info=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
VERSION          = "4.0.0"
TMDB_KEY_DEFAULT = "15d2ea6d0dc1d476efbca3eba2b9bbfb"
TMDB_BASE        = "https://api.themoviedb.org/3"
TMDB_IMG_BASE    = "https://image.tmdb.org/t/p"

SERVERS: list[dict] = [
    {"id": "vidlink",    "name": "VidLink Pro",  "badge": "⚡",
     "movieBase": "https://vidlink.pro/movie/",               "tvBase": "https://vidlink.pro/tv/"},
    {"id": "vidsrcpro",  "name": "VidSrc PRO",   "badge": "🔥",
     "movieBase": "https://vidsrc.pro/embed/movie/",          "tvBase": "https://vidsrc.pro/embed/tv/"},
    {"id": "videasy",    "name": "Videasy",       "badge": "🎬",
     "movieBase": "https://player.videasy.net/movie/",        "tvBase": "https://player.videasy.net/tv/"},
    {"id": "vidsrccc",   "name": "VidSrc CC",     "badge": "🌐",
     "movieBase": "https://vidsrc.cc/v2/embed/movie/",        "tvBase": "https://vidsrc.cc/v2/embed/tv/"},
    {"id": "autoembed",  "name": "AutoEmbed",     "badge": "🤖",
     "movieBase": "https://player.autoembed.cc/embed/movie/", "tvBase": "https://player.autoembed.cc/embed/tv/"},
    {"id": "2embed",     "name": "2Embed",        "badge": "✨",
     "movieBase": "https://www.2embed.cc/embed/",             "tvBase": "https://www.2embed.cc/embedtv/"},
    {"id": "vidsrcme",   "name": "VidSrc.ME",     "badge": "💾",
     "movieBase": "https://vidsrc.me/embed/movie?tmdb=",      "tvBase": "https://vidsrc.me/embed/tv?tmdb="},
]

ROKU_ECP_PORT = 8060
DEFAULT_ROKU_PASS = "rokudev"

PROJECT_CANDIDATES: list[Path] = [
    Path.cwd() / "BingeBox-Roku-v2",
    Path.cwd() / "BingeBox_Omega_Roku_v3",
    Path.cwd(),
    Path.home() / "Desktop"   / "BingeBox-Roku-v2",
    Path.home() / "Downloads" / "BingeBox-Roku-v2",
    Path.home() / "Documents" / "BingeBox-Roku-v2",
    Path.home() / "Desktop"   / "Reoi" / "BingeBox-Roku-v2",
    Path.home() / "Downloads" / "Reoi" / "BingeBox-Roku-v2",
]

# BrightScript reserved words (for syntax checker)
BS_KEYWORDS = {
    "and","as","box","boolean","createobject","dim","double","dynamic","each",
    "else","elseif","end","endfor","endfunction","endif","endsub","endwhile",
    "exit","exitwhile","false","field","float","for","function","goto","if",
    "import","in","integer","invalid","let","line_num","longin","next","not","objfun",
    "or","print","rem","return","rnd","run","step","stop","string","sub","super",
    "tab","then","to","true","type","void","while",
}

# ─────────────────────────────────────────────────────────────────────────────
# TERMINAL UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
def terminal_width() -> int:
    try:
        return min(os.get_terminal_size().columns, 120)
    except Exception:
        return 80


def progress_bar(done: int, total: int, width: int = 30, label: str = "") -> str:
    frac = done / total if total else 0
    filled = int(width * frac)
    bar = clr("█" * filled, G) + clr("░" * (width - filled), DG)
    pct = f"{frac * 100:5.1f}%"
    return f"  [{bar}] {pct}  {label}"


def spinner(msg: str, stop_event: threading.Event, done_event: threading.Event):
    frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    i = 0
    while not stop_event.is_set():
        frame = clr(frames[i % len(frames)], C)
        sys.stdout.write(f"\r  {frame}  {msg}   ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + " " * (len(msg) + 12) + "\r")
    sys.stdout.flush()
    done_event.set()


@contextlib.contextmanager
def spin(msg: str):
    """Context manager that shows a spinner while work is happening."""
    stop = threading.Event()
    done = threading.Event()
    t = threading.Thread(target=spinner, args=(msg, stop, done), daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        done.wait(timeout=1)


def confirm(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    raw = input(f"  {prompt} {hint}: ").strip().lower()
    if not raw:
        return default
    return raw.startswith("y")


def choose_from(options: list[tuple[str, str]], prompt: str = "Choose") -> Optional[int]:
    """Display numbered menu, return 0-based index or None on cancel."""
    for i, (label, desc) in enumerate(options, 1):
        print(f"  {clr(f'[{i}]', C)} {clr(label, W):20} {clr(desc, DG)}")
    print(f"  {clr('[0]', DG)} Back / Cancel")
    raw = input(f"  {prompt}: ").strip()
    if raw == "0" or not raw:
        return None
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return idx
    except ValueError:
        pass
    warn("Invalid choice.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────────────────────────────────────
def banner():
    os.system("cls" if IS_WIN else "clear")
    art = r"""
  ██████╗ ██╗███╗   ██╗ ██████╗ ███████╗██████╗  ██████╗ ██╗  ██╗
  ██╔══██╗██║████╗  ██║██╔════╝ ██╔════╝██╔══██╗██╔═══██╗╚██╗██╔╝
  ██████╔╝██║██╔██╗ ██║██║  ███╗█████╗  ██████╔╝██║   ██║ ╚███╔╝
  ██╔══██╗██║██║╚██╗██║██║   ██║██╔══╝  ██╔══██╗██║   ██║ ██╔██╗
  ██████╔╝██║██║ ╚████║╚██████╔╝███████╗██████╔╝╚██████╔╝██╔╝ ██╗
  ╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝"""
    print(clr(art, R))
    print(clr(f"  OMEGA  ROKU v3.0  ·  Dev Tool v{VERSION}  ·  Pure Python 3.10+", Y))
    print(clr(f"  Python {sys.version.split()[0]} · {platform.system()} {platform.machine()}", DG))
    print(clr("  ─────────────────────────────────────────────────────", DG))
    blank()


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════════

def find_project() -> Optional[Path]:
    # CLI argument wins
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        p = Path(sys.argv[1])
        if (p / "package.json").exists():
            return p.resolve()
        warn(f"Provided path '{p}' has no package.json — searching elsewhere.")

    for c in PROJECT_CANDIDATES:
        if (c / "package.json").exists():
            return c.resolve()
    return None


def prompt_project() -> Optional[Path]:
    warn("Project folder not found automatically.")
    raw = input("  Enter full path to project root (Enter to skip): ").strip().strip('"\'')
    if raw:
        p = Path(raw)
        if (p / "package.json").exists():
            return p.resolve()
        err(f"No package.json at '{p}'")
    warn("No valid project path. Build/inspect features disabled.")
    return None


def read_config(root: Path) -> dict:
    """Parse TMDB key and feature flags from Config.bs."""
    result = {"tmdb_key": TMDB_KEY_DEFAULT, "features": {}}
    cfg = root / "src" / "source" / "Services" / "Config.bs"
    if not cfg.exists():
        return result
    try:
        text = cfg.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'TMDB_KEY:\s*"([a-f0-9]{32})"', text)
        if m:
            result["tmdb_key"] = m.group(1)
        flags = re.findall(r"(Enable\w+|BandwidthSaver):\s*(true|false)", text)
        result["features"] = {k: v == "true" for k, v in flags}
    except OSError as e:
        _log_err("read_config", e)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT / DEPENDENCY CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

def _run_version(cmd: list[str]) -> Optional[str]:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def check_node() -> bool:
    step("Checking Node.js / npm...")
    node = shutil.which("node")
    npm  = shutil.which("npm")
    npx  = shutil.which("npx")

    all_ok = True

    if not node:
        err("Node.js not found!")
        warn("  Install from https://nodejs.org (LTS)")
        if IS_WIN:
            warn("  Or: winget install OpenJS.NodeJS.LTS")
        elif IS_MAC:
            warn("  Or: brew install node")
        else:
            warn("  Or: sudo apt install nodejs npm")
        all_ok = False
    else:
        ver = _run_version(["node", "--version"]) or "?"
        # BUG FIX: original code crashed if check_output threw; now handled
        major = int(ver.lstrip("v").split(".")[0]) if ver != "?" else 0
        status = clr(ver, G) if major >= 16 else clr(f"{ver} (upgrade recommended, need ≥16)", Y)
        ok(f"Node.js {status}")

    if not npm:
        err("npm not found (should ship with Node.js)")
        all_ok = False
    else:
        nver = _run_version(["npm", "--version"]) or "?"
        ok(f"npm v{nver}")

    if not npx:
        warn("npx not found (fallback compiler unavailable)")
    else:
        ok(f"npx available")

    git_ok = shutil.which("git") is not None
    ok("git available") if git_ok else warn("git not found")

    return all_ok


def full_env_check(root: Optional[Path]):
    """Full system health check — tool versions, dirs, ports."""
    hdr("ENVIRONMENT HEALTH CHECK")

    check_node()
    sep()

    tools = [
        ("python3",   ["python3", "--version"]),
        ("git",       ["git",     "--version"]),
        ("curl",      ["curl",    "--version"]),
        ("node",      ["node",    "--version"]),
        ("npm",       ["npm",     "--version"]),
        ("npx",       ["npx",     "--version"]),
    ]
    step("Tool versions:")
    for name, cmd in tools:
        ver = _run_version(cmd)
        if ver:
            ok(f"{name:12} {ver.splitlines()[0][:60]}")
        else:
            warn(f"{name:12} not found")

    sep()
    step("Python stdlib modules:")
    for mod in ["json", "zipfile", "urllib", "socket", "hashlib", "threading"]:
        try:
            __import__(mod)
            ok(f"{mod}")
        except ImportError:
            err(f"{mod} MISSING")

    if root:
        sep()
        step("Project structure:")
        dirs_to_check = [
            root / "src",
            root / "src" / "components",
            root / "src" / "source" / "Services",
            root / "src" / "source" / "Utils",
            root / "node_modules",
        ]
        for d in dirs_to_check:
            label = str(d.relative_to(root))
            if d.exists():
                ok(f"{label}/")
            else:
                warn(f"{label}/ — missing")

        sep()
        step("Disk space:")
        try:
            usage = shutil.disk_usage(root)
            free_gb = usage.free / 1e9
            total_gb = usage.total / 1e9
            pct = (usage.used / usage.total) * 100
            colour = R if free_gb < 1 else Y if free_gb < 5 else G
            ok(f"Free: {clr(f'{free_gb:.1f} GB', colour)} / {total_gb:.1f} GB  ({pct:.0f}% used)")
        except Exception as e:
            warn(f"Could not read disk usage: {e}")

    sep()
    step("Internet connectivity:")
    targets = [
        ("TMDB API",    "api.themoviedb.org", 443),
        ("GitHub",      "github.com",          443),
        ("npm Registry","registry.npmjs.org",  443),
    ]
    for label, host, port in targets:
        try:
            with socket.create_connection((host, port), timeout=4):
                ok(f"{label:20} reachable")
        except Exception:
            err(f"{label:20} UNREACHABLE")

    blank()
    ok("Health check complete — see log for details")
    blank()


# ═══════════════════════════════════════════════════════════════════════════════
# NPM INSTALL
# ═══════════════════════════════════════════════════════════════════════════════

def npm_install(root: Path) -> bool:
    step("Installing npm dependencies (brighterscript + roku-deploy)...")
    if not shutil.which("npm"):
        err("npm not found — install Node.js first")
        return False

    # BUG FIX: original passed capture_output=False AND text=True simultaneously
    # which is fine for Popen but confusing. Switched to explicit stdout/stderr.
    result = subprocess.run(
        ["npm", "install"],
        cwd=root,
        stdout=None,      # stream directly to terminal
        stderr=None,
    )
    if result.returncode != 0:
        err("npm install FAILED — check output above")
        log.error(f"npm install exited {result.returncode} in {root}")
        return False
    ok("Dependencies installed successfully")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# COMPILE (BrighterScript)
# ═══════════════════════════════════════════════════════════════════════════════

def compile_project(root: Path) -> bool:
    step("Compiling BrighterScript (bsc)...")

    node_modules = root / "node_modules"
    if not node_modules.exists():
        warn("node_modules not found — running npm install first...")
        if not npm_install(root):
            return False

    # BUG FIX: original code ran bsc, on failure tried npx bsc — but silently
    # swallowed the first-run stdout/stderr (capture_output=False + text=True
    # was set on both runs which printed to terminal, fine, but result2 return
    # check was wrong: it checked result2.returncode but never assigned result2
    # if result.returncode==0 branch was taken).  Cleaned up logic here.
    t0 = time.perf_counter()

    # Primary: npm run build
    result = subprocess.run(["npm", "run", "build"], cwd=root)
    if result.returncode != 0:
        warn("npm run build failed — trying npx bsc directly...")
        result = subprocess.run(["npx", "bsc"], cwd=root)
        if result.returncode != 0:
            err("Compilation FAILED — see BrightScript errors above")
            log.error(f"bsc compile failed in {root}")
            return False

    elapsed = time.perf_counter() - t0
    staging = root / "out" / ".roku-deploy-staging"
    if staging.exists():
        file_count = sum(1 for f in staging.rglob("*") if f.is_file())
        total_kb   = sum(f.stat().st_size for f in staging.rglob("*") if f.is_file()) // 1024
        ok(f"Compiled in {elapsed:.1f}s → {file_count} files, ~{total_kb} KB")
    else:
        warn("Staging dir not created — build may have partially failed")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# PACKAGE ZIP
# ═══════════════════════════════════════════════════════════════════════════════

# BUG FIX: original generated zip names that included colons on Windows (":") via
# strftime("%H:%M") inside the filename — Windows rejects colons in filenames.
# Fixed to use safe timestamp format.
def package_zip(root: Path, use_staging: bool = True, output_dir: Optional[Path] = None) -> Optional[Path]:
    step("Packaging .zip for Roku sideload...")

    ts       = datetime.now().strftime("%Y%m%d-%H%M")   # colon-free
    zip_name = f"BingeBox-Omega-v3-{ts}.zip"
    out_dir  = output_dir or root
    zip_path = out_dir / zip_name

    staging = root / "out" / ".roku-deploy-staging"
    src_dir  = root / "src"

    if use_staging and staging.exists():
        base = staging
        ok("Using compiled staging dir")
    elif src_dir.exists():
        base = src_dir
        warn("Staging dir not found — packaging raw src/ (uncompiled)")
    else:
        err("Neither staging nor src/ found. Run compile first.")
        return None

    # Collect files and show progress
    all_files = sorted(f for f in base.rglob("*") if f.is_file())
    total = len(all_files)
    if total == 0:
        err("Source directory is empty — nothing to package")
        return None

    checksums: dict[str, str] = {}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for i, f in enumerate(all_files, 1):
            arc = f.relative_to(base)
            zf.write(f, arc)
            data = f.read_bytes()
            checksums[str(arc)] = hashlib.md5(data).hexdigest()
            sys.stdout.write(f"\r{progress_bar(i, total, label=f.name[:30])}")
            sys.stdout.flush()

    sys.stdout.write("\r" + " " * 80 + "\r")
    size_kb = zip_path.stat().st_size // 1024

    # Write checksum manifest alongside zip
    cksum_path = zip_path.with_suffix(".md5")
    cksum_path.write_text(
        "\n".join(f"{v}  {k}" for k, v in sorted(checksums.items())) + "\n"
    )

    ok(f"Package: {zip_path.name}  ({size_kb} KB, {total} files)")
    ok(f"Checksums: {cksum_path.name}")
    info(f"Full path: {zip_path}")
    log.info(f"Packaged {total} files → {zip_path}  ({size_kb} KB)")
    return zip_path


def compare_zips(zip_a: Path, zip_b: Path):
    """Show what changed between two Roku zip packages."""
    hdr(f"ZIP DIFF: {zip_a.name}  vs  {zip_b.name}")
    try:
        with zipfile.ZipFile(zip_a) as za, zipfile.ZipFile(zip_b) as zb:
            names_a = {i.filename: i for i in za.infolist()}
            names_b = {i.filename: i for i in zb.infolist()}

            only_a = sorted(set(names_a) - set(names_b))
            only_b = sorted(set(names_b) - set(names_a))
            both   = sorted(set(names_a) & set(names_b))

            if only_a:
                warn(f"Removed ({len(only_a)}):")
                for n in only_a:
                    info(f"  − {n}")
            if only_b:
                ok(f"Added ({len(only_b)}):")
                for n in only_b:
                    info(f"  + {n}")

            changed = []
            for n in both:
                if names_a[n].CRC != names_b[n].CRC:
                    changed.append(n)
            if changed:
                warn(f"Modified ({len(changed)}):")
                for n in changed:
                    sa = names_a[n].file_size
                    sb = names_b[n].file_size
                    delta = sb - sa
                    sign = "+" if delta >= 0 else ""
                    info(f"  ~ {n}  ({sa}B → {sb}B  {sign}{delta}B)")

            if not (only_a or only_b or changed):
                ok("Packages are IDENTICAL")
    except Exception as e:
        err(f"Zip diff failed: {e}")
        _log_err("compare_zips", e)


def list_zip_contents(zip_path: Path):
    """Print a detailed listing of a zip file."""
    hdr(f"ZIP CONTENTS: {zip_path.name}")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            infos = sorted(zf.infolist(), key=lambda x: x.filename)
            total_raw = 0
            total_comp = 0
            for info_ in infos:
                ratio = (1 - info_.compress_size / info_.file_size) * 100 if info_.file_size else 0
                print(f"  {clr(info_.filename, C):60} "
                      f"{info_.file_size:>8,}B → {info_.compress_size:>8,}B "
                      f"{clr(f'{ratio:.0f}%', DG)}")
                total_raw  += info_.file_size
                total_comp += info_.compress_size
            sep()
            total_ratio = (1 - total_comp / total_raw) * 100 if total_raw else 0
            ok(f"Total: {len(infos)} files, {total_raw:,} B raw → {total_comp:,} B compressed ({total_ratio:.1f}% saved)")
    except Exception as e:
        err(f"Cannot read zip: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# ROKU DEPLOY  (HTTP multipart — no CLI dependency)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_multipart(zip_path: Path) -> tuple[bytes, str]:
    """Build a properly-encoded multipart/form-data body."""
    boundary = f"BingeBoxOmegaBoundary{int(time.time())}"
    CRLF = b"\r\n"

    def field(name: str, value: str) -> bytes:
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode("utf-8")

    zip_data = zip_path.read_bytes()

    # BUG FIX: original code concatenated string parts + bytes without encoding
    # the string parts first, which raised TypeError on Python 3. Fixed here by
    # building everything as bytes from the start.
    file_header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="archive"; filename="{zip_path.name}"\r\n'
        f"Content-Type: application/zip\r\n\r\n"
    ).encode("utf-8")

    closer = f"\r\n--{boundary}--\r\n".encode("utf-8")

    body = field("mysubmit", "Install") + file_header + zip_data + closer
    return body, boundary


def deploy_to_roku(zip_path: Path, roku_ip: str, roku_pass: str, timeout: int = 60) -> bool:
    step(f"Deploying to Roku at {roku_ip}...")
    url = f"http://{roku_ip}/plugin_install"

    body, boundary = _build_multipart(zip_path)
    size_mb = len(body) / 1e6

    credentials = base64.b64encode(f"rokudev:{roku_pass}".encode()).decode()

    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Basic {credentials}")
    req.add_header("Content-Length", str(len(body)))
    req.add_header("User-Agent", f"BingeBoxOmega/{VERSION}")

    info(f"Upload size: {size_mb:.2f} MB")
    t0 = time.perf_counter()

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read().decode("utf-8", errors="replace")
            elapsed   = time.perf_counter() - t0

            # BUG FIX: original checked "Install Success" which is not always
            # present on newer Roku firmware. Broaden to also accept HTTP 200
            # with no error keywords.
            success_keywords = ["Install Success", "Packaged", "Application Installed"]
            failure_keywords = ["failed", "error", "invalid"]

            body_lower = resp_body.lower()
            if any(k.lower() in body_lower for k in failure_keywords):
                err(f"Roku reported an error (HTTP {resp.status}):")
                info(resp_body[:300])
                return False
            elif resp.getcode() == 200 or any(k in resp_body for k in success_keywords):
                ok(f"Deployed in {elapsed:.1f}s to Roku at {roku_ip}!")
                log.info(f"Deploy success → {roku_ip}  ({elapsed:.1f}s)")
                return True
            else:
                warn(f"Ambiguous response (HTTP {resp.getcode()})")
                info(resp_body[:200])
                return False

    except urllib.error.HTTPError as e:
        if e.code == 401:
            err("Authentication failed — wrong dev password?")
            warn(f"Default password is '{DEFAULT_ROKU_PASS}' — set in Roku Dev Mode settings")
        else:
            err(f"HTTP {e.code}: {e.reason}")
        _log_err("deploy_to_roku", e)
        return False
    except urllib.error.URLError as e:
        err(f"Cannot reach Roku at {roku_ip}")
        warn("  • Is Roku in Developer Mode? (Settings → System → Advanced → Developer mode)")
        warn("  • Are you on the same Wi-Fi network?")
        warn(f"  • Error: {e.reason}")
        _log_err("deploy_to_roku", e)
        return False
    except TimeoutError:
        err(f"Deploy timed out after {timeout}s — is the Roku responsive?")
        return False
    except Exception as e:
        err(f"Deploy failed: {e}")
        _log_err("deploy_to_roku", e)
        return False


def deploy_interactive(root: Path, zip_path: Optional[Path] = None):
    blank()
    print(clr("  ┌─ ROKU DEVICE DEPLOY ─────────────────────────────────┐", M))
    print(clr("  │  Roku must be in DEV MODE:                           │", M))
    print(clr("  │  Settings → System → Advanced → Developer mode       │", M))
    print(clr("  └──────────────────────────────────────────────────────┘", M))
    blank()

    roku_ip = input("  Roku device IP (e.g. 192.168.1.50) or Enter to cancel: ").strip()
    if not roku_ip:
        warn("Deploy cancelled.")
        return

    # Validate IP/hostname format loosely
    # BUG FIX: original accepted anything including empty strings which caused
    # confusing errors later; now validate before proceeding.
    ip_pattern = re.compile(
        r"^(\d{1,3}\.){3}\d{1,3}$|^[a-zA-Z0-9._-]+$"
    )
    if not ip_pattern.match(roku_ip):
        err(f"'{roku_ip}' doesn't look like a valid IP or hostname")
        return

    roku_pass = input(f"  Roku dev password (default: {DEFAULT_ROKU_PASS}): ").strip() or DEFAULT_ROKU_PASS

    if zip_path is None or not zip_path.exists():
        warn("No zip found — packaging now...")
        zip_path = package_zip(root)
        if zip_path is None:
            return

    deploy_to_roku(zip_path, roku_ip, roku_pass)


# ═══════════════════════════════════════════════════════════════════════════════
# ROKU ECP (External Control Protocol)
# ═══════════════════════════════════════════════════════════════════════════════

def roku_ecp(roku_ip: str, path: str, method: str = "GET", body: bytes = b"") -> Optional[str]:
    """Send an ECP command to the Roku and return the response text."""
    try:
        conn = http.client.HTTPConnection(roku_ip, ROKU_ECP_PORT, timeout=5)
        conn.request(method, path, body)
        resp = conn.getresponse()
        data = resp.read().decode("utf-8", errors="replace")
        conn.close()
        return data
    except Exception as e:
        _log_err(f"roku_ecp {path}", e)
        return None


def roku_remote_tool(roku_ip: str):
    """Interactive ECP remote control."""
    hdr("ROKU ECP REMOTE CONTROL")
    info(f"Target: {roku_ip}:{ROKU_ECP_PORT}")
    blank()

    # Check device info first
    info_xml = roku_ecp(roku_ip, "/query/device-info")
    if not info_xml:
        err(f"Cannot reach Roku at {roku_ip}:{ROKU_ECP_PORT}")
        return

    # Parse friendly name
    name_m = re.search(r"<friendly-device-name>([^<]+)</friendly-device-name>", info_xml)
    model_m = re.search(r"<model-name>([^<]+)</model-name>", info_xml)
    sw_m    = re.search(r"<software-version>([^<]+)</software-version>", info_xml)
    if name_m:
        ok(f"Connected to: {name_m.group(1)}")
    if model_m:
        info(f"Model: {model_m.group(1)}")
    if sw_m:
        info(f"Firmware: {sw_m.group(1)}")

    sep()
    KEYS = {
        "h": "Home",         "b": "Back",         "u": "Up",
        "d": "Down",         "l": "Left",          "r": "Right",
        "s": "Select",       "p": "Play",          "f": "Fwd",
        "v": "Rev",          "i": "Info",          "x": "Search",
        "m": "InstantReplay","n": "VolumeUp",      "z": "VolumeDown",
        "0": "VolumeUp", "9": "VolumeDown",
    }
    print("  Key map:")
    for k, v in KEYS.items():
        print(f"    {clr(k, C)} → {v}")
    print(f"  {clr('q', DG)} → Quit remote")
    blank()

    while True:
        raw = input("  Key: ").strip().lower()
        if raw == "q":
            break
        key = KEYS.get(raw)
        if not key:
            warn(f"Unknown key '{raw}'")
            continue
        result = roku_ecp(roku_ip, f"/keypress/{key}", method="POST")
        if result is not None:
            ok(f"Sent: {key}")
        else:
            err(f"Failed to send: {key}")


def roku_app_list(roku_ip: str):
    """List installed apps on the Roku."""
    hdr("ROKU INSTALLED APPS")
    xml = roku_ecp(roku_ip, "/query/apps")
    if not xml:
        err(f"Cannot reach Roku at {roku_ip}:{ROKU_ECP_PORT}")
        return
    apps = re.findall(r'<app id="([^"]+)"[^>]*>([^<]+)</app>', xml)
    if not apps:
        warn("No apps found or unable to parse response")
        return
    ok(f"{len(apps)} installed apps:")
    sep()
    for app_id, name in sorted(apps, key=lambda x: x[1].lower()):
        print(f"  {clr(app_id.ljust(12), DG)} {name}")


def scan_roku_on_network(subnet: str = ""):
    """Scan local subnet for Roku devices via ECP."""
    hdr("ROKU NETWORK SCANNER")
    if not subnet:
        # Guess local subnet
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            subnet = ".".join(local_ip.split(".")[:3])
        except Exception:
            subnet = "192.168.1"

    info(f"Scanning {subnet}.1-254 on port {ROKU_ECP_PORT} (this may take ~30s)...")
    blank()

    found: list[str] = []
    results: queue.Queue = queue.Queue()

    def probe(ip: str):
        try:
            with socket.create_connection((ip, ROKU_ECP_PORT), timeout=0.3):
                results.put(ip)
        except Exception:
            pass

    threads = []
    for i in range(1, 255):
        ip = f"{subnet}.{i}"
        t = threading.Thread(target=probe, args=(ip,), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=2)

    while not results.empty():
        ip = results.get()
        xml = roku_ecp(ip, "/query/device-info")
        if xml:
            name_m = re.search(r"<friendly-device-name>([^<]+)</friendly-device-name>", xml)
            name = name_m.group(1) if name_m else "Roku Device"
            ok(f"{ip:16}  {name}")
            found.append(ip)

    if not found:
        warn("No Roku devices found on subnet")
    else:
        ok(f"Found {len(found)} device(s)")
    return found


# ═══════════════════════════════════════════════════════════════════════════════
# GIT TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def _git(root: Path, args: list[str], stream: bool = True) -> Optional[subprocess.CompletedProcess]:
    """Run a git command, return result or None on failure."""
    if not shutil.which("git"):
        err("git not found. Install from https://git-scm.com")
        return None
    repo = root if (root / ".git").exists() else (root.parent if (root.parent / ".git").exists() else None)
    if not repo:
        warn("No .git directory found — is this a cloned repo?")
        return None
    return subprocess.run(
        ["git"] + args,
        cwd=repo,
        stdout=None if stream else subprocess.PIPE,
        stderr=None if stream else subprocess.PIPE,
        text=True,
    )


def git_pull(root: Path):
    step("Pulling latest from GitHub...")
    r = _git(root, ["pull"])
    if r and r.returncode == 0:
        ok("Git pull complete")
    elif r:
        err("Git pull failed — check remote / branch / credentials")


def git_status(root: Path):
    hdr("GIT STATUS")
    r = _git(root, ["status", "--short", "--branch"])
    if r and r.returncode != 0:
        err("git status failed")


def git_log(root: Path, n: int = 15):
    hdr("GIT LOG")
    r = _git(root, [
        "log", f"-{n}",
        "--pretty=format:%C(yellow)%h%Creset  %C(cyan)%ad%Creset  %s  %C(dim)%an%Creset",
        "--date=short",
    ])
    if r and r.returncode != 0:
        err("git log failed")


def git_diff(root: Path):
    hdr("GIT DIFF (staged + unstaged)")
    r = _git(root, ["diff", "HEAD"])
    if r and r.returncode != 0:
        err("git diff failed")


def git_stash(root: Path):
    hdr("GIT STASH")
    opts = [
        ("push",  "Stash current changes"),
        ("pop",   "Pop last stash"),
        ("list",  "List all stashes"),
        ("drop",  "Drop last stash"),
    ]
    idx = choose_from([(o, d) for o, d in opts], "Stash action")
    if idx is None:
        return
    cmd = opts[idx][0]
    r = _git(root, ["stash", cmd])
    if r and r.returncode == 0:
        ok(f"git stash {cmd} complete")
    elif r:
        err(f"git stash {cmd} failed")


def git_branch_manager(root: Path):
    hdr("GIT BRANCH MANAGER")
    opts = [
        ("list",    "List all branches"),
        ("new",     "Create new branch"),
        ("switch",  "Switch branch"),
        ("delete",  "Delete branch"),
        ("merge",   "Merge branch into current"),
    ]
    idx = choose_from([(o, d) for o, d in opts], "Branch action")
    if idx is None:
        return

    action = opts[idx][0]
    if action == "list":
        _git(root, ["branch", "-a"])
    elif action == "new":
        name = input("  New branch name: ").strip()
        if name:
            r = _git(root, ["checkout", "-b", name])
            if r and r.returncode == 0:
                ok(f"Created and switched to '{name}'")
    elif action == "switch":
        name = input("  Branch to switch to: ").strip()
        if name:
            r = _git(root, ["checkout", name])
            if r and r.returncode == 0:
                ok(f"Switched to '{name}'")
    elif action == "delete":
        name = input("  Branch to delete: ").strip()
        if name and confirm(f"Delete branch '{name}'?", default=False):
            r = _git(root, ["branch", "-d", name])
            if r and r.returncode == 0:
                ok(f"Deleted '{name}'")
    elif action == "merge":
        name = input("  Branch to merge: ").strip()
        if name:
            r = _git(root, ["merge", name])
            if r and r.returncode == 0:
                ok(f"Merged '{name}'")


def generate_changelog(root: Path):
    """Generate a CHANGELOG.md from git log."""
    hdr("CHANGELOG GENERATOR")
    r = _git(root, [
        "log", "--pretty=format:%ad|%s|%an",
        "--date=short",
    ], stream=False)
    if not r or r.returncode != 0:
        err("Cannot generate changelog — git log failed")
        return

    lines_by_date: dict[str, list[str]] = defaultdict(list)
    for raw in r.stdout.strip().splitlines():
        parts = raw.split("|", 2)
        if len(parts) == 3:
            date, subject, author = parts
            lines_by_date[date].append(f"- {subject} _{author}_")

    out: list[str] = ["# CHANGELOG\n"]
    for date in sorted(lines_by_date, reverse=True):
        out.append(f"\n## {date}")
        out.extend(lines_by_date[date])

    changelog = root / "CHANGELOG.md"
    changelog.write_text("\n".join(out) + "\n")
    ok(f"Changelog written to {changelog}")
    info(f"{sum(len(v) for v in lines_by_date.values())} commits across {len(lines_by_date)} dates")


# ═══════════════════════════════════════════════════════════════════════════════
# FULL PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def full_pipeline(root: Path, headless: bool = False):
    blank()
    print(clr("  ════════ FULL PIPELINE ════════════════════════════════", Y))
    print("  Pull → Install → Compile → Package → Deploy")
    sep()

    t_start = time.perf_counter()
    steps_done: list[str] = []

    def run_step(name: str, fn) -> bool:
        nonlocal steps_done
        ok_flag = fn()
        if ok_flag:
            steps_done.append(name)
        return ok_flag

    if not run_step("git pull", lambda: (_git(root, ["pull"]) or object()).__class__.__name__ != "NoneType"):
        # git pull isn't fatal — continue
        pass
    steps_done.append("git pull")

    if not run_step("npm install", lambda: npm_install(root)):
        err("Pipeline stopped at npm install.")
        return

    if not run_step("bsc compile", lambda: compile_project(root)):
        err("Pipeline stopped at compile.")
        return

    zip_path = package_zip(root)
    if zip_path is None:
        err("Pipeline stopped at packaging.")
        return
    steps_done.append("package zip")

    if not headless:
        blank()
        if confirm("Deploy to Roku now?"):
            deploy_interactive(root, zip_path)
            steps_done.append("deploy")
    else:
        warn("Headless mode: skipping deploy (run manually)")

    elapsed = time.perf_counter() - t_start
    blank()
    sep("═")
    ok(f"Pipeline complete in {elapsed:.1f}s:  {' → '.join(steps_done)}")
    sep("═")


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT LINTER / INSPECTOR
# ═══════════════════════════════════════════════════════════════════════════════

# BUG FIX: original linter only checked components/ at root level of that dir
# (glob("*.xml")), missing nested components. Changed to rglob.
# Also: original listed issues but never printed line numbers. Now we do.

_LINT_RULES = [
    (r"console\.log\b",                 "JS console.log found (invalid in BrightScript)"),
    (r"\blocalhost\b",                  "Hardcoded localhost URL"),
    (r"\b127\.0\.0\.1\b",               "Hardcoded loopback IP"),
    (r"sandbox\s*=",                    "sandbox= attribute detected"),
    (r"(?i)\bTODO\b",                   "TODO comment"),
    (r"(?i)\bFIXME\b",                  "FIXME comment"),
    (r"(?i)\bHACK\b",                   "HACK comment"),
    (r'"password"\s*:',                 "Possible plaintext password"),
    (r'api_key\s*=\s*"[^"]{8,}"',       "Possible hardcoded API key"),
    (r'\bprint\s+"',                     "Naked print statement (use Logger)"),
    (r"(?i)http://(?!localhost)",        "Non-HTTPS URL"),
    (r"\bCreateObject\s*\(\s*\"roArray\"\s*\)", "Use [] literal instead of CreateObject(\"roArray\")"),
]

def _lint_file(path: Path, root: Path) -> list[dict]:
    """Return list of {line, col, rule, text} issues for one file."""
    issues = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for lineno, line in enumerate(lines, 1):
            for pattern, msg in _LINT_RULES:
                m = re.search(pattern, line)
                if m:
                    issues.append({
                        "file": str(path.relative_to(root)),
                        "line": lineno,
                        "col":  m.start() + 1,
                        "msg":  msg,
                        "text": line.strip(),
                    })
    except OSError:
        pass
    return issues


def inspect_project(root: Path):
    step("Inspecting & linting project...")
    sep()
    issues: list[str] = []
    lint_hits: list[dict] = []

    # ── Manifest ──────────────────────────────────────────────────────────────
    manifest = root / "src" / "manifest"
    if manifest.exists():
        ok("manifest found")
        required_keys = [
            "title", "major_version", "minor_version", "build_version",
            "mm_icon_focus_hd", "splash_screen_hd", "ui_resolutions",
        ]
        mtext = manifest.read_text()
        for key in required_keys:
            if re.search(rf"^{key}=", mtext, re.MULTILINE):
                info(f"  ✓ {key}")
            else:
                warn(f"  ✗ {key} MISSING")
                issues.append(f"manifest: missing {key}")
    else:
        err("manifest MISSING — Roku will reject the package!")
        issues.append("manifest missing")

    sep()

    # ── Components ────────────────────────────────────────────────────────────
    comp_dir = root / "src" / "components"
    if comp_dir.exists():
        xml_files = sorted(comp_dir.rglob("*.xml"))
        bs_stems  = {f.stem for f in comp_dir.rglob("*.bs")}
        ok(f"Components: {len(xml_files)} XML files")
        for xf in xml_files:
            if xf.stem in bs_stems:
                ok(f"  {xf.stem}.xml ↔ {xf.stem}.bs")
            else:
                warn(f"  {xf.stem}.xml — NO matching .bs file!")
                issues.append(f"Missing .bs for {xf.stem}.xml")
    else:
        err("src/components/ missing!")
        issues.append("components dir missing")

    sep()

    # ── Services / Utils ──────────────────────────────────────────────────────
    for sub in ["Services", "Utils"]:
        d = root / "src" / "source" / sub
        if d.exists():
            files = [f.name for f in d.rglob("*.bs")]
            ok(f"{sub}/: {files}")
        else:
            err(f"src/source/{sub}/ MISSING!")
            issues.append(f"{sub} dir missing")

    sep()

    # ── package.json ──────────────────────────────────────────────────────────
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
        except json.JSONDecodeError as e:
            err(f"package.json is invalid JSON: {e}")
            issues.append("package.json invalid JSON")
            data = {}
        deps = {**data.get("devDependencies", {}), **data.get("dependencies", {})}
        ok("package.json dependencies:")
        for k, v in deps.items():
            info(f"  {k}: {v}")
        for must_have in ["brighterscript"]:
            if must_have not in deps:
                warn(f"{must_have} not in dependencies!")
                issues.append(f"{must_have} missing from package.json")
    else:
        err("package.json not found!")
        issues.append("package.json missing")

    sep()

    # ── bsconfig.json ─────────────────────────────────────────────────────────
    bsconfig = root / "bsconfig.json"
    if bsconfig.exists():
        try:
            bc = json.loads(bsconfig.read_text())
            ok("bsconfig.json valid")
            for k, v in bc.items():
                info(f"  {k}: {v}")
        except json.JSONDecodeError as e:
            err(f"bsconfig.json invalid JSON: {e}")
            issues.append("bsconfig.json invalid")
    else:
        warn("bsconfig.json not found (using defaults)")

    sep()

    # ── Full-file lint (with line numbers) ────────────────────────────────────
    step(f"Scanning all .bs files for {len(_LINT_RULES)} lint rules...")
    all_bs = list((root / "src").rglob("*.bs"))
    ok(f"{len(all_bs)} .bs files found")

    for f in all_bs:
        hits = _lint_file(f, root)
        lint_hits.extend(hits)

    if lint_hits:
        blank()
        warn(f"{len(lint_hits)} lint issue(s):")
        sep()
        for hit in lint_hits:
            print(
                f"  {clr(hit['file'], C)}:{clr(str(hit['line']), Y)} col {hit['col']}\n"
                f"    {clr(hit['msg'], R)}\n"
                f"    {clr(hit['text'][:80], DG)}"
            )
            issues.append(f"{hit['file']}:{hit['line']} — {hit['msg']}")
    else:
        ok("No lint issues found")

    sep()

    # ── Asset check ───────────────────────────────────────────────────────────
    step("Checking manifest-referenced image assets...")
    if manifest.exists():
        mtext = manifest.read_text()
        img_refs = re.findall(r"pkg:/images/([^\s]+)", mtext)
        img_dir  = root / "src" / "images"
        for img in img_refs:
            img_path = img_dir / img
            if img_path.exists():
                ok(f"{img}")
            else:
                err(f"{img} — FILE MISSING!")
                issues.append(f"Missing image asset: {img}")

    sep()
    blank()
    if issues:
        err(f"{len(issues)} issue(s) found:")
        for i in issues:
            info(f"  • {i}")
    else:
        ok("All checks passed — project looks clean!")
    blank()

    # Export report
    if confirm("Export lint report to lint_report.txt?", default=False):
        report = root / "lint_report.txt"
        lines = [f"BingeBox Omega Lint Report — {datetime.now().isoformat()}\n\n"]
        for issue in issues:
            lines.append(f"  - {issue}\n")
        report.write_text("".join(lines))
        ok(f"Report saved to {report}")


def bs_syntax_check(root: Path):
    """Quick BrightScript syntax sanity checker (no BSC needed)."""
    hdr("BRIGHTSCRIPT SYNTAX CHECKER")
    all_bs = list((root / "src").rglob("*.bs"))
    if not all_bs:
        warn("No .bs files found")
        return

    errors: list[str] = []
    for f in all_bs:
        text = f.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        rel   = str(f.relative_to(root))

        # Check for mismatched sub/end sub and function/end function
        depth_sub = 0
        depth_fn  = 0
        for ln, line in enumerate(lines, 1):
            stripped = line.strip().lower()
            if re.match(r"\bsub\b", stripped) and "end sub" not in stripped:
                depth_sub += 1
            if re.match(r"\bfunction\b", stripped) and "end function" not in stripped:
                depth_fn += 1
            if stripped == "end sub":
                depth_sub -= 1
            if stripped == "end function":
                depth_fn -= 1
            # Check for JS-style let/const (illegal in BS)
            if re.match(r"(let|const)\s+\w+", stripped):
                errors.append(f"{rel}:{ln}  JS-style '{stripped[:40]}' — use dim/assignment")
            # Check for JS arrow functions
            if "=>" in line:
                errors.append(f"{rel}:{ln}  Arrow function '=>' is invalid in BrightScript")

        if depth_sub != 0:
            errors.append(f"{rel}  Mismatched sub/end sub (imbalance: {depth_sub})")
        if depth_fn != 0:
            errors.append(f"{rel}  Mismatched function/end function (imbalance: {depth_fn})")

    if errors:
        err(f"{len(errors)} syntax issue(s):")
        for e_ in errors:
            print(f"  {clr('!', Y)} {e_}")
    else:
        ok(f"No syntax issues in {len(all_bs)} .bs files")


# ═══════════════════════════════════════════════════════════════════════════════
# TMDB API
# ═══════════════════════════════════════════════════════════════════════════════

def tmdb_fetch(endpoint: str, api_key: str, params: dict | None = None) -> Optional[dict]:
    """Fetch from TMDB API; returns parsed JSON or None."""
    base_params = {"api_key": api_key, "language": "en-US"}
    if params:
        base_params.update(params)
    sep_char = "&" if "?" in endpoint else "?"
    qs  = urllib.parse.urlencode(base_params)
    url = f"{TMDB_BASE}{endpoint}{sep_char}{qs}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"BingeBoxOmega/{VERSION}"})
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        err(f"TMDB HTTP {e.code}: {endpoint}")
        if e.code == 401:
            warn("Invalid API key")
        elif e.code == 404:
            warn("Endpoint or resource not found")
        _log_err(f"tmdb_fetch {endpoint}", e)
        return None
    except Exception as e:
        err(f"TMDB error: {e}")
        _log_err(f"tmdb_fetch {endpoint}", e)
        return None


def _fmt_item(item: dict) -> str:
    title  = item.get("title") or item.get("name") or "?"
    mid    = item.get("id", "?")
    mtype  = item.get("media_type", "?")
    year   = (item.get("release_date") or item.get("first_air_date") or "")[:4]
    rating = item.get("vote_average", 0)
    return (
        f"  {clr(str(mid).ljust(9), Y)}"
        f"{clr(title.ljust(44), W)}"
        f"{clr(mtype.ljust(8), DG)}"
        f"{year}  {clr(f'⭐{rating:.1f}', M)}"
    )


def tmdb_tester(api_key: str):
    step("TMDB API Live Tester")
    info(f"Key: {api_key[:8]}...{api_key[-4:]}")
    sep()

    # BUG FIX: original didn't handle the case where the API key is invalid
    # gracefully — now surfaces the error type clearly.
    data = tmdb_fetch("/configuration", api_key)
    if data:
        ok("API key VALID — connection successful")
        img_sizes = data.get("images", {}).get("poster_sizes", [])
        info(f"Poster sizes: {', '.join(img_sizes)}")
    else:
        err("API key failed or no internet")
        return

    while True:
        blank()
        print(clr("  ┌─ TMDB TESTER ──────────────────────────────────────┐", C))
        print(f"  │  {clr('[1]', C)} Search movie/show by name                     │")
        print(f"  │  {clr('[2]', C)} Browse home-row endpoints                     │")
        print(f"  │  {clr('[3]', C)} Trending this week                            │")
        print(f"  │  {clr('[4]', C)} Get details by TMDB ID                        │")
        print(f"  │  {clr('[5]', C)} Discover (filter by genre/year/rating)         │")
        print(f"  │  {clr('[6]', C)} Person / cast lookup                          │")
        print(f"  │  {clr('[7]', C)} Generate all embed URLs for an item           │")
        print(f"  │  {clr('[B]', DG)} Back                                          │")
        print(clr("  └───────────────────────────────────────────────────────┘", C))
        blank()

        c = input("  Choose: ").strip().upper()
        if c == "B":
            break

        if c == "1":
            q = input("  Search: ").strip()
            if not q:
                continue
            data = tmdb_fetch(f"/search/multi", api_key, {"query": q})
            if not data:
                continue
            sep()
            results = data.get("results", [])
            if not results:
                warn("No results")
            for item in results[:10]:
                print(_fmt_item(item))

        elif c == "2":
            endpoints = [
                ("/trending/all/week",                                                 "Trending"),
                ("/movie/popular",                                                     "Popular Movies"),
                ("/movie/now_playing",                                                 "Now Playing"),
                ("/movie/top_rated",                                                   "Top Rated Movies"),
                ("/tv/top_rated",                                                      "Top Rated TV"),
                ("/tv/popular",                                                        "Popular TV"),
                ("/tv/airing_today",                                                   "Airing Today"),
                ("/discover/movie?with_genres=28&sort_by=popularity.desc",             "Action"),
                ("/discover/movie?with_genres=27&sort_by=popularity.desc",             "Horror"),
                ("/discover/tv?with_genres=16&sort_by=popularity.desc",                "Anime"),
                ("/discover/movie?vote_average.gte=7.5&vote_count.gte=1000&sort_by=vote_average.desc", "Hidden Gems"),
            ]
            idx = choose_from([(label, ep[:40]) for ep, label in endpoints])
            if idx is None:
                continue
            ep, label = endpoints[idx]
            data = tmdb_fetch(ep, api_key)
            if not data:
                continue
            results = data.get("results", [])
            ok(f"{len(results)} items in '{label}'")
            sep()
            for item in results[:12]:
                print(_fmt_item(item))

        elif c == "3":
            data = tmdb_fetch("/trending/all/week", api_key)
            if not data:
                continue
            ok("Trending this week:")
            sep()
            for i, item in enumerate(data.get("results", [])[:10], 1):
                title = item.get("title") or item.get("name") or "?"
                mtype = item.get("media_type", "?")
                rating = item.get("vote_average", 0)
                print(f"  {clr(str(i).rjust(2), M)}.  {clr(title.ljust(44), W)} [{mtype}]  ⭐{rating:.1f}")

        elif c == "4":
            mid   = input("  TMDB ID: ").strip()
            if not mid.isdigit():
                err("TMDB ID must be a number")
                continue
            mtype = input("  Type [movie/tv] (default: movie): ").strip() or "movie"
            data  = tmdb_fetch(f"/{mtype}/{mid}", api_key)
            if not data:
                continue
            sep()
            title    = data.get("title") or data.get("name") or "?"
            tagline  = data.get("tagline", "")
            rating   = data.get("vote_average", 0)
            votes    = data.get("vote_count", 0)
            overview = data.get("overview", "")
            year     = (data.get("release_date") or data.get("first_air_date") or "")[:4]
            genres   = ", ".join(g["name"] for g in data.get("genres", []))
            runtime  = data.get("runtime") or data.get("episode_run_time", [None])[0]

            ok(f"{title} ({year})")
            if tagline:
                info(f'"{tagline}"')
            info(f"⭐ {rating:.1f}/10  ({votes:,} votes)")
            info(f"Genres: {genres}")
            if runtime:
                info(f"Runtime: {runtime} min")
            sep()
            # Word-wrap overview to 70 chars
            for line in textwrap.wrap(overview, 70):
                info(line)

            # Embed URLs
            blank()
            if confirm("Show embed URLs for this item?", default=False):
                for srv in SERVERS:
                    url = build_embed_url(str(mid), mtype, srv)
                    print(f"  {clr(srv['badge'], W)} {clr(srv['name'].ljust(14), C)} {url}")

        elif c == "5":
            blank()
            print(f"  {clr('Discover filters (press Enter to skip any):', W)}")
            genre_id = input("  Genre ID (e.g. 28=Action, 35=Comedy, 27=Horror): ").strip()
            min_year = input("  Min release year (e.g. 2000): ").strip()
            max_year = input("  Max release year (e.g. 2024): ").strip()
            min_rating = input("  Min rating (e.g. 7.0): ").strip()
            mtype  = input("  Type [movie/tv] (default: movie): ").strip() or "movie"

            params: dict = {"sort_by": "popularity.desc"}
            if genre_id:
                params["with_genres"] = genre_id
            if min_year:
                key = "primary_release_date.gte" if mtype == "movie" else "first_air_date.gte"
                params[key] = f"{min_year}-01-01"
            if max_year:
                key = "primary_release_date.lte" if mtype == "movie" else "first_air_date.lte"
                params[key] = f"{max_year}-12-31"
            if min_rating:
                params["vote_average.gte"] = min_rating
                params["vote_count.gte"] = "100"

            data = tmdb_fetch(f"/discover/{mtype}", api_key, params)
            if not data:
                continue
            results = data.get("results", [])
            ok(f"{len(results)} results (page 1 of {data.get('total_pages', 1)}):")
            sep()
            for item in results[:12]:
                print(_fmt_item(item))

        elif c == "6":
            name = input("  Person name (actor/director): ").strip()
            if not name:
                continue
            data = tmdb_fetch("/search/person", api_key, {"query": name})
            if not data:
                continue
            results = data.get("results", [])
            if not results:
                warn("No results")
                continue
            p = results[0]
            ok(f"{p.get('name', '?')}  (ID: {p.get('id', '?')})")
            info(f"Popularity: {p.get('popularity', 0):.1f}")
            known_for = p.get("known_for", [])
            info("Known for:")
            for k in known_for:
                t = k.get("title") or k.get("name") or "?"
                info(f"  • {t} ({k.get('media_type', '?')})")

        elif c == "7":
            mid   = input("  TMDB ID: ").strip()
            mtype = input("  Type [movie/tv] (default: movie): ").strip() or "movie"
            s = e = "1"
            if mtype == "tv":
                s = input("  Season (default: 1): ").strip() or "1"
                e = input("  Episode (default: 1): ").strip() or "1"
            sep()
            ok(f"Embed URLs for TMDB:{mid} ({mtype})")
            for srv in SERVERS:
                url = build_embed_url(mid, mtype, srv, s, e)
                print(f"  {clr(srv['badge'], W)} {clr(srv['name'].ljust(14), C)} {url}")


# ═══════════════════════════════════════════════════════════════════════════════
# SERVER URL BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_embed_url(tmdb_id: str, mtype: str, srv: dict, s: str = "1", e: str = "1") -> str:
    # BUG FIX: original only checked srv["id"] == "vidsrcme" for TV special-case
    # but VidSrc.ME also uses a different query-string format for movies.
    # Centralised the logic and handled both.
    if mtype == "movie":
        base = srv["movieBase"] + tmdb_id
        if srv["id"] == "vidlink":
            base += "?primaryColor=E50914&autoplay=true&nextbutton=true"
        elif srv["id"] == "vidsrcme":
            # already ends in ?tmdb=  so ID is already appended
            pass
    else:
        if srv["id"] == "vidsrcme":
            base = srv["tvBase"] + tmdb_id + f"&season={s}&episode={e}"
        else:
            base = srv["tvBase"] + tmdb_id + f"/{s}/{e}"
        if srv["id"] == "vidlink":
            base += "?primaryColor=E50914&autoplay=true"
    return base


def server_url_builder():
    step("Streaming Server URL Builder")
    sep()
    tmdb_id = input("  TMDB ID (e.g. 550 for Fight Club): ").strip()
    if not tmdb_id or not tmdb_id.isdigit():
        warn("Invalid TMDB ID")
        return
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


def bulk_server_ping():
    """Ping all streaming servers and report latency + reachability."""
    hdr("BULK SERVER HEALTH CHECK")
    info("Testing all streaming servers...")
    blank()

    results: list[dict] = []

    for srv in SERVERS:
        url = srv["movieBase"] + "550"
        host = urllib.parse.urlparse(url).hostname or ""
        port = 443
        try:
            t0 = time.perf_counter()
            with socket.create_connection((host, port), timeout=5):
                ms = (time.perf_counter() - t0) * 1000
            status = clr(f"✓ {ms:.0f}ms", G)
            results.append({"name": srv["name"], "host": host, "ms": ms, "ok": True})
        except Exception:
            status = clr("✗ UNREACHABLE", R)
            results.append({"name": srv["name"], "host": host, "ms": 9999, "ok": False})

        badge = srv["badge"]
        name  = clr(srv["name"].ljust(14), C)
        host_s = clr(host, DG)
        print(f"  {badge} {name} {host_s:40} {status}")

    blank()
    reachable = [r for r in results if r["ok"]]
    if reachable:
        best = min(reachable, key=lambda x: x["ms"])
        ok(f"Fastest server: {best['name']}  ({best['ms']:.0f}ms)")
    warn(f"{len(results) - len(reachable)}/{len(results)} server(s) unreachable")


# ═══════════════════════════════════════════════════════════════════════════════
# MANIFEST EDITOR
# ═══════════════════════════════════════════════════════════════════════════════

def edit_manifest(root: Path):
    mp = root / "src" / "manifest"
    if not mp.exists():
        err("manifest not found!")
        return

    step("Manifest Editor")
    sep()

    lines = mp.read_text().splitlines()
    for i, line in enumerate(lines, 1):
        key_part = clr(line.split("=")[0] if "=" in line else line, C)
        val_part = "=" + "=".join(line.split("=")[1:]) if "=" in line else ""
        print(f"  {clr(str(i).rjust(2), DG)}  {key_part}{val_part}")
    sep()
    blank()

    print(f"  {clr('Commands:', W)}")
    print(f"  {clr('  set key=value', C)}  — update or add a field")
    print(f"  {clr('  del key',        C)}  — remove a field")
    print(f"  {clr('  bump',           C)}  — increment build_version")
    print(f"  {clr('  Enter',          DG)} — cancel")
    blank()

    cmd = input("  > ").strip()
    if not cmd:
        warn("Cancelled.")
        return

    # BUG FIX: original didn't handle 'del' or 'bump' commands — added here.
    if cmd.lower() == "bump":
        new_lines = []
        bumped = False
        for line in lines:
            if line.startswith("build_version="):
                try:
                    cur = int(line.split("=", 1)[1].strip())
                except ValueError:
                    cur = 0
                new_lines.append(f"build_version={cur + 1}")
                bumped = True
            else:
                new_lines.append(line)
        if not bumped:
            new_lines.append("build_version=1")
        mp.write_text("\n".join(new_lines) + "\n")
        new_val = next((l.split("=", 1)[1] for l in new_lines if l.startswith("build_version=")), "?")
        ok(f"build_version bumped to {new_val}")
        return

    if cmd.lower().startswith("del "):
        key = cmd[4:].strip()
        new_lines = [l for l in lines if not l.startswith(key + "=")]
        mp.write_text("\n".join(new_lines) + "\n")
        ok(f"Removed: {key}")
        return

    if cmd.lower().startswith("set "):
        cmd = cmd[4:]

    if "=" not in cmd:
        warn("Unknown command or missing '=' — use: set key=value")
        return

    key, val = cmd.split("=", 1)
    key = key.strip()
    val = val.strip()

    new_lines = []
    replaced  = False
    for line in lines:
        if line.startswith(key + "="):
            new_lines.append(f"{key}={val}")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f"{key}={val}")

    mp.write_text("\n".join(new_lines) + "\n")
    ok(f"{'Updated' if replaced else 'Added'}: {key}={val}")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG VIEWER
# ═══════════════════════════════════════════════════════════════════════════════

def show_config(root: Path):
    step("Config viewer — servers, rows, feature flags from Config.bs")
    cfg_path = root / "src" / "source" / "Services" / "Config.bs"
    if not cfg_path.exists():
        err("Config.bs not found!")
        return
    text = cfg_path.read_text(encoding="utf-8", errors="replace")

    # Servers
    servers = re.findall(r'id:\s*"([^"]+)",\s*name:\s*"([^"]+)"', text)
    sep()
    ok(f"Servers ({len(servers)}):")
    for sid, sname in servers:
        print(f"    {clr(sid.ljust(14), Y)} {sname}")

    # Rows
    rows = re.findall(r'title:\s*"([^"]+)"[^}]+?endpoint:\s*"([^"]+)"', text, re.DOTALL)
    blank()
    ok(f"Content rows ({len(rows)}):")
    for title, ep in rows:
        print(f"    {clr(title.ljust(28), M)} {clr(ep, C)}")

    # Feature flags
    flags = re.findall(r"(Enable\w+|BandwidthSaver):\s*(true|false)", text)
    blank()
    ok("Feature flags:")
    for flag, val in flags:
        colour = G if val == "true" else DG
        print(f"    {flag.ljust(26)} {clr(val, colour)}")

    # ENV constants
    env_vals = re.findall(r'(\w+_\w+):\s*"([^"]+)"', text)
    if env_vals:
        blank()
        ok("Environment constants:")
        for k, v in env_vals:
            print(f"    {clr(k.ljust(18), Y)} {v}")
    blank()


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY DUMP (simulate reading Roku registry from backup JSONs)
# ═══════════════════════════════════════════════════════════════════════════════

def registry_dump(root: Path):
    """Display any exported registry JSON files in the project."""
    hdr("REGISTRY / PERSISTED DATA VIEWER")
    reg_files = list(root.rglob("*.registry.json")) + list(root.rglob("registry_backup*.json"))
    if not reg_files:
        warn("No registry backup files found (*.registry.json)")
        info("Run 'Export registry' from the Roku dev web UI to produce one")
        return
    for rf in reg_files:
        try:
            data = json.loads(rf.read_text())
            ok(f"{rf.name}:")
            for k, v in data.items():
                print(f"    {clr(k.ljust(24), C)} {clr(str(v)[:80], DG)}")
        except Exception as e:
            err(f"Cannot parse {rf.name}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════════════

def run_benchmarks(root: Optional[Path]):
    """Micro-benchmarks for common dev operations."""
    hdr("PERFORMANCE BENCHMARKS")
    sep()

    results: list[tuple[str, float]] = []

    # 1. File count speed
    if root:
        t0 = time.perf_counter()
        count = sum(1 for _ in (root / "src").rglob("*") if _.is_file())
        t1 = time.perf_counter()
        ms = (t1 - t0) * 1000
        results.append(("File traversal (src/)", ms))
        info(f"File traversal: {count} files in {ms:.1f}ms")

    # 2. JSON parse
    sample = json.dumps({"items": [{"id": i, "title": f"Item {i}"} for i in range(1000)]})
    t0 = time.perf_counter()
    for _ in range(1000):
        json.loads(sample)
    t1 = time.perf_counter()
    ms = (t1 - t0) * 1000
    results.append(("JSON parse (1000×)", ms))
    info(f"JSON parse 1000×: {ms:.1f}ms")

    # 3. Regex match
    t0 = time.perf_counter()
    for _ in range(10000):
        re.search(r'TMDB_KEY:\s*"([a-f0-9]{32})"', 'TMDB_KEY: "15d2ea6d0dc1d476efbca3eba2b9bbfb"')
    t1 = time.perf_counter()
    ms = (t1 - t0) * 1000
    results.append(("Regex search (10k×)", ms))
    info(f"Regex 10k×: {ms:.1f}ms")

    # 4. MD5 hashing
    data = b"X" * 100_000
    t0 = time.perf_counter()
    for _ in range(100):
        hashlib.md5(data).hexdigest()
    t1 = time.perf_counter()
    ms = (t1 - t0) * 1000
    results.append(("MD5 hash 100KB×100", ms))
    info(f"MD5 100KB×100: {ms:.1f}ms")

    # 5. TMDB latency (network)
    try:
        t0 = time.perf_counter()
        with socket.create_connection(("api.themoviedb.org", 443), timeout=5):
            pass
        t1 = time.perf_counter()
        ms = (t1 - t0) * 1000
        results.append(("TMDB TCP connect", ms))
        info(f"TMDB TCP connect: {ms:.1f}ms")
    except Exception:
        warn("TMDB unreachable — skipping network benchmark")

    sep()
    ok("Benchmark complete")


# ═══════════════════════════════════════════════════════════════════════════════
# ROLLBACK MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

def rollback_manager(root: Path):
    """List previous zip packages and allow re-deploying an older one."""
    hdr("ROLLBACK MANAGER")
    zips = sorted(root.glob("BingeBox-Omega-*.zip"), reverse=True)
    if not zips:
        warn("No packaged zip files found in project root")
        return

    ok(f"Found {len(zips)} package(s):")
    for i, z in enumerate(zips, 1):
        ts_s = z.stat().st_mtime
        ts   = datetime.fromtimestamp(ts_s).strftime("%Y-%m-%d %H:%M")
        size = z.stat().st_size // 1024
        print(f"  {clr(f'[{i}]', C)} {z.name:40} {ts}  {size:>5} KB")

    blank()
    raw = input("  Select package to redeploy (0 to cancel): ").strip()
    if raw == "0" or not raw:
        return
    try:
        idx = int(raw) - 1
        chosen = zips[idx]
    except (ValueError, IndexError):
        warn("Invalid selection")
        return

    ok(f"Selected: {chosen.name}")
    roku_ip = input("  Roku device IP: ").strip()
    if not roku_ip:
        warn("Cancelled.")
        return
    roku_pass = input(f"  Roku dev password (default: {DEFAULT_ROKU_PASS}): ").strip() or DEFAULT_ROKU_PASS
    deploy_to_roku(chosen, roku_ip, roku_pass)


# ═══════════════════════════════════════════════════════════════════════════════
# ENV EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def export_env(root: Path):
    """Export project config to .env and JSON formats."""
    hdr("ENVIRONMENT EXPORT")
    cfg = read_config(root)

    env_data = {
        "BINGEBOX_VERSION":  "3.0.0",
        "TMDB_API_KEY":      cfg.get("tmdb_key", TMDB_KEY_DEFAULT),
        "PROJECT_ROOT":      str(root),
        "EXPORT_TIME":       datetime.now().isoformat(),
    }
    env_data.update({f"FEATURE_{k.upper()}": str(v) for k, v in cfg.get("features", {}).items()})

    # .env
    env_path = root / ".env.bingebox"
    env_path.write_text("\n".join(f"{k}={v}" for k, v in env_data.items()) + "\n")
    ok(f"Written: {env_path}")

    # JSON
    json_path = root / "bingebox_env.json"
    json_path.write_text(json.dumps(env_data, indent=2))
    ok(f"Written: {json_path}")

    sep()
    for k, v in env_data.items():
        print(f"  {clr(k.ljust(30), C)} {clr(v, DG)}")


# ═══════════════════════════════════════════════════════════════════════════════
# WATCHDOG (file-change monitor → auto-rebuild)
# ═══════════════════════════════════════════════════════════════════════════════

def watchdog(root: Path):
    """Watch src/ for changes and auto-trigger compile + package."""
    hdr("WATCHDOG — AUTO BUILD ON CHANGE")
    info(f"Monitoring: {root / 'src'}")
    info("Press Ctrl+C to stop")
    blank()

    def snapshot() -> dict[str, float]:
        s: dict[str, float] = {}
        for f in (root / "src").rglob("*"):
            if f.is_file():
                try:
                    s[str(f)] = f.stat().st_mtime
                except OSError:
                    pass
        return s

    prev = snapshot()
    ok("Watching...")

    try:
        while True:
            time.sleep(1.5)
            curr = snapshot()

            changed = [
                p for p, t in curr.items()
                if p not in prev or prev[p] != t
            ]
            removed = [p for p in prev if p not in curr]

            if changed or removed:
                blank()
                for c in changed:
                    warn(f"Changed: {Path(c).relative_to(root)}")
                for r in removed:
                    warn(f"Removed: {Path(r).relative_to(root)}")
                blank()
                step("Auto-building...")
                compile_project(root)
                package_zip(root)
                ok("Auto-build complete — watching for more changes...")
                prev = snapshot()
            else:
                prev = curr

    except KeyboardInterrupt:
        blank()
        ok("Watchdog stopped.")


# ═══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE FILE DIFF VIEWER
# ═══════════════════════════════════════════════════════════════════════════════

def interactive_diff(root: Path):
    """Side-by-side diff of any two files in the project."""
    hdr("FILE DIFF VIEWER")
    all_files = sorted(
        str(f.relative_to(root))
        for f in root.rglob("*") if f.is_file() and f.suffix in (".bs", ".xml", ".json", ".md", "")
    )
    if len(all_files) < 2:
        warn("Need at least 2 files to diff")
        return

    print("  Enter paths relative to project root (or absolute):")
    path_a = input("  File A: ").strip()
    path_b = input("  File B: ").strip()

    try:
        fa = (root / path_a) if not Path(path_a).is_absolute() else Path(path_a)
        fb = (root / path_b) if not Path(path_b).is_absolute() else Path(path_b)
        lines_a = fa.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        lines_b = fb.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except OSError as e:
        err(f"Cannot read file: {e}")
        return

    diff = list(difflib.unified_diff(lines_a, lines_b, fromfile=path_a, tofile=path_b, lineterm=""))
    if not diff:
        ok("Files are identical")
        return

    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            print(clr(line, W))
        elif line.startswith("+"):
            print(clr(line, G))
        elif line.startswith("-"):
            print(clr(line, R))
        elif line.startswith("@@"):
            print(clr(line, C))
        else:
            print(clr(line, DG))


# ═══════════════════════════════════════════════════════════════════════════════
# HEADLESS / CI MODE
# ═══════════════════════════════════════════════════════════════════════════════

def headless_main(args: argparse.Namespace, root: Optional[Path]):
    """Non-interactive mode for CI pipelines."""
    cmd = args.headless.lower()
    if not root:
        err("Project not found — pass path as second argument")
        sys.exit(1)

    print(f"[CI] BingeBox Omega v{VERSION} — headless '{cmd}'")
    t0 = time.perf_counter()

    if cmd == "build":
        ok_flag = compile_project(root)
        sys.exit(0 if ok_flag else 1)

    elif cmd == "install":
        ok_flag = npm_install(root)
        sys.exit(0 if ok_flag else 1)

    elif cmd == "package":
        z = package_zip(root)
        sys.exit(0 if z else 1)

    elif cmd == "lint":
        inspect_project(root)
        sys.exit(0)

    elif cmd == "pipeline":
        full_pipeline(root, headless=True)
        sys.exit(0)

    else:
        err(f"Unknown headless command: '{cmd}'")
        err("Valid: build, install, package, lint, pipeline")
        sys.exit(2)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN MENU
# ═══════════════════════════════════════════════════════════════════════════════

MENU = [
    # (key, label, colour, group)
    ("1",  "Install npm deps",              G,  "build"),
    ("2",  "Compile BrighterScript",        G,  "build"),
    ("3",  "Package .zip",                  G,  "build"),
    ("4",  "Deploy to Roku (LAN)",          G,  "build"),
    ("P",  "★ FULL PIPELINE",               Y,  "build"),
    (None, None, None, None),
    ("5",  "Git pull",                      B,  "git"),
    ("G",  "Git menu (status/log/branch…)", B,  "git"),
    (None, None, None, None),
    ("6",  "TMDB API tester",               C,  "tools"),
    ("7",  "Server URL builder",            C,  "tools"),
    ("8",  "Inspect & lint project",        C,  "tools"),
    ("9",  "Edit manifest",                 C,  "tools"),
    ("0",  "View config",                   C,  "tools"),
    ("S",  "BS syntax check",               C,  "tools"),
    (None, None, None, None),
    ("A",  "Server ping / health check",    M,  "advanced"),
    ("D",  "File diff viewer",              M,  "advanced"),
    ("E",  "Export env / config",           M,  "advanced"),
    ("H",  "Environment health check",      M,  "advanced"),
    ("K",  "Roku ECP remote control",       M,  "advanced"),
    ("L",  "Scan Roku on network",          M,  "advanced"),
    ("N",  "Roku installed apps",           M,  "advanced"),
    ("R",  "Rollback package",              M,  "advanced"),
    ("W",  "Watchdog (auto-build)",         M,  "advanced"),
    ("X",  "Benchmarks",                    M,  "advanced"),
    ("Z",  "Zip diff / contents",           M,  "advanced"),
    (None, None, None, None),
    ("Q",  "Quit",                          DG, "meta"),
]


def print_menu(project_root: Optional[Path], last_zip: Optional[Path]):
    blank()
    w = min(terminal_width(), 62)
    print(clr(f"  {'═'*w}", C))
    print(clr(f"  ║{'BingeBox Omega Dev Menu':^{w-2}}║", C))
    print(clr(f"  {'═'*w}", C))

    prev_group = None
    for key, label, colour, group in MENU:
        if key is None:
            print(f"  ║{' '*{w-2}}║")
            continue
        if group != prev_group and group != prev_group:
            pass
        prev_group = group
        tag  = clr(f"[{key}]", colour)
        line = f"  ║  {tag} {label}"
        pad  = w - len(f"  ║  [{key}] {label}") + 2
        print(line + " " * max(pad, 2) + "║")

    print(clr(f"  {'═'*w}", C))
    blank()

    if project_root:
        print(f"  {clr('Project:', DG)} {clr(str(project_root), W)}")
    else:
        print(f"  {clr('Project:', DG)} {clr('NOT FOUND  (build features limited)', R)}")
    if last_zip:
        print(f"  {clr('Last zip:', DG)} {clr(last_zip.name, G)}")
    print(f"  {clr('Log:', DG)} {clr(str(LOG_FILE), DG)}")
    blank()


def git_submenu(root: Path):
    hdr("GIT TOOLS")
    opts = [
        ("pull",       "Pull from remote"),
        ("status",     "Show status"),
        ("log",        "Show commit log"),
        ("diff",       "Show diff"),
        ("stash",      "Stash manager"),
        ("branch",     "Branch manager"),
        ("changelog",  "Generate CHANGELOG.md"),
    ]
    idx = choose_from([(o, d) for o, d in opts])
    if idx is None:
        return
    action = opts[idx][0]
    dispatch = {
        "pull":      lambda: git_pull(root),
        "status":    lambda: git_status(root),
        "log":       lambda: git_log(root),
        "diff":      lambda: git_diff(root),
        "stash":     lambda: git_stash(root),
        "branch":    lambda: git_branch_manager(root),
        "changelog": lambda: generate_changelog(root),
    }
    dispatch[action]()


def zip_submenu(root: Path, last_zip: Optional[Path]):
    hdr("ZIP TOOLS")
    opts = [
        ("contents", "List zip contents"),
        ("diff",     "Diff two zips"),
    ]
    idx = choose_from([(o, d) for o, d in opts])
    if idx is None:
        return
    action = opts[idx][0]

    if action == "contents":
        zips = sorted(root.glob("BingeBox-Omega-*.zip"), reverse=True)
        if not zips:
            if last_zip and last_zip.exists():
                zips = [last_zip]
            else:
                warn("No zips found")
                return
        zip_opts = [(z.name, f"{z.stat().st_size//1024} KB") for z in zips[:8]]
        i = choose_from(zip_opts)
        if i is None:
            return
        list_zip_contents(zips[i])

    elif action == "diff":
        zips = sorted(root.glob("BingeBox-Omega-*.zip"), reverse=True)
        if len(zips) < 2:
            warn("Need at least 2 zips to diff")
            return
        zip_opts = [(z.name, f"{z.stat().st_size//1024} KB") for z in zips[:8]]
        print("  Select first zip:")
        ia = choose_from(zip_opts)
        if ia is None:
            return
        print("  Select second zip:")
        ib = choose_from(zip_opts)
        if ib is None or ib == ia:
            warn("Select two different zips")
            return
        compare_zips(zips[ia], zips[ib])


def roku_ecp_submenu(root: Path):
    hdr("ROKU ECP TOOLS")
    roku_ip = input("  Roku device IP: ").strip()
    if not roku_ip:
        return
    opts = [
        ("remote",  "Interactive remote control"),
        ("apps",    "List installed apps"),
    ]
    idx = choose_from([(o, d) for o, d in opts])
    if idx is None:
        return
    if opts[idx][0] == "remote":
        roku_remote_tool(roku_ip)
    else:
        roku_app_list(roku_ip)


def main():
    # ── Argument parsing ──────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description=f"BingeBox Omega Dev Tool v{VERSION}",
        add_help=True,
    )
    parser.add_argument("project_path", nargs="?", help="Path to project root")
    parser.add_argument("--headless", metavar="CMD",
                        help="Run non-interactively: build|install|package|lint|pipeline")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    args, _ = parser.parse_known_args()

    global NO_COLOR
    if args.no_color:
        NO_COLOR = True

    # ── Project discovery ─────────────────────────────────────────────────────
    project_root = find_project()

    # ── Headless / CI mode ────────────────────────────────────────────────────
    if args.headless:
        headless_main(args, project_root)
        return

    # ── Interactive mode ──────────────────────────────────────────────────────
    banner()

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

    last_zip: Optional[Path] = None

    def need_root() -> bool:
        nonlocal project_root, api_key
        if project_root:
            return True
        project_root = prompt_project()
        if project_root:
            cfg     = read_config(project_root)
            api_key = cfg.get("tmdb_key", TMDB_KEY_DEFAULT)
            return True
        return False

    while True:
        try:
            print_menu(project_root, last_zip)
            choice = input("  Choose: ").strip().upper()

            # Build
            if choice == "1":
                if need_root(): npm_install(project_root)
            elif choice == "2":
                if need_root(): compile_project(project_root)
            elif choice == "3":
                if need_root():
                    z = package_zip(project_root)
                    if z: last_zip = z
            elif choice == "4":
                if need_root(): deploy_interactive(project_root, last_zip)
            elif choice == "P":
                if need_root(): full_pipeline(project_root)

            # Git
            elif choice == "5":
                if need_root(): git_pull(project_root)
            elif choice == "G":
                if need_root(): git_submenu(project_root)

            # Tools
            elif choice == "6": tmdb_tester(api_key)
            elif choice == "7": server_url_builder()
            elif choice == "8":
                if need_root(): inspect_project(project_root)
            elif choice == "9":
                if need_root(): edit_manifest(project_root)
            elif choice == "0":
                if need_root(): show_config(project_root)
            elif choice == "S":
                if need_root(): bs_syntax_check(project_root)

            # Advanced
            elif choice == "A": bulk_server_ping()
            elif choice == "D":
                if need_root(): interactive_diff(project_root)
            elif choice == "E":
                if need_root(): export_env(project_root)
            elif choice == "H":  full_env_check(project_root)
            elif choice == "K":
                if need_root(): roku_ecp_submenu(project_root)
            elif choice == "L":
                subnet = input("  Subnet prefix (e.g. 192.168.1, Enter to auto-detect): ").strip()
                found  = scan_roku_on_network(subnet)
                if found and project_root and confirm("Deploy to a found device?", default=False):
                    ip = found[0] if len(found) == 1 else input("  Which IP? ").strip()
                    if ip:
                        deploy_interactive(project_root, last_zip)
            elif choice == "N":
                ip = input("  Roku IP: ").strip()
                if ip: roku_app_list(ip)
            elif choice == "R":
                if need_root(): rollback_manager(project_root)
            elif choice == "W":
                if need_root(): watchdog(project_root)
            elif choice == "X":  run_benchmarks(project_root)
            elif choice == "Z":
                if need_root(): zip_submenu(project_root, last_zip)

            elif choice == "Q":
                blank()
                ok("Goodbye! — BingeBox Omega")
                log.info("Clean exit by user")
                sys.exit(0)
            else:
                warn(f"Unknown option: '{choice}'")

        except KeyboardInterrupt:
            blank()
            warn("Interrupted — returning to menu (Q to quit)")
        except Exception as exc:
            err(f"Unexpected error: {exc}")
            _log_err("main loop", exc)
            if os.getenv("BINGEBOX_DEBUG"):
                traceback.print_exc()
            warn("Error logged. Continuing...")


if __name__ == "__main__":
    main()
