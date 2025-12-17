import os
import subprocess
import sys
import time
import signal
import multiprocessing

HOME = os.path.expanduser("~")
MINER_DIR = f"{HOME}/cpuminer-multi"
MINER_BIN = f"{MINER_DIR}/cpuminer"
LOG_FILE = f"{HOME}/miner.log"

CPU_THREADS = multiprocessing.cpu_count()

# Profit-switching pool list (FaucetPay compatible)
POOLS = [
    ("sha256d", "stratum+tcp://sha256.mine.zpool.ca:3333"),
    ("scrypt",  "stratum+tcp://scrypt.mine.zpool.ca:3433"),
    ("x11",     "stratum+tcp://x11.mine.zpool.ca:3533"),
    ("x13",     "stratum+tcp://x13.mine.zpool.ca:3633"),
    ("lyra2z",  "stratum+tcp://lyra2z.mine.zpool.ca:4553"),
]

SWITCH_INTERVAL = 600  # seconds per algo (10 min)

running = True
current_proc = None

def run(cmd):
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def ensure_packages():
    run("pkg update -y")
    run("pkg install -y python git clang make automake autoconf libtool")

def install_miner():
    if os.path.exists(MINER_BIN):
        return
    run(f"rm -rf {MINER_DIR}")
    run(f"git clone https://github.com/tpruvot/cpuminer-multi {MINER_DIR}")
    os.chdir(MINER_DIR)
    run("./autogen.sh")
    run("CFLAGS='-O2' ./configure")
    run(f"make -j{CPU_THREADS}")

def start_miner(email, algo, pool):
    os.chdir(MINER_DIR)
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
        stdout=open(LOG_FILE, "a"),
        stderr=subprocess.STDOUT
    )

def profit_switch_loop(email):
    global current_proc
    idx = 0

    while running:
        algo, pool = POOLS[idx % len(POOLS)]
        print(f"[+] Switching to {algo} | {pool}")

        if current_proc:
            current_proc.terminate()
            time.sleep(3)

        current_proc = start_miner(email, algo, pool)

        start = time.time()
        while time.time() - start < SWITCH_INTERVAL:
            if not running:
                return
            if current_proc.poll() is not None:
                print("[!] Miner crashed — restarting")
                current_proc = start_miner(email, algo, pool)
            time.sleep(5)

        idx += 1

def shutdown(sig, frame):
    global running
    running = False
    run("pkill cpuminer")
    print("\n[✓] Miner stopped")
    sys.exit(0)

def main():
    global running

    print("=== MAX CPU PROFIT SWITCHING FaucetPay Miner ===\n")
    email = input("Enter FaucetPay EMAIL: ").strip()

    if "@" not in email:
        print("Invalid email")
        sys.exit(1)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    ensure_packages()
    install_miner()

    print(f"[✓] Using {CPU_THREADS} CPU threads (MAX)")
    print("[✓] Profit switching enabled")
    print("[✓] BTC auto-convert → FaucetPay\n")

    profit_switch_loop(email)

if __name__ == "__main__":
    main()

