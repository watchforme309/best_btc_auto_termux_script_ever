#!/usr/bin/env python3
import os,csv,hashlib,subprocess,platform,stat
from datetime import datetime

CASE="CASE_"+datetime.utcnow().strftime("%Y%m%d_%H%M%S")
BASE=next(p for p in[
    os.path.expanduser("~/storage/downloads"),
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~")] if os.path.exists(p))

ROOT=os.path.join(BASE,CASE)
EV=os.path.join(ROOT,"evidence")
os.makedirs(EV,exist_ok=True)

INDEX=os.path.join(ROOT,"evidence_index.csv")
CHAIN=os.path.join(ROOT,"chain_of_custody.txt")

def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(8192),b""): h.update(b)
    return h.hexdigest()

def save(name,data):
    name=name.replace("/","_")
    p=os.path.join(EV,name+".txt")
    open(p,"w",errors="ignore").write(data)
    return p

def log(action):
    open(CHAIN,"a").write(
        f"{datetime.utcnow().isoformat()} UTC {action}\n")

def add(name,path,desc):
    csv.writer(open(INDEX,"a",newline="")).writerow(
        [name,path,sha(path),
         datetime.utcnow().isoformat(),desc])

csv.writer(open(INDEX,"w",newline="")).writerow(
    ["artifact","path","sha256","utc","description"])
log("Case opened")

# SYSTEM ID
sysinfo=f"""
Hostname: {platform.node()}
OS: {platform.platform()}
Python: {platform.python_version()}
UTC: {datetime.utcnow().isoformat()}
"""
p=save("system_identification",sysinfo)
add("system_identification",p,"Device identification")
log("System identified")

# USERS
try:
    p=save("user_accounts",open("/etc/passwd").read())
    add("user_accounts",p,"Local accounts")
except: pass

# LOGCAT (Android)
try:
    p=save("android_logcat",
        subprocess.check_output(
            ["logcat","-d","-v","threadtime"],
            stderr=subprocess.DEVNULL
        ).decode(errors="ignore"))
    add("android_logcat",p,"Android system logs")
except: pass

# AUTH / ACCESS LOGS
LOGS=["/var/log","/data/data/com.termux/files/usr/var/log"]
for d in LOGS:
    if not os.path.exists(d): continue
    for r,_,f in os.walk(d):
        for n in f:
            if any(x in n.lower() for x in ["auth","secure","log"]):
                try:
                    src=os.path.join(r,n)
                    p=save(src,open(src,errors="ignore").read())
                    add(src,p,"Authentication / access log")
                except: pass

# PERSISTENCE / BACKDOORS
ARTS=["~/.ssh/authorized_keys","~/.bashrc",
      "~/.profile","/etc/crontab"]
for a in ARTS:
    a=os.path.expanduser(a)
    if os.path.isfile(a):
        try:
            p=save(a,open(a,errors="ignore").read())
            add(a,p,"Persistence artifact")
        except: pass

# FILE TIMELINE
lines=[]
for d in LOGS:
    if not os.path.exists(d): continue
    for r,_,f in os.walk(d):
        for n in f:
            try:
                s=os.stat(os.path.join(r,n))
                lines.append(
                    f"{r}/{n}|{s.st_size}|"
                    f"{stat.filemode(s.st_mode)}|"
                    f"{datetime.fromtimestamp(s.st_mtime)}")
            except: pass

p=save("file_timeline","\n".join(lines))
add("file_timeline",p,"Filesystem timeline")

# CASE SUMMARY
summary=f"""
FORENSIC EVIDENCE COLLECTION
Case: {CASE}
UTC: {datetime.utcnow().isoformat()}

Method:
- Read-only acquisition
- Individual artifacts
- SHA-256 integrity
- Chain of custody maintained

Purpose:
- Support investigation of unauthorized access
"""
p=save("README",summary)
add("README",p,"Case summary")

log("Case closed")
print("EVIDENCE READY:",ROOT)
