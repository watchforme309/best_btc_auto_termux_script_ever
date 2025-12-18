#!/usr/bin/env python3
import os
import subprocess
import time
import socket
import threading
import sys
import re

# ================= CONFIG =================
BTC_ADDRESS = "32QLDQf4UNqCNJTKYBNXK2jzSnSctWfwc4"

POOLS = [
    ("CKPOOL",  "solo.ckpool.org", 3333),
    ("ZSOLO",   "btc.zsolo.bid",    6057),
    ("ANTPOOL", "solo.antpool.com", 3333),
    ("PUBLIC",  "public-pool.io",   21496),
]

CPU_CORES = os.cpu_count() or 4
MINER_DIR = os.path.expanduser("~/cpuminer-multi")
MINER_BIN = f"{MINER_DIR}/cpuminer"

# ================= STATE =================
best_share_diff = 0.0
accepted_shares = 0
start_time = time.time()
miners_running = 0

lock = threading.Lock()

# ================= UTIL =================
def run(cmd):
    subprocess.run(
        cmd, shell=True, check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def clear():
    os.system("clear")

def pool_alive(host, port):
    try:
        socket.create_connection((host, port), timeout=5).close()
        return True
    except:
        return False

# ================= INSTALL =================
def install():
    print("[*] Installing dependencies...")
    run("pkg update -y")
    run("pkg install -y git clang make automake autoconf libtool pkg-config openssl python")

    if not os.path.exists(MINER_BIN):
        print("[*] Building cpuminer-multi...")
        run("git clone https://github.com/tpruvot/cpuminer-multi.git")
        os.chdir(MINER_DIR)
        run("./autogen.sh")
        run("./configure CFLAGS='-O3'")
        run(f"make -j{CPU_CORES}")
        os.chdir("..")

# ================= MINER =================
def miner_thread(pool, threads):
    global best_share_diff, accepted_shares

    name, host, port = pool

    cmd = (
        f"{MINER_BIN} "
        f"-a sha256d "
        f"-o stratum+tcp://{host}:{port} "
        f"-u {BTC_ADDRESS} "
        f"-p x "
        f"-t {threads}"
    )

    proc = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    diff_regex = re.compile(r"diff(?:iculty)?\s*[:=]?\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)

    for line in proc.stdout:
        line = line.strip().lower()

        if "accepted" in line:
            with lock:
                accepted_shares += 1

        match = diff_regex.search(line)
        if match:
            try:
                diff = float(match.group(1))
                with lock:
                    if diff > best_share_diff:
                        best_share_diff = diff
            except:
                pass

# ================= DASHBOARD =================
def dashboard():
    while True:
        uptime = int(time.time() - start_time)
        load = os.getloadavg()[0]

        with lock:
            best = best_share_diff
            acc = accepted_shares

        clear()
        print("⛏️  BTC NERDMINER-STYLE LOTTERY MINER (TERMUX)")
        print("=" * 55)
        print(f"BTC Address      : {BTC_ADDRESS}")
        print(f"CPU Cores        : {CPU_CORES}")
        print(f"Active Miners    : {miners_running}")
        print(f"CPU Load         : {load:.2f}")
        print(f"Accepted Shares  : {acc}")
        print(f"Best Share Diff  : {best:.8f}")
        print(f"Uptime           : {uptime}s")
        print("=" * 55)
        print("✔ Hashing ACTIVE (CPU-bound)")
        print("⚠️  Lottery mining — extremely low odds")
        time.sleep(2)

# ================= MAIN =================
def main():
    global miners_running

    install()

    alive_pools = [p for p in POOLS if pool_alive(p[1], p[2])]
    if not alive_pools:
        print("[X] No pools available")
        sys.exit(1)

    threads_per_pool = max(1, CPU_CORES // len(alive_pools))

    for pool in alive_pools:
        t = threading.Thread(
            target=miner_thread,
            args=(pool, threads_per_pool),
            daemon=True
        )
        t.start()
        miners_running += 1
        time.sleep(0.5)

    dashboard()

# ================= RUN =================
if __name__ == "__main__":
    main()

