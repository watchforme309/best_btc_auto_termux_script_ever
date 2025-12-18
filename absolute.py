
#!/usr/bin/env python3
import os, subprocess, time, socket, threading, re, sys

BTC_ADDRESS = "32QLDQf4UNqCNJTKYBNXK2jzSnSctWfwc4"

# Fewer pools = more hashes per pool
POOLS = [
    ("CKPOOL", "solo.ckpool.org", 3333),
    ("ZSOLO",  "btc.zsolo.bid",    6057),
]

CPU_CORES = os.cpu_count() or 4
MINER_DIR = os.path.expanduser("~/cpuminer-multi")
MINER_BIN = f"{MINER_DIR}/cpuminer"

best_diff = 0.0
accepted = 0
lock = threading.Lock()
start = time.time()

# ---------- UTIL ----------
def run(cmd):
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def pool_alive(h, p):
    try:
        socket.create_connection((h, p), timeout=5).close()
        return True
    except:
        return False

# ---------- INSTALL ----------
def install():
    run("pkg update -y")
    run("pkg install -y git clang make automake autoconf libtool pkg-config openssl python")

    if not os.path.exists(MINER_BIN):
        run("git clone https://github.com/tpruvot/cpuminer-multi.git")
        os.chdir(MINER_DIR)
        run("./autogen.sh")
        run("./configure CFLAGS='-O3 -fomit-frame-pointer -funroll-loops'")
        run(f"make -j{CPU_CORES}")
        os.chdir("..")

# ---------- MINER ----------
def miner(pool, threads):
    global best_diff, accepted
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

    diff_re = re.compile(r"diff[^0-9]*([0-9]*\.?[0-9]+)")

    for line in proc.stdout:
        l = line.lower()

        if "accepted" in l:
            with lock:
                accepted += 1

        m = diff_re.search(l)
        if m:
            try:
                d = float(m.group(1))
                with lock:
                    if d > best_diff:
                        best_diff = d
            except:
                pass

# ---------- DASH ----------
def dashboard():
    while True:
        up = int(time.time() - start)
        load = os.getloadavg()[0]
        with lock:
            bd = best_diff
            ac = accepted

        os.system("clear")
        print("⛏️  BTC TERMUX MAX HASH (HONEST)")
        print("=" * 45)
        print(f"BTC Address     : {BTC_ADDRESS}")
        print(f"CPU Cores       : {CPU_CORES}")
        print(f"CPU Load        : {load:.2f}")
        print(f"Accepted Shares : {ac}")
        print(f"Best Share Diff : {bd:.8f}")
        print(f"Uptime          : {up}s")
        print("=" * 45)
        print("✔ Absolute max achievable on Android CPU")
        time.sleep(2)

# ---------- MAIN ----------
def main():
    install()

    alive = [p for p in POOLS if pool_alive(p[1], p[2])]
    if not alive:
        print("No pools alive")
        sys.exit(1)

    threads_each = max(1, CPU_CORES // len(alive))

    for p in alive:
        threading.Thread(target=miner, args=(p, threads_each), daemon=True).start()
        time.sleep(0.5)

    dashboard()

if __name__ == "__main__":
    main()
