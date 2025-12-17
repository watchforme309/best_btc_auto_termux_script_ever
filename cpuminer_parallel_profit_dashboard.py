#!/usr/bin/env python3

import os
import sys
import time
import json
import signal
import subprocess
import multiprocessing
from urllib.request import urlopen, Request

# ---------------- PATHS ----------------
HOME = os.path.expanduser("~")
MINER_DIR = f"{HOME}/cpuminer-multi"
MINER_BIN = f"{MINER_DIR}/cpuminer"
LOG_DIR = f"{HOME}/miner_logs"
API_CACHE = f"{HOME}/profit_cache.json"

CPU_THREADS = multiprocessing.cpu_count()

# ---------------- ALGORITHMS (NO LYRA2Z) ----------------
ALGORITHMS = {
    "sha256d": "stratum+tcp://sha256.mine.zpool.ca:3333",
    "scrypt":  "stratum+tcp://scrypt.mine.zpool.ca:3433",
    "x11":     "stratum+tcp://x11.mine.zpool.ca:3533",
    "x13":     "stratum+tcp://x13.mine.zpool.ca:3633",
}

API_REFRESH = 300   # seconds
DASH_REFRESH = 5    # seconds

running = True
miners = {}
profit_table = {}

# ---------------- UTIL ----------------
def run(cmd):
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---------------- INSTALL ----------------
def install_deps():
    run("pkg update -y")
    run("pkg install -y python git clang make automake autoconf libtool")

def install_cpuminer():
    if os.path.exists(MINER_BIN):
        return
    run(f"rm -rf {MINER_DIR}")
    run(f"git clone https://github.com/tpruvot/cpuminer-multi {MINER_DIR}")
    os.chdir(MINER_DIR)
    run("./autogen.sh")
    run("CFLAGS='-O2' ./configure")
    run(f"make -j{CPU_THREADS}")

# ---------------- PROFIT API ----------------
def fetch_profit_api():
    url = "https://www.zpool.ca/api/status"
    try:
        req = Request(url, headers={"User-Agent": "TermuxMiner"})
        with urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())

        table = {}
        for algo, info in data.items():
            if algo in ALGORITHMS:
                table[algo] = float(info.get("estimate", 0))

        with open(API_CACHE, "w") as f:
            json.dump(table, f)

        return table
    except Exception:
        if os.path.exists(API_CACHE):
            with open(API_CACHE) as f:
                return json.load(f)
        return {}

# ---------------- MINING ----------------
def start_miner(email, algo, pool):
    log = f"{LOG_DIR}/{algo}.log"
    cmd = (
        f"{MINER_BIN} "
        f"-a {algo} "
        f"-o {pool} "
        f"-u {email} "
        f"-p c=BTC,mc=BTC "
        f"-t {CPU_THREADS}"
    )
    return subprocess.Popen(
        cmd,
        shell=True,
        stdout=open(log, "a"),
        stderr=subprocess.STDOUT
    )

def start_all_miners(email):
    os.makedirs(LOG_DIR, exist_ok=True)
    os.chdir(MINER_DIR)

    for algo, pool in ALGORITHMS.items():
        miners[algo] = start_miner(email, algo, pool)
        time.sleep(2)

# ---------------- DASHBOARD ----------------
def clear():
    os.system("clear" if os.name == "posix" else "cls")

def parse_hashrate(logfile):
    if not os.path.exists(logfile):
        return "-"
    try:
        with open(logfile, "rb") as f:
            f.seek(-4096, os.SEEK_END)
            tail = f.read().decode(errors="ignore")

        for line in reversed(tail.splitlines()):
            l = line.lower()
            if "kh/s" in l or "mh/s" in l or "gh/s" in l:
                return line.strip()[:70]
    except Exception:
        pass
    return "-"

def dashboard(email):
    global profit_table
    last_api = 0

    while running:
        now = time.time()
        if now - last_api > API_REFRESH:
            profit_table = fetch_profit_api()
            last_api = now

        clear()
        print("=== CPUMINER-MULTI PARALLEL DASHBOARD ===")
        print(f"CPU cores: {CPU_THREADS} | FaucetPay: {email}")
        print("----------------------------------------")

        for algo in ALGORITHMS:
            log = f"{LOG_DIR}/{algo}.log"
            rate = parse_hashrate(log)
            profit = profit_table.get(algo, 0)
            print(f"{algo:<8} | est BTC/MH/day: {profit:<12} | {rate}")

        print("\nCTRL+C to stop all miners")
        time.sleep(DASH_REFRESH)

# ---------------- SHUTDOWN ----------------
def shutdown(sig, frame):
    global running
    running = False
    run("pkill cpuminer")
    print("\n[✓] All miners stopped")
    sys.exit(0)

# ---------------- MAIN ----------------
def main():
    print("=== CPUMINER-MULTI EXTREME PARALLEL MODE ===\n")
    email = input("Enter FaucetPay EMAIL: ").strip()

    if "@" not in email:
        print("Invalid FaucetPay email")
        sys.exit(1)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    install_deps()
    install_cpuminer()

    print("[✓] Starting ALL miners in parallel")
    print("[!] NO CPU limits enabled – extreme load\n")

    start_all_miners(email)
    dashboard(email)

if __name__ == "__main__":
    main()
      
