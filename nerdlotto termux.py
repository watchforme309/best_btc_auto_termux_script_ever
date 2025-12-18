#!/usr/bin/env python3
import os
import sys
import json
import time
import struct
import random
import hashlib
import asyncio
import subprocess

# -----------------------------
# AUTO-BOOTSTRAP (TERMUX)
# -----------------------------
def bootstrap():
    if os.environ.get("TERMUX_VERSION"):
        try:
            import asyncio  # noqa
        except ImportError:
            print("[*] Installing Python for Termux...")
            subprocess.run(["pkg", "install", "-y", "python"], check=False)

bootstrap()

# -----------------------------
# CONFIG
# -----------------------------
BTC_ADDRESS = "32QLDQf4UNqCNJTKYBNXK2jzSnSctWfwc4"
WORKER = "termux-lotto"

POOLS = [
    ("public-pool.io", 21496),
    ("pool.nerdminers.org", 3333),
    ("pool.pyblock.xyz", 3333),
    ("pool.sethforprivacy.com", 3333),
    ("pool.stompi.de", 3333),
    ("pool.solomining.de", 3333),
]

# -----------------------------
# HASHING
# -----------------------------
def sha256d(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

# -----------------------------
# STRATUM MINER
# -----------------------------
async def mine(pool, port):
    while True:
        try:
            reader, writer = await asyncio.open_connection(pool, port)
            print(f"[+] Connected to {pool}:{port}")

            def send(msg):
                writer.write((json.dumps(msg) + "\n").encode())

            # Subscribe
            send({"id": 1, "method": "mining.subscribe", "params": []})
            await reader.readline()

            # Authorize
            send({
                "id": 2,
                "method": "mining.authorize",
                "params": [BTC_ADDRESS, "x"]
            })
            await reader.readline()

            extranonce = os.urandom(4)

            while True:
                line = await reader.readline()
                if not line:
                    raise ConnectionError("Disconnected")

                msg = json.loads(line.decode(errors="ignore"))

                if msg.get("method") != "mining.notify":
                    continue

                params = msg["params"]
                job_id = params[0]
                prevhash = bytes.fromhex(params[1])
                coinb1 = bytes.fromhex(params[2])
                coinb2 = bytes.fromhex(params[3])
                merkle = [bytes.fromhex(x) for x in params[4]]
                version = bytes.fromhex(params[5])
                nbits = bytes.fromhex(params[6])
                ntime = bytes.fromhex(params[7])

                coinbase = coinb1 + extranonce + coinb2
                coinbase_hash = sha256d(coinbase)

                merkle_root = coinbase_hash
                for b in merkle:
                    merkle_root = sha256d(merkle_root + b)

                header_prefix = (
                    version +
                    prevhash[::-1] +
                    merkle_root[::-1] +
                    ntime +
                    nbits
                )

                for _ in range(3000):  # tiny lottery loop
                    nonce = struct.pack("<I", random.getrandbits(32))
                    header = header_prefix + nonce
                    h = sha256d(header)

                    # VERY LOW SHARE TARGET (nerdminer style)
                    if h[-2:] == b"\x00\x00":
                        print(f"[🎉] Share found on {pool}")
                        send({
                            "id": random.randint(10, 99999),
                            "method": "mining.submit",
                            "params": [
                                BTC_ADDRESS,
                                job_id,
                                extranonce.hex(),
                                nonce.hex(),
                                ntime.hex()
                            ]
                        })

        except Exception as e:
            print(f"[!] {pool} error: {e}")
            await asyncio.sleep(5)

# -----------------------------
# MAIN
# -----------------------------
async def main():
    print("===================================")
    print(" NerdMiner-style Lottery Miner")
    print(" BTC:", BTC_ADDRESS)
    print(" Pools:", len(POOLS))
    print("===================================")

    tasks = [mine(p, port) for p, port in POOLS]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Stopped")
