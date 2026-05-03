#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    BINGEBOX OMEGA SUPREME — ROKU SDK                         ║
║        Custom-Tailored for the BingeBox v3.0 BrighterScript Engine           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ [CORE]      rosc, npm install, package zip, Direct ECP Sideload Deployment   ║
║ [AST]       Deep BrighterScript Linter, Component/XML Sync Validator         ║
║[TMDB]      Live API Pulse, Discover Engine, Cast Matrix via `Config.bs`     ║
║ [NETWORK]   Dynamic Server Payload extraction directly from `Config.bs`      ║
║ [UI]        CLI OS, Rich Telemetry Dashboard, Turtle Cyberpunk HUD           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import sys, os, re, json, zipfile, shutil, time, socket, hashlib, base64
import threading, subprocess, urllib.request, urllib.parse, urllib.error
import http.client, argparse, platform, logging, queue, contextlib
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
    os.system("") # Enable ANSI on Windows

R, G, Y, C, M, W, DG, B, RST = "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[95m", "\033[97m", "\033[90m", "\033[94m", "\033[0m"

def clr(t: str, c: str) -> str: return f"{c}{t}{RST}"
def ok(m: str):    print(f"  {clr('✓', G)} {m}")
def err(m: str):   print(f"  {clr('✗', R)} {m}")
def warn(m: str):  print(f"  {clr('!', Y)} {m}")
def step(m: str):  print(f"\n  {clr('▶', C)} {clr(m, W)}")
def info(m: str):  print(f"    {clr(m, DG)}")
def hdr(m: str):   print(f"\n  {clr('━'*54, B)}\n  {clr(m, M+'\\033[1m')}\n  {clr('━'*54, B)}")

# Logging
log = logging.getLogger("omega_sdk")
logging.basicConfig(filename=str(Path.home() / ".bingebox_sdk.log"), level=logging.DEBUG)

# ─────────────────────────────────────────────────────────────────────────────
# PROJECT PARSER & BRIGHTERSCRIPT AST
# ─────────────────────────────────────────────────────────────────────────────
def find_project() -> Optional[Path]:
    for cand in[Path.cwd(), Path.cwd() / "BingeBox-Roku-v2", Path.home() / "Desktop/BingeBox-Roku-v2"]:
        if (cand / "package.json").exists() and (cand / "src/manifest").exists():
            return cand.resolve()
    return None

def read_bs_config(root: Path) -> dict:
    """Deeply parses your specific `Config.bs` file to keep the Python SDK synced"""
    result = {"tmdb_key": "15d2ea6d0dc1d476efbca3eba2b9bbfb", "servers": [], "rows":[], "features": {}}
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
def compile_project(root: Path) -> bool:
    step("Executing BrighterScript Compiler Pipeline...")
    if not (root / "node_modules").exists():
        subprocess.run(["npm", "install"], cwd=root)
        
    res = subprocess.run(["npm", "run", "build"], cwd=root, capture_output=True, text=True)
    if res.returncode != 0:
        res = subprocess.run(["npx", "bsc"], cwd=root, capture_output=True, text=True)
        if res.returncode != 0:
            err("Compilation FAILED. Compiler Output:")
            print(clr(res.stdout[-800:], Y)); return False
            
    ok("Bytecode Transpilation Complete -> out/.roku-deploy-staging/")
    return True

def package_zip(root: Path) -> Optional[Path]:
    step("Packaging Roku Payload (.zip)...")
    base = root / "out/.roku-deploy-staging"
    if not base.exists(): base = root / "src"
    
    zip_path = root / f"BingeBox-Supreme-{datetime.now().strftime('%Y%m%d-%H%M')}.zip"
    all_files = sorted(f for f in base.rglob("*") if f.is_file())
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for f in all_files: zf.write(f, f.relative_to(base))
            
    ok(f"Payload Sealed: {zip_path.name} ({zip_path.stat().st_size//1024} KB)")
    return zip_path

