#!/usr/bin/env bash
set -e

clear
echo "==========================================="
echo "  Bitcoin CPU Lottery Miner (Linux)"
echo "  CKPool SOLO + Public Pool Auto-Fallback"
echo "==========================================="
echo

# -------- Ask for BTC Address ----------
read -rp "Enter your Bitcoin address: " BTC_ADDR

if [[ ! "$BTC_ADDR" =~ ^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}$ ]]; then
  echo "❌ Invalid BTC address"
  exit 1
fi

WORKER="lotto-$(hostname)"
THREADS=$(nproc)
LOGDIR="$HOME/btc_lottery_logs"
mkdir -p "$LOGDIR"

echo
echo "Using $THREADS CPU threads"
echo "Logs in $LOGDIR"
sleep 2

# -------- Install dependencies ----------
echo "📦 Installing dependencies..."
sudo apt update
sudo apt install -y \
  git build-essential automake autoconf libcurl4-openssl-dev \
  libjansson-dev libssl-dev libgmp-dev

# -------- Install cpuminer ----------
if ! command -v cpuminer >/dev/null 2>&1; then
  echo "⚙️ Building cpuminer..."
  git clone https://github.com/tpruvot/cpuminer-multi.git
  cd cpuminer-multi
  ./build.sh
  sudo make install
  cd ..
fi

echo "✅ cpuminer installed"
sleep 1

# -------- Pool definitions ----------
CKPOOL_PRIMARY="stratum+tcp://solo.ckpool.org:3333"
CKPOOL_TLS="stratum+ssl://solo.ckpool.org:443"
PUBLIC_POOL="stratum+tcp://public-pool.io:21496"

# -------- Mining loop ----------
while true; do
  echo "🎯 SOLO LOTTERY MINING (CKPOOL 3333)"
  cpuminer \
    -a sha256d \
    -o $CKPOOL_PRIMARY \
    -u $BTC_ADDR.$WORKER \
    -p x \
    -t $THREADS \
    --retry-pause=5 \
    --timeout=120 \
    | tee "$LOGDIR/ckpool.log" || true

  echo "🔐 CKPOOL TLS FALLBACK (443)"
  cpuminer \
    -a sha256d \
    -o $CKPOOL_TLS \
    -u $BTC_ADDR.$WORKER \
    -p x \
    -t $THREADS \
    --retry-pause=5 \
    --timeout=120 \
    | tee "$LOGDIR/ckpool_tls.log" || true

  echo "🌍 PUBLIC POOL MODE (public-pool.io)"
  cpuminer \
    -a sha256d \
    -o $PUBLIC_POOL \
    -u $BTC_ADDR.$WORKER \
    -p x \
    -t $THREADS \
    --retry-pause=5 \
    --timeout=120 \
    | tee "$LOGDIR/public_pool.log" || true

  echo "🔄 Restarting lottery cycle..."
  sleep 10
done
