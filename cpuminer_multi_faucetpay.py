import os
import subprocess
import sys
import time
import signal
import multiprocessing

HOME = os.path.expanduser("~")
MINER_DIR = f"{HOME}/cpuminer-multi"
MINER_BIN = f"{MINER_DIR}/cpuminer"
LOG_FILE = f"{HOME}/cpuminer.log"

THREADS = multiprocessing.cpu_count()
SWITCH_TIME = 600  # seconds per algo

# FaucetPay compatible profit-switching pools (cpuminer-multi supported)
POOLS = [
    ("sha256d", "stratum+tcp://sha256.mine.zpool.ca:3333"),
    ("scrypt",  "stratum+tcp://scrypt.mine.zpool.ca:3433"),
    ("x11",     "stratum+tcp://x11.mine.zpool.ca:3533"),
    ("x13",     "stratum+tcp://x13.mine.zpool.ca:3633"),
    ("lyra2z",  "stratum+tcp://lyra2z.mine.zpool.ca:4553"),
]

running = True
current_proc = None

def run(cmd):
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def install_dependencies():
    run("pkg update -y")
    run("pkg install -y git clang make automake autoconf libtool python")

def install_cpuminer():
    if os.path.exists(MINER_BIN):
        print("[✓] cpuminer-multi already installed")
        return

    print("[*] Installing cpuminer-multi")
    run(f"rm -rf {MINER_DIR}")
    run(f"git clone https://github.com/tpruvot/cpuminer-multi {MINER_DIR}")
    os.chdir(MINER_DIR)
    run("./autogen.sh")
    run("CFLAGS='-O2' ./configure")
    run(f"make -j{THREADS}")

def start_miner(email, algo, pool):
    os.chdir(MINER_DIR)
    cmd = (
        f"{MINER_BIN} "
        f"-a {algo} "
        f"-o {pool} "
        f"-u {email} "
        f"-p c=BTC,mc=BTC "
        f"-t {THREADS}"
    )
    return subprocess.Popen(
        cmd,
        shell=True,
        stdout=open(LOG_FILE, "a"),
        stderr=subprocess.STDOUT
    )

def profit_switch(email):
    global current_proc
    i = 0

    while running:
        algo, pool = POOLS[i % len(POOLS)]
        print(f"[+] Switching to {algo}")

        if current_proc:
            current_proc.terminate()
            time.sleep(3)

        current_proc = start_miner(email, algo, pool)
        start = time.time()

        while time.time() - start < SWITCH_TIME:
            if not running:
                return
            if current_proc.poll() is not None:
                print("[!] Miner crashed — restarting")
                current_proc = start_miner(email, algo, pool)
            time.sleep(5)

        i += 1

def shutdown(sig, frame):
    global running
    running = False
    run("pkill cpuminer")
    print("\n[✓] Miner stopped safely")
    sys.exit(0)

def main():
    print("=== cpuminer-multi MAX CPU FaucetPay Miner (Termux) ===\n")
    email = input("Enter FaucetPay EMAIL: ").strip()

    if "@" not in email:
        print("Invalid FaucetPay email")
        sys.exit(1)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    install_dependencies()
    install_cpuminer()

    print(f"[✓] Using {THREADS} CPU threads (MAX)")
    print("[✓] Profit switching enabled")
    print("[✓] Auto convert → BTC → FaucetPay\n")

    profit_switch(email)

if __name__ == "__main__":
    main()

