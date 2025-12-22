import socket
import json
import hashlib
import struct
import time
import threading
import os
import re
import sys

POOL_HOST = "public-pool.io"
POOL_PORT = 21496
PASSWORD = "x"

hashes_done = 0
shares_found = 0
difficulty = 1.0
start_time = time.time()
current_job = None
extranonce1 = None
running = True

# ---------- Utils ----------

def clear():
    os.system("clear")

def sha256d(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

def le(hexstr):
    return bytes.fromhex(hexstr)[::-1]

def valid_btc(addr):
    return re.match(r"^(1|3|bc1q)[a-zA-HJ-NP-Z0-9]{25,62}$", addr)

def recv_line(sock):
    buf = b""
    while not buf.endswith(b"\n"):
        buf += sock.recv(1)
    return json.loads(buf.decode())

def send(sock, obj):
    sock.sendall((json.dumps(obj) + "\n").encode())

# ---------- Hashrate Display ----------

def stats():
    global hashes_done
    while running:
        time.sleep(2)
        elapsed = time.time() - start_time
        rate = hashes_done / elapsed if elapsed else 0
        clear()
        print("=== PYTHON STRATUM BTC MINER ===")
        print(f"Hashrate : {rate:.2f} H/s")
        print(f"Hashes   : {hashes_done}")
        print(f"Shares   : {shares_found}")
        print(f"Diff     : {difficulty}")
        print("Ctrl+C to stop")

# ---------- Miner ----------

def mine():
    global hashes_done, shares_found

    while running:
        if not current_job:
            time.sleep(0.1)
            continue

        (job_id, prevhash, coinb1, coinb2,
         merkle_branch, version, nbits, ntime, clean) = current_job

        extranonce2 = "00000000"
        coinbase = bytes.fromhex(coinb1 + extranonce1 + extranonce2 + coinb2)
        coinbase_hash = sha256d(coinbase)

        merkle = coinbase_hash
        for m in merkle_branch:
            merkle = sha256d(merkle + bytes.fromhex(m))

        header_base = (
            le(version) +
            le(prevhash) +
            merkle[::-1] +
            le(ntime) +
            le(nbits)
        )

        nonce = 0
        while running:
            header = header_base + struct.pack("<I", nonce)
            sha = sha256d(header)
            hashes_done += 1
            nonce += 1

# ---------- Main ----------

def main():
    global extranonce1, current_job, difficulty

    clear()
    print("=== PYTHON BTC STRATUM SETUP ===\n")
    btc = input("[?] Enter BTC payout address: ").strip()

    if not valid_btc(btc):
        print("\n[!] Invalid BTC address")
        sys.exit(1)

    sock = socket.create_connection((POOL_HOST, POOL_PORT))

    # Subscribe
    send(sock, {"id": 1, "method": "mining.subscribe", "params": []})
    sub = recv_line(sock)
    extranonce1 = sub["result"][1]

    # Authorize (BTC address IS the username)
    send(sock, {
        "id": 2,
        "method": "mining.authorize",
        "params": [btc, PASSWORD]
    })

    # Start threads
    threading.Thread(target=stats, daemon=True).start()
    threading.Thread(target=mine, daemon=True).start()

    # Message loop
    while True:
        msg = recv_line(sock)

        if msg.get("method") == "mining.set_difficulty":
            difficulty = msg["params"][0]

        elif msg.get("method") == "mining.notify":
            current_job = msg["params"]

# ---------- Run ----------

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        running = False
        print("\n[!] Miner stopped")
