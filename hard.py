#!/usr/bin/env python3
# TERMUX BTC STRATUM MINER — HARDENED NETWORK VERSION
# ckpool.org + public-pool.io
# IPv4/IPv6 + TLS + Port Fallback + Reconnect

import os, sys, time, json, socket, hashlib, struct, threading, ssl

# ---------- TERMUX CHECK ----------
if not os.path.exists("/data/data/com.termux"):
    print("[-] Run inside Termux")
    sys.exit(1)

os.system("pkg update -y >/dev/null 2>&1")
os.system("pkg install -y python >/dev/null 2>&1")

# ---------- USER INPUT ----------
print("\n=== HARDENED TERMUX BTC MINER ===\n")
btc = input("Enter BTC address: ").strip()
if len(btc) < 26:
    print("[-] Invalid BTC address")
    sys.exit(1)

print("\nSelect pool:")
print("1) ckpool.org (public)")
print("2) public-pool.io")

choice = input("Choice [1/2]: ").strip()

if choice == "1":
    POOL = "ckpool.org"
    WORKER = btc + ".termux"
elif choice == "2":
    POOL = "public-pool.io"
    WORKER = btc
else:
    sys.exit(1)

PASSWORD = "x"

# ---------- PORT FALLBACK LIST ----------
PORTS = [
    (3333, False),   # plain stratum
    (443, True),    # TLS stratum (mobile safe)
]

# ---------- GLOBAL STATE ----------
sock = None
f = None
job = {}
extranonce1 = ""
extranonce2_size = 0

hashes = 0
accepted = 0
rejected = 0
start = time.time()

# ---------- CONNECT WITH FALLBACK ----------
def connect():
    global sock, f, extranonce1, extranonce2_size

    for port, use_tls in PORTS:
        try:
            print(f"[*] Trying {POOL}:{port} TLS={use_tls}")

            # IPv4 + IPv6 compatible
            addrinfo = socket.getaddrinfo(POOL, port, socket.AF_UNSPEC, socket.SOCK_STREAM)

            af, socktype, proto, _, sa = addrinfo[0]
            raw = socket.socket(af, socktype, proto)
            raw.settimeout(15)

            if use_tls:
                ctx = ssl.create_default_context()
                sock = ctx.wrap_socket(raw, server_hostname=POOL)
            else:
                sock = raw

            sock.connect(sa)
            f = sock.makefile("rwb", buffering=0)

            # Subscribe
            send({"id": 1, "method": "mining.subscribe", "params": []})
            r = recv()
            extranonce1 = r["result"][1]
            extranonce2_size = r["result"][2]

            # Authorize
            send({"id": 2, "method": "mining.authorize", "params": [WORKER, PASSWORD]})
            recv()

            print(f"[+] Connected to {POOL}:{port}")
            return True

        except Exception as e:
            print(f"[!] Failed {POOL}:{port} -> {e}")
            time.sleep(2)

    return False

# ---------- JSON IO ----------
def send(o):
    f.write((json.dumps(o) + "\n").encode())

def recv():
    return json.loads(f.readline().decode())

# ---------- HASH ----------
def dsha(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

# ---------- LISTENER ----------
def listener():
    global job
    while True:
        try:
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
        except:
            print("[!] Connection lost — reconnecting")
            reconnect()

# ---------- MINER ----------
def miner():
    global hashes, accepted, rejected
    extranonce2 = 0

    while True:
        if not job:
            time.sleep(0.1)
            continue

        try:
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

                hashes += 1
                hsh = dsha(header)

                # demo-level condition
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

        except:
            print("[!] Miner error — reconnecting")
            reconnect()

# ---------- RECONNECT ----------
def reconnect():
    global sock, f, job
    try:
        sock.close()
    except:
        pass
    job = {}
    time.sleep(3)
    while not connect():
        time.sleep(5)

# ---------- STATS ----------
def stats():
    while True:
        time.sleep(5)
        t = time.time() - start
        hr = hashes / t if t else 0
        print(f"H/s {hr:.2f} | hashes {hashes} | acc {accepted} | rej {rejected}")

# ---------- START ----------
while not connect():
    time.sleep(5)

threading.Thread(target=listener, daemon=True).start()
threading.Thread(target=stats, daemon=True).start()
miner()
