#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import time

POOL = "stratum+tcp://public-pool.io:21496"
MINER_DIR = os.path.expanduser("~/cpuminer-multi")
MINER_BIN = os.path.expanduser("~/cpuminer")

def run(cmd):
    subprocess.run(cmd, shell=True)

def clear():
    os.system("clear")

def is_valid_btc(address):
    pattern = r"^(1|3|bc1q)[a-zA-HJ-NP-Z0-9]{25,62}$"
    return re.match(pattern, address) is not None

def install_dependencies():
    print("[+] Installing dependencies...")
    run("pkg update -y")
    run("pkg install -y git clang make automake autoconf libtool pkg-config openssl")

def install_cpuminer():
    if os.path.exists(MINER_BIN):
        print("[✓] cpuminer already installed")
        return

    print("[+] Installing cpuminer-multi...")
    if not os.path.exists(MINER_DIR):
        run(f"git clone https://github.com/tpruvot/cpuminer-multi {MINER_DIR}")

    os.chdir(MINER_DIR)
    run("./build.sh")
    run(f"cp cpuminer {MINER_BIN}")
    run(f"chmod +x {MINER_BIN}")
    os.chdir(os.path.expanduser("~"))

def start_miner(address):
    clear()
    print("=== PUBLIC-POOL.IO SOLO LOTTERY MINER ===\n")
    print(f"Pool: public-pool.io")
    print(f"Address: {address}")
    print(f"Threads: {os.cpu_count()}")
    print("\nPress CTRL+C to stop\n")
    time.sleep(2)

    cmd = [
        MINER_BIN,
        "-a", "sha256d",
        "-o", POOL,
        "-u", address,
        "-p", "x",
        "-t", str(os.cpu_count())
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[!] Miner stopped")

def main():
    clear()
    print("=== BITCOIN SOLO LOTTERY SETUP ===\n")

    address = input("[?] Enter your Bitcoin address: ").strip()

    if not is_valid_btc(address):
        print("\n[!] Invalid Bitcoin address")
        sys.exit(1)

    install_dependencies()
    install_cpuminer()
    start_miner(address)

if __name__ == "__main__":
    main()
      
