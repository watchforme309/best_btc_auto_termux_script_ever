
#!/usr/bin/env python3
# TERMUX BTC STRATUM MINER — CKPOOL + PUBLIC-POOL.IO (EDUCATIONAL)

import os, sys, time, json, socket, hashlib, struct, threading

# ---------- TERMUX CHECK ----------
if not os.path.exists("/data/data/com.termux"):
    print("[-] Run this inside Termux")
    sys.exit(1)

os.system("pkg update -y >/dev/null 2>&1")
os.system("pkg install -y python >/dev/null 2>&1")

# ---------- USER INPUT ----------
print("\n=== TERMUX BTC PYTHON MINER ===\n")
btc = input("Enter BTC address: ").strip()

if len(btc) < 26:
    print("[-] Invalid BTC address")
    sys.exit(1)

print("\nSelect pool:")
print("1) CKPOOL (public)")
print("2) public-pool.io")

choice = input("Choice [1/2]: ").strip()

if choice == "1":
    POOL = "ckpool.org"
    PORT = 3333
    WORKER = btc + ".termux"
elif choice == "2":
    POOL = "public-pool.io"
    PORT = 21496
    WORKER = btc
else:
    print("[-] Invalid choice")
    sys.exit(1)

PASSWORD = "x"

# ---------- STRATUM ----------
sock = socket.socket()
sock.connect((POOL, PORT))
f = sock.makefile("rwb", buffering=0)

job = {}
extranonce1 = ""
extranonce2_size = 0

hashes = 0
accepted = 0
rejected = 0
start = time.time()

def send(o):
    f.write((json.dumps(o) + "\n").encode())

def recv():
    return json.loads(f.readline().decode())

# Subscribe
send({"id": 1, "method": "mining.subscribe", "params": []})
resp = recv()
extranonce1 = resp["result"][1]
extranonce2_size = resp["result"][2]

# Authorize
send({"id": 2, "method": "mining.authorize", "params": [WORKER, PASSWORD]})
recv()

print(f"[+] Connected to {POOL}:{PORT}")

# ---------- HASH ----------
def dsha(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

# ---------- LISTENER ----------
def listener():
    global job
    while True:
        msg = recv()
        if msg.get("method") == "mining.notify":
            p = msg["params"]
            job = {
                "job_id": p[0],
                "prevhash": p[1],
                "coinb1": p[2],
                "coinb2": p[3],
                "merkle": p[4],
                "version": p[5],
                "nbits": p[6],
                "ntime": p[7],
            }
            print("[*] New job")

# ---------- MINER ----------
def miner():
    global hashes, accepted, rejected
    extranonce2 = 0

    while True:
        if not job:
            time.sleep(0.1)
            continue

        en2 = extranonce2.to_bytes(extranonce2_size, "little").hex()
        coinbase = (
            bytes.fromhex(job["coinb1"])
            + bytes.fromhex(extranonce1 + en2)
            + bytes.fromhex(job["coinb2"])
        )

        mr = dsha(coinbase)
        for h in job["merkle"]:
            mr = dsha(mr + bytes.fromhex(h))

        for nonce in range(0xffffffff):
            header = (
                bytes.fromhex(job["version"])
                + bytes.fromhex(job["prevhash"])[::-1]
                + mr[::-1]
                + bytes.fromhex(job["ntime"])[::-1]
                + bytes.fromhex(job["nbits"])[::-1]
                + struct.pack("<I", nonce)
            )

            hsh = dsha(header)
            hashes += 1

            # Demo-level condition (real difficulty is far higher)
            if hsh[::-1].hex().startswith("000000"):
                send({
                    "id": 4,
                    "method": "mining.submit",
                    "params": [
                        WORKER,
                        job["job_id"],
                        en2,
                        job["ntime"],
                        struct.pack("<I", nonce).hex()
                    ]
                })

                r = recv()
                if r.get("result"):
                    accepted += 1
                    print("[✓] SHARE ACCEPTED")
                else:
                    rejected += 1
                    print("[✗] SHARE REJECTED")

        extranonce2 += 1

# ---------- STATS ----------
def stats():
    while True:
        time.sleep(5)
        t = time.time() - start
        hr = hashes / t if t else 0
        print(f"H/s {hr:.2f} | hashes {hashes} | acc {accepted} | rej {rejected}")

# ---------- START ----------
threading.Thread(target=listener, daemon=True).start()
threading.Thread(target=stats, daemon=True).start()
miner()
