import os
import subprocess
import sys
import time
import signal
import multiprocessing

HOME = os.path.expanduser("~")
MINER_DIR = f"{HOME}/cpuminer-multi"
MINER_BIN = f"{MINER_DIR}/cpuminer"
LOG_DIR = f"{HOME}/miner_logs"

TOTAL_THREADS = multiprocessing.cpu_count()

# Divide CPU threads evenly across miners
POOLS = [
    ("sha256d", "stratum+tcp://sha256.mine.zpool.ca:3333"),
    ("scrypt",  "stratum+tcp://scrypt.mine.zpool.ca:3433"),
    ("x11",     "stratum+tcp://x11.mine.zpool.ca:3533"),
    ("x13",     "stratum+tcp://x13.mine.zpool.ca:3633"),
    ("lyra2z",  "stratum+tcp://lyra2z.mine.zpool.ca:4553"),
]

THREADS_PER_MINER = max(1, TOTAL_THREADS // len(POOLS))
running = True
miners = {}

def run(cmd):
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def install_deps():
    run("pkg update -y")
    run("pkg install -y git clang make automake autoconf libtool python")

def install_cpuminer():
    if os.path.exists(MINER_BIN):
        return
    run(f"rm -rf {MINER_DIR}")
    run(f"git clone https://github.com/tpruvot/cpuminer-multi {MINER_DIR}")
    os.chdir(MINER_DIR)
    run("./autogen.sh")
    run("CFLAGS='-O2' ./configure")
    run(f"make -j{TOTAL_THREADS}")

def start_miner(email, algo, pool):
    log = f"{LOG_DIR}/{algo}.log"
    cmd = (
        f"{MINER_BIN} "
        f"-a {algo} "
        f"-o {pool} "
        f"-u {email} "
        f"-p c=BTC,mc=BTC "
        f"-t {THREADS_PER_MINER}"
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

    for algo, pool in POOLS:
        print(f"[+] Starting {algo} ({THREADS_PER_MINER} threads)")
        miners[algo] = start_miner(email, algo, pool)
        time.sleep(2)

def monitor_miners(email):
    while running:
        for algo, proc in list(miners.items()):
            if proc.poll() is not None:
                print(f"[!] {algo} crashed — restarting")
                miners[algo] = start_miner(email, algo, POOLS_DICT[algo])
        time.sleep(10)

def shutdown(sig, frame):
    global running
    running = False
    run("pkill cpuminer")
    print("\n[✓] All miners stopped")
    sys.exit(0)

# Build lookup dict
POOLS_DICT = {a: p for a, p in POOLS}

def main():
    print("=== PARALLEL cpuminer-multi FaucetPay Miner (Termux) ===\n")
    email = input("Enter FaucetPay EMAIL: ").strip()

    if "@" not in email:
        print("Invalid FaucetPay email")
        sys.exit(1)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    install_deps()
    install_cpuminer()

    print(f"[✓] CPU cores detected: {TOTAL_THREADS}")
    print(f"[✓] Threads per miner: {THREADS_PER_MINER}")
    print("[✓] All miners running in parallel")
    print("[✓] Auto convert → BTC → FaucetPay\n")

    start_all_miners(email)
    monitor_miners(email)

if __name__ == "__main__":
    main()
  
