import socket
import json
import time

# ========== USER INPUT ==========
btc_address = input("Enter your Bitcoin payout address> ")
worker_name = f"{btc_address}.anonminer" 

print(f"[+] Worker name set to: {worker_name}")
print("[+] Starting Stratum connection to Public Pool...\n")

# ========== STRATUM CONFIG ==========
POOL_HOST = "public-pool.io"
POOL_PORT = 21496

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((POOL_HOST, POOL_PORT))

    def send(msg):
        sock.sendall((json.dumps(msg) + "\n").encode())

    # ========== 1. SUBSCRIBE ==========
    send({"id": 1, "method": "mining.subscribe", "params": []})
    sub_response = sock.recv(1024).decode()
    print(f"[+] Subscribe Response: {sub_response.strip()}")

    # ========== 2. AUTHORIZE ==========
    send({"id": 2, "method": "mining.authorize", "params": [worker_name, "x"]})
    auth_response = sock.recv(1024).decode()
    print(f"[+] Auth Response: {auth_response.strip()}")

    # Corrected check for the "true" result you received
    if '"result":true' in auth_response.replace(" ", ""):
        print("\n[*] SUCCESS! Authorized. Now listening for incoming jobs...\n")
        
        # ========== 3. LISTEN LOOP ==========
        while True:
            try:
                data = sock.recv(4096).decode()
                if data:
                    # Clean and split multiple messages if they arrive together
                    for line in data.strip().split('\n'):
                        if "mining.notify" in line:
                            print(f"NEW JOB: {line}")
                        else:
                            print(f"POOL MSG: {line}")
                time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n[!] Miner stopped")
                break
    else:
        print("[!] Authorization failed. The pool rejected the address.")

except Exception as e:
    print(f"[!] Error: {e}")
finally:
    sock.close()