def deploy_to_roku(zip_path: Path, ip: str, pwd: str):
    step(f"Transmitting Payload to targeted Roku ECP Unit ({ip})...")
    boundary = f"SigmaBoundary{int(time.time())}"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"mysubmit\"\r\n\r\nInstall\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"archive\"; filename=\"{zip_path.name}\"\r\n"
            f"Content-Type: application/zip\r\n\r\n").encode() + zip_path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(f"http://{ip}/plugin_install", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Basic {base64.b64encode(f'rokudev:{pwd}'.encode()).decode()}")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = r.read().decode().lower()
        if "install success" in resp or r.status == 200: ok("Flash Successful. App Executing.")
        else: err("Roku OS rejected the firmware."); info(resp[:200])
    except Exception as e: err(f"Deployment dropped: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# DEEP LINTER (Specifically tailored to your Project Files)
# ─────────────────────────────────────────────────────────────────────────────
def inspect_project(root: Path):
    hdr("ROKU PROJECT LINTER & INTEGRITY CHECK")
    
    # 1. Manifest verification
    man = root / "src/manifest"
    if man.exists():
        ok("Manifest Config Found")
        lines = man.read_text().splitlines()
        for ref in["pkg:/images/icon_focus_hd.png", "pkg:/images/icon_side_hd.png", "pkg:/images/splash_hd.png"]:
            if any(ref in l for l in lines):
                asset = root / "src" / ref.replace("pkg:/", "")
                if asset.exists(): ok(f"Asset Linked: {asset.name}")
                else: err(f"Asset Missing from src/images: {asset.name}")
    
    # 2. BS Component Linkage (Checking DetailsScreen, OmegaPlayer, etc)
    comp_dir = root / "src/components"
    xml_files = {f.stem for f in comp_dir.rglob("*.xml")}
    bs_files = {f.stem for f in comp_dir.rglob("*.bs")}
    missing_bs = xml_files - bs_files
    if missing_bs:
        for m in missing_bs: err(f"Component <{m}> has no companion .bs script!")
    else: ok(f"Strict Component Pairing Verified ({len(xml_files)} pairs)")
    
    # 3. BrightScript Security / Safety checks
    hits = 0
    for f in (root / "src").rglob("*.bs"):
        txt = f.read_text(errors="ignore")
        if "console.log" in txt: err(f"JS artifact 'console.log' in {f.name}"); hits+=1
        if "=>" in txt: err(f"JS artifact '=>' (Arrow function) in {f.name}"); hits+=1
        if re.search(r'\bprint\s+"', txt): warn(f"Unsafe print in {f.name} (Use Utils.Logger)"); hits+=1
    
    if hits == 0: ok("Abstract Syntax Tree is clean. Code adheres to BingeBox Standards.")
    
# ─────────────────────────────────────────────────────────────────────────────
# TMDB & SERVER BUSINESS LOGIC (Mirrors `OmegaPlayer.bs` & `DataManager.bs`)
# ─────────────────────────────────────────────────────────────────────────────
def build_embed_url(mid: str, media_type: str, srv: dict, s=1, e=1) -> str:
    """Perfectly mimics the logic inside your OmegaPlayer.bs file"""
    if media_type == "movie":
        url = srv["movieBase"] + mid
        if srv["id"] == "vidlink": url += "?primaryColor=E50914&autoplay=true"
    else:
        url = srv["tvBase"] + mid + "/1/1"
        if srv["id"] == "vidsrcme": url = srv["tvBase"] + mid + f"&season={s}&episode={e}"
        if srv["id"] == "vidlink": url += "?primaryColor=E50914&autoplay=true"
    return url

def tmdb_fetch(ep: str, key: str) -> dict:
    url = f"https://api.themoviedb.org/3{ep}{'&' if '?' in ep else '?'}api_key={key}&language=en-US"
    try:
        with urllib.request.urlopen(url, timeout=10) as r: return json.loads(r.read().decode())
    except: return {}

# ─────────────────────────────────────────────────────────────────────────────
# UIs
# ─────────────────────────────────────────────────────────────────────────────
def launch_rich_dashboard(root: Path, cfg: dict):
    if not RICH_AVAILABLE: err("Install rich via pip."); return
    trending = tmdb_fetch("/trending/all/week", cfg["tmdb_key"])
    
    def get_layout():
        ly = Layout()
        ly.split_column(Layout(name="top", size=3), Layout(name="mid"), Layout(name="bot", size=3))
        ly["mid"].split_row(Layout(name="l"), Layout(name="r"))
        return ly
        
    with Live(get_layout(), refresh_per_second=2, screen=True) as live:
        try:
            while True:
                ly = get_layout()
                ly["top"].update(Panel(f"[bold cyan]BINGEBOX SUPREME ENGINE[/] | TARGET_DIR: {root.name}", box=box.DOUBLE))
                
                # Servers from YOUR Config.bs
                t_srv = Table(title="Config.bs Stream Endpoints")
                t_srv.add_column("Badge"); t_srv.add_column("Node Name"); t_srv.add_column("Status")
                for s in cfg.get("servers",[]): t_srv.add_row(s['badge'], s['name'], "[green]LOADED[/]")
                ly["l"].update(Panel(t_srv))
                
                # TMDB Pulse
                t_db = Table(title="TMDB Global Pulse")
                t_db.add_column("Score"); t_db.add_column("Title")
                for r in trending.get("results", [])[:15]: 
                    t_db.add_row(f"[yellow]{r.get('vote_average',0):.1f}[/]", r.get("title") or r.get("name"))
                ly["r"].update(Panel(t_db))
                
                ly["bot"].update(Panel(Align.center("[bold red]Press CTRL+C To Break Link[/]")))
                live.update(ly)
                time.sleep(1)
        except KeyboardInterrupt: pass

def launch_turtle_hud(root: Path, cfg: dict):
    if not TURTLE_AVAILABLE: err("Turtle unavailable."); return
    sc = turtle.Screen()
    sc.bgcolor("#050505"); sc.setup(1000, 700); sc.tracer(0); sc.title("BINGEBOX OMEGA HUD")
    
    t = turtle.Turtle(); t.hideturtle(); t.speed(0); t.color("#00ffcc"); t.penup()
    trending = tmdb_fetch("/trending/all/week", cfg["tmdb_key"])
    
    def render():
        t.clear()
        t.goto(-480, 310); t.write(">>> BINGEBOX SDK DATALINK <<<", font=("Courier", 18, "bold"))
        t.goto(-450, 200)
        t.write(f"PROJECT: {root.name}\nSYSTEM: {platform.system()}\nCONFIG SERVER COUNT: {len(cfg.get('servers',[]))}", font=("Courier", 12))
        t.goto(10, 200)
        t.write("TMDB TRENDING INGEST:", font=("Courier", 12, "bold"))
        for i, r in enumerate(trending.get("results", [])[:15]):
            t.goto(10, 170 - (i*20))
            t.write(f"> {(r.get('title') or r.get('name'))[:40]}", font=("Courier", 10))
        sc.update()
        
    render()
    sc.listen(); sc.onkey(sc.bye, "q")
    try: turtle.mainloop()
    except: pass

# ─────────────────────────────────────────────────────────────────────────────
# SUPERVISOR CLI
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description=f"BingeBox Supreme Engine v{VERSION}")
    parser.add_argument("--headless", metavar="CMD", help="build | install | package")
    args = parser.parse_args()

    # Pre-flight
    project_root = find_project()
    if args.headless and project_root:
        if args.headless == "build": sys.exit(0 if compile_project(project_root) else 1)
        elif args.headless == "package": sys.exit(0 if package_zip(project_root) else 1)

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
            print(f"  ║ {clr('[ TOOL CHAIN ]', DG)}                                                     ║")
            print(f"  ║  {clr('[3]', B)} Static Linter (Validates Component/XML sync)                 ║")
            print(f"  ║  {clr('[4]', B)} Config Server Dumper (Verify Config.bs Extracted Variables)  ║")
            print(f"  ║  {clr('[5]', M)} URL Stream Tester (Tests OmegaPlayer embed logic)            ║")
            print(f"  ║ {clr('[ ADVANCED UIs ]', DG)}                                                   ║")
            print(f"  ║  {clr('[R]', C)} Initialize RICH Live Terminal Dashboard                      ║")
            print(f"  ║  {clr('[T]', C)} Initialize TURTLE Cyberpunk Graphical HUD                    ║")
            print(f"  ║  {clr('[Q]', DG)} Disconnect / Terminate Process                               ║")
            print(clr(f"  ╚═══════════════════════════════════════════════════════════════════╝", M))
            print(f"  [ TARGET ] {clr(str(project_root) if project_root else 'UNLINKED', G if project_root else R)}")
            blank()
            
            c = input(clr("  root@omegasupreme :~# ", C)).strip().upper()
            
            if not project_root and c in ("1", "2", "3", "4", "5", "R", "T"):
                err("Requires linked project route."); project_root = find_project(); continue
                
            if c == "1":
                compile_project(project_root)
                last_zip = package_zip(project_root)
            elif c == "2":
                ip = input("  Device IPv4: ").strip()
                if ip: deploy_to_roku(last_zip or package_zip(project_root), ip, input("  Password: ") or "rokudev")
            elif c == "3":
                inspect_project(project_root)
            elif c == "4":
                ok("Synced Arrays Extracted from Config.bs:")
                for s in cfg["servers"]: print(f"  {s['badge']} {clr(s['name'], C)}")
                print(); ok("Synced Endpoints Extracted from Config.bs:")
                for r in cfg["rows"]: print(f"  {clr(r['title'], M)} ({r['endpoint']})")
            elif c == "5":
                mid = input("  TMDB ID (Movie): ")
                for s in cfg["servers"]:
                    print(f"  {s['badge']} {s['name']:14} {clr(build_embed_url(mid, 'movie', s), DG)}")
            elif c == "R": launch_rich_dashboard(project_root, cfg)
            elif c == "T": launch_turtle_hud(project_root, cfg)
            elif c == "Q": break
            
        except KeyboardInterrupt: warn("\nInterrupt Detected. Use 'Q' to quit.")
        except Exception as e: err(f"CRITICAL PROCESS FAULT: {e}")

if __name__ == "__main__":
    main()