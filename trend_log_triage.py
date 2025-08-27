
#!/usr/bin/env python3
"""
Trend Log Triage Utility
Reads a Trend bot log file, detects common error signatures, and prints actionable fixes.

Usage:
  python trend_log_triage.py /path/to/trend.log [--since '2025-08-27 00:00']
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

PATTERNS = [  # (name, regex, why_it_happens, fix)
    ("InsufficientWarmup", r"(not enough|insufficient) data|warmup|min bars|window size", 
     "Indicators (MACD/ATR/ADX/RBC) need a minimum bar window before producing signals.",
     "Gate entries until MIN_BARS are loaded. Configure warmup: trend.min_bars >= max(MACD.long, ATR.period*2, ADX.period*2)."),
    ("NaNValues", r"NaN|nan encountered|invalid value encountered", 
     "NaN from indicators (divide-by-zero, empty arrays, misaligned OHLCV).", 
     "Sanitize inputs; use np.nan_to_num; enforce eps in denominators; drop leading NaNs before signal logic."),
    ("ZeroDivision", r"ZeroDivisionError", 
     "Division by zero in indicator or risk sizing.", 
     "Clamp denominators with eps (e.g., max(abs(x), 1e-9))."),
    ("IndexBounds", r"IndexError: (index|list index) out of range|too many indices", 
     "Signal references past bars without checking length.", 
     "Use safe slicing and len checks; prefer df.iloc[-1] guarded by len>=1."),
    ("NoneAttr", r"AttributeError: 'NoneType' object has no attribute", 
     "Upstream returned None (market data, client, order result).", 
     "Assert not None; short-circuit with retries; add connectivity/health checks."),
    ("PandasShape", r"ValueError: (Shapes|operands) could not be broadcast|cannot reindex|length mismatch", 
     "Mismatched series lengths (e.g., OHLCV vs indicator series).", 
     "Align indexes; use .tail(n) after computing indicators; reindex/ffill where appropriate."),
    ("LinAlg", r"numpy\.linalg\.(LinAlgError|SVD did not converge|Singular matrix)", 
     "Unstable matrix ops in filters/regressions.", 
     "Regularize (ridge), scale inputs, or reduce window size; catch and skip that tick."),
    ("Cancelled", r"asyncio\.(CancelledError|TimeoutError)|concurrent\.futures\.TimeoutError", 
     "Task cancelled or timed out (RPC, WS, or driver).", 
     "Wrap awaits with timeouts and retries; backoff & resume; mark bot state=DEGRADED."),
    ("OrderRejected", r"(order|submit).*(rejected|failed|400|403|429|5\d{2})", 
     "Venue rejected order (throttle, auth, bad params).", 
     "Throttle; validate params; ensure auth/nonce; for 429 use jitter/backoff."),
    ("ModuleMissing", r"ModuleNotFoundError|ImportError: No module named", 
     "Missing dependency (ta-lib, pandas-ta, driftpy, anchorpy).", 
     "Install correct deps; pin versions; avoid optional libs in prod path."),
    ("WSDisconnect", r"(websocket|WS).*(disconnect|closed|going away|code=1006)", 
     "Market data feed dropped.", 
     "Auto-reconnect with jitter, resubscribe, verify gap-fill before trading."),
    ("ConfigKey", r"KeyError: ['\"]?[A-Za-z0-9_\.]+['\"]?", 
     "Missing config key.", 
     "Validate configs on boot; provide defaults; fail-fast with clear message."),
]

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile", help="Path to Trend bot log file") 
    ap.add_argument("--since", help="Only analyze lines at/after this timestamp (YYYY-MM-DD HH:MM)")
    ap.add_argument("--context", type=int, default=2, help="Lines of context around matches (default 2)" )
    return ap.parse_args()

def line_has_timestamp(line):
    # Accepts '2025-08-27 03:04:57,399 - ...' or ISO-like
    return re.search(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}", line) is not None

def ts_ok(line, since):
    if not since:
        return True
    m = re.search(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})", line)
    if not m:
        return False
    ts = datetime.strptime(" ".join(m.groups()), "%Y-%m-%d %H:%M")
    return ts >= since

def scan(lines, since_dt, ctx):
    findings = []
    for i, line in enumerate(lines):
        if since_dt and not ts_ok(line, since_dt):
            continue
        for name, rx, why, fix in PATTERNS:
            if re.search(rx, line, flags=re.IGNORECASE):
                start = max(0, i-ctx); end = min(len(lines), i+ctx+1)
                snippet = "".join(lines[start:end])
                findings.append({"pattern": name, "line": i+1, "snippet": snippet, "why": why, "fix": fix})
    return findings

def main():
    args = parse_args()
    p = Path(args.logfile)
    if not p.exists():
        print(f"❌ File not found: {p}")
        return 2
    lines = p.read_text(errors="ignore").splitlines(keepends=True)
    since_dt = None
    if args.since:
        try:
            since_dt = datetime.strptime(args.since, "%Y-%m-%d %H:%M")
        except Exception:
            print("⚠️  --since format invalid; expected YYYY-MM-DD HH:MM. Ignoring.")
    findings = scan(lines, since_dt, args.context)
    if not findings:
        print("✅ No known error signatures found. If you're still seeing failures, share the last 200 lines around the incident.")
        return 0
    print("\n=== Trend Log Triage Report ===\n")
    by_pattern = {}
    for f in findings:
        by_pattern.setdefault(f["pattern"], []).append(f)
    for pattern, items in by_pattern.items():
        print(f"• {pattern} — {len(items)} hit(s)")
    print("\nDetailed Findings (first 8 shown per pattern):\n")
    for pattern, items in by_pattern.items():
        for f in items[:8]:
            print(f"--- {pattern} @ line {f['line']} ---")
            print(f['snippet'])
            print("Why:", f['why'])
            print("Fix:", f['fix'])
            print()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
