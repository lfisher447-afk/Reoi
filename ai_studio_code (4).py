#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    BINGEBOX OMEGA SUPREME — ROKU SDK                         ║
║        Custom-Tailored for the BingeBox v3.0 BrighterScript Engine           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ [CORE]      rosc, npm install, package zip, Direct ECP Sideload Deployment   ║
║ [AST]       Deep BrighterScript Linter, Component/XML Sync Validator         ║
║ [TMDB]      Live API Pulse, Discover Engine, Cast Matrix via `Config.bs`     ║
║ [NETWORK]   Dynamic Server Payload extraction directly from `Config.bs`      ║
║[TOOLS]     Watchdog Daemon, Binary Zip Diff, ECP Remote, Subnet Scanner     ║
║ [GIT]       Commit History, Diff, Pull, Status, Auto-Changelog Generator     ║
║ [UI]        CLI OS, Rich Telemetry Dashboard, Turtle Cyberpunk HUD           ║
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
import platform
import logging
import queue
import contextlib
import textwrap
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# UI FRAMEWORKS (Graceful Degradation)
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
if sys.platform == "win32":
    os.system("") # Enable ANSI natively on Windows 10+

R, G, Y, C, M, W, DG, B, RST = "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[95m", "\033[97m", "\033[90m", "\033[94m", "\033[0m"

def clr(t: str, c: str) -> str: return f"{c}{t}{RST}"
def ok(m: str):    print(f"  {clr('✓', G)} {m}")
def err(m: str):   print(f"  {clr('✗', R)} {m}")
def warn(m: str):  print(f"  {clr('!', Y)} {m}")
def step(m: str):  print(f"\n  {clr('▶', C)} {clr(m, W)}")
def info(m: str):  print(f"    {clr(m, DG)}")
def hdr(m: str):   print(f"\n  {clr('━'*54, B)}\n  {clr(m, M+'\033[1m')}\n  {clr('━'*54, B)}")
def sep(ch="─"):   print(f"  {clr(ch*54, DG)}")
def blank():       print()

# Logging Isolation
log = logging.getLogger("omega_sdk")
logging.basicConfig(filename=str(Path.home() / ".bingebox_sdk.log"), level=logging.DEBUG)

def _log_err(context: str, exc: Exception):
    log.error(f"{context}: {exc}", exc_info=True)

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT PARSER & BRIGHTERSCRIPT AST
# ─────────────────────────────────────────────────────────────────────────────
def find_project() -> Optional[Path]:
    for cand in[Path.cwd(), Path.cwd() / "BingeBox-Roku-v2", Path.home() / "Desktop/BingeBox-Roku-v2"]:
        if (cand / "package.json").exists() and (cand / "src/manifest").exists():
            return cand.resolve()
    return None

def prompt_project() -> Optional[Path]:
    warn("Project folder not found automatically.")
    raw = input("  Enter full path to project root (Enter to skip): ").strip().strip('"\'')
    if raw:
        p = Path(raw)
        if (p / "package.json").exists(): return p.resolve()
        err(f"No package.json at '{p}'")
    return None

def read_bs_config(root: Path) -> dict:
    """Deeply parses your specific `Config.bs` file to keep the Python SDK synced"""
    result = {"tmdb_key": "15d2ea6d0dc1d476efbca3eba2b9bbfb", "servers":[], "rows":[], "features": {}}
    cfg = root / "src" / "source" / "Services" / "Config.bs"
    if not cfg.exists(): return result
    
    text = cfg.read_text(encoding="utf-8", errors="replace")
    
    # 1. TMDB Key
    tmdb_match = re.search(r'TMDB_KEY:\s*"([^"]+)"', text)
    if tmdb_match: result["tmdb_key"] = tmdb_match.group(1)
    
    # 2. Servers (Multi-line parsing tailored to your BrighterScript arrays)
    srv_pattern = r'id:\s*"([^"]+)",\s*name:\s*"([^"]+)"(?:.*?badge:\s*"([^"]+)")?[^}]*?movieBase:\s*"([^"]+)"[^}]*?tvBase:\s*"([^"]+)"'
    for m in re.finditer(srv_pattern, text, re.DOTALL):
        result["servers"].append({
            "id": m.group(1), "name": m.group(2), "badge": m.group(3) or "🌐",
            "movieBase": m.group(4), "tvBase": m.group(5)
        })
        
    # 3. Content Rows
    row_pattern = r'title:\s*"([^"]+)"[^}]+?endpoint:\s*"([^"]+)"'
    for m in re.finditer(row_pattern, text, re.DOTALL):
        result["rows"].append({"title": m.group(1), "endpoint": m.group(2)})
        
    # 4. Feature Flags
    for m in re.finditer(r'(Enable\w+|BandwidthSaver):\s*(true|false)', text):
        result["features"][m.group(1)] = m.group(2) == "true"
        
    return result

