#!/data/data/com.termux/files/usr/bin/python

import os
import sys
import json
import base64
import getpass
import subprocess
from secrets import token_bytes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HOME = os.path.expanduser("~")
VAULT_FILE = os.path.join(HOME, "FULL_HOME_VAULT.enc")

EXCLUDE_DIRS = {
    "/data/data/com.termux/files/usr",
    "/system",
    "/proc",
    "/dev"
}

def run(cmd):
    subprocess.check_call(cmd)

def ensure_crypto():
    try:
        import cryptography  # noqa
    except ImportError:
        print("Installing required package...")
        run(["pkg", "install", "python-cryptography", "-y"])

def derive_key(password, salt):
    return Scrypt(
        salt=salt,
        length=32,
        n=2**15,
        r=8,
        p=1
    ).derive(password)

def should_exclude(path):
    for d in EXCLUDE_DIRS:
        if path.startswith(d):
            return True
    return False

def collect_files():
    files = []
    for root, _, filenames in os.walk(HOME):
        if should_exclude(root):
            continue
        for f in filenames:
            p = os.path.join(root, f)
            if p == VAULT_FILE:
                continue
            files.append(p)
    return files

def encrypt_all():
    print("⚠️ WARNING ⚠️")
    print("This will encrypt ALL your Termux home files.")
    print("A single vault file will remain.")
    print("You MUST remember the password.")
    confirm = input("Type YES to continue: ")

    if confirm != "YES":
        print("Cancelled.")
        return

    password = getpass.getpass("Create vault password: ").encode()
    salt = token_bytes(16)
    key = derive_key(password, salt)
    aes = AESGCM(key)
    nonce = token_bytes(12)

    data = {}
    files = collect_files()

    print(f"Encrypting {len(files)} files...")

    for p in files:
        try:
            with open(p, "rb") as f:
                data[p] = base64.b64encode(f.read()).decode()
        except Exception as e:
            print(f"Skipping {p}: {e}")

    ciphertext = aes.encrypt(nonce, json.dumps(data).encode(), None)

    with open(VAULT_FILE, "wb") as f:
        f.write(salt + nonce + ciphertext)

    for p in files:
        try:
            os.remove(p)
        except:
            pass

    print("✅ ALL FILES ENCRYPTED")
    print("Vault:", VAULT_FILE)

def decrypt_all():
    password = getpass.getpass("Vault password: ").encode()

    with open(VAULT_FILE, "rb") as f:
        blob = f.read()

    salt, nonce, ct = blob[:16], blob[16:28], blob[28:]
    key = derive_key(password, salt)
    aes = AESGCM(key)

    data = json.loads(aes.decrypt(nonce, ct, None))

    for p, content in data.items():
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(base64.b64decode(content))

    print("🔓 All files restored")

def main():
    ensure_crypto()
    print("1) Encrypt ALL files in Termux home")
    print("2) Decrypt vault")
    choice = input("> ")

    if choice == "1":
        encrypt_all()
    elif choice == "2":
        decrypt_all()
    else:
        print("Invalid option")

if __name__ == "__main__":
    main()