# ─────────────────────────────────────────────────────────────────────────────
# BUILD & DEPLOYMENT CORE
# ─────────────────────────────────────────────────────────────────────────────
def npm_install(root: Path) -> bool:
    step("Resolving NPM Workspace Dependencies...")
    if not shutil.which("npm"):
        err("npm missing from PATH"); return False
    res = subprocess.run(["npm", "install"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if res.returncode != 0:
        err("npm install FAILED"); info(res.stderr.decode(errors='replace')[:500]); return False
    ok("Dependencies locked and loaded")
    return True

def compile_project(root: Path) -> bool:
    step("Executing BrighterScript Compiler Pipeline...")
    if not (root / "node_modules").exists():
        if not npm_install(root): return False
        
    res = subprocess.run(["npm", "run", "build"], cwd=root, capture_output=True, text=True)
    if res.returncode != 0:
        warn("npm run build failed, invoking npx bsc directly...")
        res = subprocess.run(["npx", "bsc"], cwd=root, capture_output=True, text=True)
        if res.returncode != 0:
            err("Compilation FAILED. Compiler Output:")
            print(clr(res.stdout[-800:], Y)); return False
            
    ok("Bytecode Transpilation Complete -> out/.roku-deploy-staging/")
    return True

def package_zip(root: Path) -> Optional[Path]:
    step("Packaging Roku Payload (.zip)...")
    base = root / "out/.roku-deploy-staging"
    if not base.exists(): 
        warn("Staging folder missing, dropping down to raw src/ mode.")
        base = root / "src"
    
    zip_path = root / f"BingeBox-Supreme-{datetime.now().strftime('%Y%m%d-%H%M')}.zip"
    all_files = sorted(f for f in base.rglob("*") if f.is_file())
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for f in all_files: zf.write(f, f.relative_to(base))
            
    ok(f"Payload Sealed: {zip_path.name} ({zip_path.stat().st_size//1024} KB)")
    return zip_path

def deploy_to_roku(zip_path: Path, ip: str, pwd: str):
    step(f"Transmitting Payload to targeted Roku ECP Unit ({ip})...")
    boundary = f"SigmaBoundary{int(time.time())}"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"mysubmit\"\r\n\r\nInstall\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"archive\"; filename=\"{zip_path.name}\"\r\n"
        f"Content-Type: application/zip\r\n\r\n"
    ).encode() + zip_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(f"http://{ip}/plugin_install", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Basic {base64.b64encode(f'rokudev:{pwd}'.encode()).decode()}")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = r.read().decode(errors="replace").lower()
        if "install success" in resp or r.status == 200: ok("Flash Successful. App Executing.")
        else: err("Roku OS rejected the firmware."); info(resp[:200])
    except urllib.error.HTTPError as e: err("Auth Failed" if e.code == 401 else f"HTTP {e.code}")
    except Exception as e: err(f"Deployment dropped: {e}")

def deploy_interactive(root: Path, zip_path: Optional[Path] = None):
    blank()
    print(clr("  ┌─ ROKU HARWARE LINK ──────────────────┐", C))
    print(clr("  │  Roku OS Dev Mode Required (8060)    │", C))
    print(clr("  └──────────────────────────────────────┘", C))
    
    ip = input("  Device IPv4 Address: ").strip()
    if not ip: return
    pwd = input(f"  Root Password (default: rokudev): ").strip() or "rokudev"
    
    if not zip_path or not zip_path.exists():
        zip_path = package_zip(root)
    if zip_path: deploy_to_roku(zip_path, ip, pwd)

# ─────────────────────────────────────────────────────────────────────────────
# DEEP LINTER (Tailored to Project Files)
# ─────────────────────────────────────────────────────────────────────────────
def inspect_project(root: Path):
    hdr("ROKU PROJECT LINTER & INTEGRITY CHECK")
    
    # 1. Manifest
    man = root / "src/manifest"
    if man.exists():
        ok("Manifest Config Found")
        lines = man.read_text().splitlines()
        for ref in["pkg:/images/icon_focus_hd.png", "pkg:/images/icon_side_hd.png", "pkg:/images/splash_hd.png"]:
            if any(ref in l for l in lines):
                asset = root / "src" / ref.replace("pkg:/", "")
                if asset.exists(): ok(f"Asset Linked: {asset.name}")
                else: err(f"Asset Missing from src/images: {asset.name}")
    else: err("Manifest Missing!")
    
    # 2. BS Component Linkage
    comp_dir = root / "src/components"
    if comp_dir.exists():
        xml_files = {f.stem for f in comp_dir.rglob("*.xml")}
        bs_files = {f.stem for f in comp_dir.rglob("*.bs")}
        missing_bs = xml_files - bs_files
        if missing_bs:
            for m in missing_bs: err(f"Component <{m}.xml> has no companion .bs script!")
        else: ok(f"Strict Component Pairing Verified ({len(xml_files)} pairs)")
    
    # 3. BrightScript Security / Syntax
    hits = 0
    for f in (root / "src").rglob("*.bs"):
        txt = f.read_text(errors="ignore")
        if "console.log" in txt: err(f"JS artifact 'console.log' in {f.name}"); hits+=1
        if "=>" in txt: err(f"JS artifact '=>' (Arrow function) in {f.name}"); hits+=1
        if re.search(r'\bprint\s+"', txt): warn(f"Unsafe print in {f.name} (Use Utils.Logger)"); hits+=1
        if re.search(r"\b(let|const)\s+\w+", txt): err(f"JS 'let/const' declaration in {f.name}"); hits+=1
    
    if hits == 0: ok("Abstract Syntax Tree is clean. Code adheres to BingeBox Standards.")
    else: warn(f"{hits} Linter exceptions detected.")

def edit_manifest(root: Path):
    man = root / "src/manifest"
    if not man.exists(): err("Manifest Missing!"); return
    
    hdr("MANIFEST MODIFICATION UTILITY")
    lines = man.read_text().splitlines()
    for i, l in enumerate(lines, 1): print(f" {clr(str(i).rjust(2), DG)}  {l}")
    sep()
    c = input("  Cmd[ 'key=val', 'bump', or Enter to cancel ]: ").strip()
    if not c: return
    
    if c == "bump":
        changed_lines =[]
        for l in lines:
            if l.startswith("build_version="):
                changed_lines.append(f"build_version={int(l.split('=')[1])+1}")
            else: changed_lines.append(l)
        man.write_text("\n".join(changed_lines) + "\n")
        ok("Build Version Incremented")
    elif "=" in c:
        k, v = c.split("=", 1)
        changed_lines =[l if not l.startswith(k+"=") else f"{k}={v}" for l in lines]
        if not any(l.startswith(k+"=") for l in changed_lines): changed_lines.append(c)
        man.write_text("\n".join(changed_lines) + "\n")
        ok("Manifest Key Written")

# ─────────────────────────────────────────────────────────────────────────────
# TMDB & SERVER BUSINESS LOGIC 
# ─────────────────────────────────────────────────────────────────────────────
def build_embed_url(mid: str, media_type: str, srv: dict, s="1", e="1") -> str:
    if media_type == "movie":
        url = srv["movieBase"] + str(mid)
        if srv["id"] == "vidlink": url += "?primaryColor=E50914&autoplay=true"
    else:
        url = srv["tvBase"] + str(mid) + "/1/1"
        if srv["id"] == "vidsrcme": url = srv["tvBase"] + str(mid) + f"&season={s}&episode={e}"
        if srv["id"] == "vidlink": url += "?primaryColor=E50914&autoplay=true"
    return url

def tmdb_fetch(ep: str, key: str, params: dict = None) -> dict:
    p = {"api_key": key, "language": "en-US"}; p.update(params or {})
    qs = urllib.parse.urlencode(p)
    url = f"https://api.themoviedb.org/3{ep}{'&' if '?' in ep else '?'}{qs}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"Supreme/{VERSION}"})
        with urllib.request.urlopen(req, timeout=10) as r: return json.loads(r.read().decode())
    except: return {}

def _fmt_item(r: dict) -> str:
    t = r.get("title") or r.get("name") or "?"
    m = r.get("media_type", "movie")
    y = (r.get("release_date") or r.get("first_air_date") or "")[:4]
    return f"  {clr(str(r.get('id', '?')).ljust(9), Y)}{clr(t.ljust(44), W)}{clr(m.ljust(8), DG)}{y}  {clr(f'⭐{r.get('vote_average',0):.1f}', M)}"

def tmdb_tester(key: str):
    hdr("TMDB GLOBAL DATALINK")
    if not tmdb_fetch("/configuration", key): err("Datalink Failed (Invalid Key or Offline)"); return
    ok("Datalink Established")
    
    while True:
        blank()
        print(clr("  ┌─ TMDB COMMAND MENU ──────────────────────────────┐", C))
        print("  │ [1] Multi-Search   [2] Horizon (Trending)        │")
        print("  │ [3] Deep Data ID   [4] Discover (Filter)         │")
        print("  │ [5] Actor/Cast     [0] Disconnect                │")
        print(clr("  └──────────────────────────────────────────────────┘", C))
        
        c = input(f"  {clr('TMDB', M)} > ").strip()
        if c == "0": break
        elif c == "1":
            d = tmdb_fetch("/search/multi", key, {"query": input("  Query: ").strip()})
            for r in d.get("results", [])[:10]: print(_fmt_item(r))
        elif c == "2":
            d = tmdb_fetch("/trending/all/week", key)
            for r in d.get("results", [])[:10]: print(_fmt_item(r))
        elif c == "3":
            mid = input("  TMDB ID: ")
            d = tmdb_fetch(f"/{input('  Type [movie/tv]: ') or 'movie'}/{mid}", key)
            if d:
                print(f"\n  {clr(d.get('title') or d.get('name'), C)} ({d.get('release_date', d.get('first_air_date', ''))[:4]})")
                print(f"  ⭐ {d.get('vote_average', 0):.1f} / 10 | Genres: {', '.join(g['name'] for g in d.get('genres',[]))}")
                print(f"  {textwrap.shorten(d.get('overview', ''), width=100)}")
        elif c == "4":
            print(f"  {clr('[Skip any filter with Enter]', W)}")
            g = input("  Genre ID (ex: 28=Action): ")
            y = input("  Min Year: ")
            t = input("  Type[movie/tv]: ") or "movie"
            p = {"sort_by": "popularity.desc"}
            if g: p["with_genres"] = g
            if y: p["primary_release_date.gte" if t=="movie" else "first_air_date.gte"] = f"{y}-01-01"
            for r in tmdb_fetch(f"/discover/{t}", key, p).get("results", [])[:10]: print(_fmt_item(r))
        elif c == "5":
            d = tmdb_fetch("/search/person", key, {"query": input("  Actor Name: ").strip()})
            if d.get("results"):
                p = d["results"][0]
                ok(f"{p['name']} (Pop: {p['popularity']:.1f})")
                for k in p.get("known_for",[]): print(f"    - {k.get('title') or k.get('name')} ({k.get('media_type')})")

def server_url_tester(cfg: dict):
    hdr("STREAMING NODE URL COMPILER")
    mid = input("  TMDB Entity ID: ").strip()
    if not mid.isdigit(): err("Invalid ID"); return
    typ = input("  Format (movie/tv): ").strip() or "movie"
    s = e = "1"
    if typ == "tv":
        s = input("  Season (default 1): ").strip() or "1"
        e = input("  Episode (default 1): ").strip() or "1"
    sep()
    for srv in cfg.get("servers",[]):
        print(f"  {srv.get('badge','')} {clr(srv.get('name','').ljust(14), C)} {build_embed_url(mid, typ, srv, s, e)}")
    blank()

# ─────────────────────────────────────────────────────────────────────────────
# GIT, WATCHDOG, DIFF & NETWORK TOOLS
# ─────────────────────────────────────────────────────────────────────────────
def _git(root: Path, args: list[str]):
    if not shutil.which("git"): err("Git CLI missing."); return None
    return subprocess.run(["git"] + args, cwd=root if (root / ".git").exists() else root.parent, text=True)

def git_pull(r: Path): step("Pulling Origin..."); _git(r,["pull"])
def git_status(r: Path): step("Repo Status:"); _git(r,["status", "-s", "-b"])
def git_log(r: Path): step("Commit History:"); _git(r,["log", "-10", "--pretty=format:%C(yellow)%h%Creset %C(cyan)%ad%Creset %s", "--date=short"])
def git_diff(r: Path): step("Working Tree Diff:"); _git(r, ["diff", "HEAD"])
def generate_changelog(r: Path):
    res = subprocess.run(["git", "log", "--pretty=format:%ad|%s", "--date=short"], cwd=r, capture_output=True, text=True)
    if res.returncode == 0:
        logs = defaultdict(list)
        for line in res.stdout.splitlines():
            if "|" in line: d, msg = line.split("|", 1); logs[d].append(f"- {msg}")
        out = ["# CHANGELOG\n"]
        for d in sorted(logs, reverse=True): out.append(f"## {d}\n" + "\n".join(logs[d]) + "\n")
        (r / "CHANGELOG.md").write_text("\n".join(out))
        ok("CHANGELOG.md fully synthesized.")
    else: err("Git log extraction failed")

def watchdog(root: Path):
    hdr("SUPREME WATCHDOG DAEMON")
    def snap(): 
        try: return {str(f): f.stat().st_mtime for f in (root / "src").rglob("*") if f.is_file()}
        except: return {}
    prev = snap()
    ok("Daemon Bound. Monitoring src/ [CTRL+C to terminate]")
    try:
        while True:
            time.sleep(1.5)
            curr = snap()
            if any(p not in prev or prev[p] != t for p, t in curr.items()) or any(p not in curr for p in prev):
                step("Change Detected. Invoking Compiler...")
                compile_project(root); package_zip(root)
                prev = snap()
                ok("System Rebuilt. Resuming monitor...")
    except KeyboardInterrupt: ok("Daemon Terminated.")

def compare_zips(za: Path, zb: Path):
    hdr(f"BINARY DELTA: {za.name} vs {zb.name}")
    try:
        with zipfile.ZipFile(za) as a, zipfile.ZipFile(zb) as b:
            na, nb = {i.filename: i for i in a.infolist()}, {i.filename: i for i in b.infolist()}
            only_a, only_b = set(na) - set(nb), set(nb) - set(na)
            for f in sorted(only_a): print(f"  - {f}")
            for f in sorted(only_b): print(f"  + {f}")
            for f in sorted(set(na) & set(nb)):
                if na[f].CRC != nb[f].CRC: print(f"  ~ {f} ({na[f].file_size}b -> {nb[f].file_size}b)")
            if not (only_a or only_b or[f for f in set(na)&set(nb) if na[f].CRC != nb[f].CRC]):
                ok("Binaries are identical.")
    except Exception as e: err(f"Diff Failed: {e}")

def roku_ecp(ip: str, path: str, method="GET") -> Optional[str]:
    try:
        c = http.client.HTTPConnection(ip, ROKU_ECP_PORT, timeout=3)
        c.request(method, path)
        return c.getresponse().read().decode(errors="ignore")
    except: return None

def roku_remote_tool(ip: str):
    hdr("ROKU ECP TERMINAL LINK")
    if not roku_ecp(ip, "/query/device-info"): err("Handshake failed"); return
    KEYS = {"h": "Home", "b": "Back", "u": "Up", "d": "Down", "l": "Left", "r": "Right", "s": "Select", "p": "Play"}
    for k, v in KEYS.items(): print(f"    {clr(k, C)} → {v}")
    while True:
        c = input(f"  {clr('KEY', M)} [q/quit] > ").strip().lower()
        if c == 'q': break
        if c in KEYS: ok(f"Sent: {KEYS[c]}"); roku_ecp(ip, f"/keypress/{KEYS[c]}", "POST")

def scan_roku_on_network():
    hdr("MULTICAST SUBNET SCANNER")
    try: subnet = ".".join(socket.gethostbyname(socket.gethostname()).split(".")[:3])
    except: subnet = "192.168.1"
    info(f"Targeting {subnet}.0/24 : 8060...")
    q = queue.Queue()
    def probe(i: str):
        try:
            with socket.create_connection((i, ROKU_ECP_PORT), timeout=0.3): q.put(i)
        except: pass
    ts =[threading.Thread(target=probe, args=(f"{subnet}.{i}",)) for i in range(1, 255)]
    for t in ts: t.start()
    for t in ts: t.join(timeout=1.0)
    found = False
    while not q.empty():
        ip = q.get(); found = True
        xml = roku_ecp(ip, "/query/device-info")
        name = re.search(r"<friendly-device-name>([^<]+)</friendly-device-name>", xml or "")
        ok(f"{ip:16} {clr(name.group(1) if name else 'Roku Device', W)}")
    if not found: warn("No signals detected.")

def bulk_server_ping(cfg: dict):
    hdr("BACKEND NODE LATENCY ANALYSIS")
    for s in cfg.get("servers", []):
        try:
            h = urllib.parse.urlparse(s["movieBase"]).hostname
            t0 = time.perf_counter()
            with socket.create_connection((h, 443), timeout=3): ms = (time.perf_counter() - t0) * 1000
            print(f"  {s.get('badge','')} {s.get('name',''):14} {h:30} {clr(f'{ms:.0f}ms', G)}")
        except: print(f"  {s.get('badge','')} {s.get('name',''):14} {h:30} {clr('UNREACHABLE', R)}")

# ─────────────────────────────────────────────────────────────────────────────
# ADVANCED UIs
# ─────────────────────────────────────────────────────────────────────────────
def launch_rich_dashboard(root: Path, cfg: dict):
    if not RICH_AVAILABLE: err("rich library missing. pip install rich"); return
    trending = tmdb_fetch("/trending/all/week", cfg["tmdb_key"])
    
    def get_layout():
        ly = Layout()
        ly.split_column(Layout(name="top", size=3), Layout(name="mid"), Layout(name="bot", size=3))
        ly["mid"].split_row(Layout(name="l", ratio=1), Layout(name="r", ratio=1))
        return ly
        
    with Live(get_layout(), refresh_per_second=2, screen=True) as live:
        try:
            while True:
                ly = get_layout()
                ly["top"].update(Panel(f"[bold cyan]BINGEBOX SUPREME ENGINE[/] | TARGET_DIR: {root.name if root else 'NONE'}", box=box.DOUBLE))
                
                t_srv = Table(title="Config.bs Stream Endpoints", expand=True)
                t_srv.add_column("Badge"); t_srv.add_column("Node Name"); t_srv.add_column("Status", justify="right")
                for s in cfg.get("servers",[]): t_srv.add_row(s.get('badge',''), s.get('name',''), "[green]LOADED[/]")
                ly["l"].update(Panel(t_srv))
                
                t_db = Table(title="TMDB Global Pulse", expand=True)
                t_db.add_column("Score"); t_db.add_column("Title")
                for r in trending.get("results", [])[:15]: 
                    t_db.add_row(f"[yellow]{r.get('vote_average',0):.1f}[/]", (r.get("title") or r.get("name"))[:35])
                ly["r"].update(Panel(t_db))
                
                ly["bot"].update(Panel(Align.center("[bold red]Press CTRL+C To Break Link[/]")))
                live.update(ly)
                time.sleep(1)
        except KeyboardInterrupt: pass

def launch_turtle_hud(root: Path, cfg: dict):
    if not TURTLE_AVAILABLE: err("Turtle graphics unavailable."); return
    sc = turtle.Screen()
    sc.bgcolor("#050505"); sc.setup(1000, 700); sc.tracer(0); sc.title("BINGEBOX OMEGA HUD")
    
    t = turtle.Turtle(); t.hideturtle(); t.speed(0); t.color("#00ffcc"); t.penup()
    trending = tmdb_fetch("/trending/all/week", cfg["tmdb_key"])
    
    def render():
        t.clear()
        t.goto(-480, 310); t.color("#ff0044")
        t.write(">>> BINGEBOX SDK DATALINK ROUTER <<<", font=("Courier", 18, "bold"))
        t.goto(-480, 200); t.color("#00ffff")
        t.write(f"PROJECT SYSTEM PATH: {root.name if root else 'UNLINKED'}\nHOST OS ARCHITECTURE: {platform.system()}\nCONFIG SERVER ARRAY COUNT: {len(cfg.get('servers',[]))}", font=("Courier", 12))
        t.goto(50, 200); t.color("#ffaa00")
        t.write("TMDB TRENDING INGEST:", font=("Courier", 12, "bold"))
        t.color("#aaaaaa")
        for i, r in enumerate(trending.get("results", [])[:15]):
            t.goto(50, 170 - (i*20))
            t.write(f"> {(r.get('title') or r.get('name'))[:40]}", font=("Courier", 10))
        sc.update()
        
    render()
    sc.listen(); sc.onkey(sc.bye, "q")
    try: turtle.mainloop()
    except: pass

# ─────────────────────────────────────────────────────────────────────────────
# SUPERVISOR CLI OS & CORE LOOP
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description=f"BingeBox Supreme Engine v{VERSION}")
    parser.add_argument("--headless", metavar="CMD", help="build | install | package")
    args = parser.parse_args()

    project_root = find_project()
    if args.headless and project_root:
        if args.headless == "build": sys.exit(0 if compile_project(project_root) else 1)
        elif args.headless == "install": sys.exit(0 if npm_install(project_root) else 1)
        elif args.headless == "package": sys.exit(0 if package_zip(project_root) else 1)

    print("\033c", end="") # Clear terminal cleanly
    art = """
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
    print(clr(art, M + '\033[1m'))
    print(clr(f"  O M E G A   S U P R E M E   v{VERSION}  ·  ULTIMATE OS DEV TOOL", Y))
    print(clr(f"  System: {platform.system()} {platform.release()}  ·  Python {sys.version.split()[0]}", DG))
    print(clr("  ─────────────────────────────────────────────────────────────────", DG))

    last_zip: Optional[Path] = None

    while True:
        try:
            # Sync SDK with the user's codebase live
            cfg = read_bs_config(project_root) if project_root else {"tmdb_key": "Offline", "servers":[]}
            
            blank()
            print(clr(f"  ╔═══════════════════════════════════════════════════════════════════╗", M))
            print(clr(f"  ║            BINGEBOX OMEGA SUPREME  —  SDK CONSOLE                 ║", M))
            print(clr(f"  ╠═══════════════════════════════════════════════════════════════════╣", M))
            print(f"  ║ {clr('[ BUILD PIPELINE ]', DG)}                                                 ║")
            print(f"  ║  {clr('[1]', G)} Execute Compiler (NPM Inst -> BSC -> Package)                ║")
            print(f"  ║  {clr('[2]', G)} Flash OS (Deploy Binary to Roku over HTTP)                   ║")
            print(f"  ║  {clr('[3]', G)} ★ FULL SYNC (Compile -> Flash)                               ║")
            print(f"  ║ {clr('[ TOOL CHAIN ]', DG)}                                                     ║")
            print(f"  ║  {clr('[4]', B)} Static Linter (Validates Component/XML sync)                 ║")
            print(f"  ║  {clr('[5]', B)} Config Server Dumper (Verify Config.bs Variables)            ║")
            print(f"  ║  {clr('[6]', M)} TMDB V3 Data Mesh (Live Search & Trending)                   ║")
            print(f"  ║  {clr('[7]', M)} URL Stream Tester & Universal Node Pinger                    ║")
            print(f"  ║ {clr('[ UTILITIES & NETWORK ]', DG)}                                            ║")
            print(f"  ║  {clr('[8]', B)} Git Workflow (Pull, Log, Status, Diff, Changelog)            ║")
            print(f"  ║  {clr('[9]', B)} Roku ECP Network (Subnet Scanner & ECP Remote)               ║")
            print(f"  ║  {clr('[W]', Y)} Watchdog (Auto-Build daemon on File Save)                    ║")
            print(f"  ║  {clr('[D]', Y)} Binary Differential Engine (Diff Build Zips)                 ║")
            print(f"  ║  {clr('[M]', Y)} Manifest Editor                                              ║")
            print(f"  ║ {clr('[ ADVANCED UIs ]', DG)}                                                   ║")
            print(f"  ║  {clr('[R]', C)} Initialize RICH Live Terminal Dashboard                      ║")
            print(f"  ║  {clr('[T]', C)} Initialize TURTLE Cyberpunk Graphical HUD                    ║")
            print(f"  ║  {clr('[Q]', DG)} Disconnect / Terminate Process                               ║")
            print(clr(f"  ╚═══════════════════════════════════════════════════════════════════╝", M))
            print(f"  [ TARGET ] {clr(str(project_root) if project_root else 'UNLINKED', G if project_root else R)}")
            blank()
            
            c = input(clr("  root@omegasupreme :~# ", C)).strip().upper()
            
            # Context Validation
            if not project_root and c in ("1", "2", "3", "4", "5", "W", "D", "M", "R", "T"):
                err("Requires linked project route."); project_root = prompt_project(); continue
                
            # EXECUTION ROUTING
            if c == "1":
                compile_project(project_root)
                last_zip = package_zip(project_root)
            elif c == "2":
                deploy_interactive(project_root, last_zip)
            elif c == "3":
                if compile_project(project_root):
                    last_zip = package_zip(project_root)
                    if last_zip and confirm("Deploy binary payload?"): deploy_interactive(project_root, last_zip)
            elif c == "4":
                inspect_project(project_root)
            elif c == "5":
                ok("Synced Arrays Extracted from Config.bs:")
                for s in cfg.get("servers",[]): print(f"  {s.get('badge', '')} {clr(s.get('name', ''), C)}")
                print(); ok("Synced Endpoints Extracted from Config.bs:")
                for r in cfg.get("rows",[]): print(f"  {clr(r.get('title', ''), M)} ({r.get('endpoint', '')})")
            elif c == "6":
                tmdb_tester(cfg["tmdb_key"])
            elif c == "7":
                print("\n  [B]uild Server Links | [P]ing Global Nodes")
                u = input("  URL Engine> ").strip().upper()
                if u == "B": server_url_tester(cfg)
                elif u == "P": bulk_server_ping(cfg)
            elif c == "8":
                print("\n  [P]ull | [S]tatus | [L]og | [D]iff | [C]hangelog")
                g = input("  Git-Mesh> ").strip().upper()
                if g == "P": git_pull(project_root)
                elif g == "S": git_status(project_root)
                elif g == "L": git_log(project_root)
                elif g == "D": git_diff(project_root)
                elif g == "C": generate_changelog(project_root)
            elif c == "9":
                print("\n  [S]can Subnet | [R]emote Control (ECP)")
                n = input("  Net> ").strip().upper()
                if n == "S": scan_roku_on_network()
                elif n == "R": roku_remote_tool(input("  Device IP: ").strip())
            elif c == "W":
                watchdog(project_root)
            elif c == "D":
                za = project_root / input("  Relative Local Zip A (.zip): ")
                zb = project_root / input("  Relative Local Zip B (.zip): ")
                if za.exists() and zb.exists(): compare_zips(za, zb)
                else: err("Binaries not located at given paths")
            elif c == "M":
                edit_manifest(project_root)
            elif c == "R": 
                launch_rich_dashboard(project_root, cfg)
            elif c == "T": 
                launch_turtle_hud(project_root, cfg)
            elif c == "Q": 
                blank(); ok("System Detached. End of Line."); break
            else:
                warn("Command Unrecognized by Neural Mesh.")
            
        except KeyboardInterrupt: warn("\nInterrupt Detected. Use 'Q' to quit.")
        except Exception as e: err(f"CRITICAL PROCESS FAULT: {e}")

if __name__ == "__main__":
    main()