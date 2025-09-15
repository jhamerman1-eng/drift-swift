#!/usr/bin/env python3
"""
Production Orchestrator (subprocess model + health/metrics + auto‑restart)

Runs MM (Swift), Hedge, and Trend bots as subprocesses with shared env
variables loaded from a single config. Exposes:
- /health, /ready, /status endpoints
- Prometheus metrics for orchestrator and bots
- Auto‑restart with backoff; MM is required, others optional
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Any

from prometheus_client import start_http_server, Gauge, Counter
from loguru import logger

REPO_ROOT = Path(__file__).resolve().parent.parent


class BotState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class BotSpec:
    role: str
    candidates: List[str]
    required: bool


@dataclass
class BotRuntime:
    spec: BotSpec
    path: Path
    process: Optional[asyncio.subprocess.Process] = None
    state: BotState = BotState.STOPPED
    last_start_ts: float = 0.0
    last_exit_code: Optional[int] = None
    restarts: int = 0
    restart_history: List[float] = field(default_factory=list)


def choose_best_script(candidates: List[str]) -> Optional[Path]:
    for rel in candidates:
        p = REPO_ROOT / rel
        if p.exists():
            return p
    return None


def resolve_specs() -> List[BotSpec]:
    return [
        BotSpec("mm", [
            "run_swift_mm_complete.py",
            "run_swift_mm_complete_fixed.py",
            "run_mm_bot_swift_sidecar_enhanced.py",
            "run_mm_bot_swift_official.py",
        ], required=True),
        BotSpec("hedge", [
            "launch_hedge_beta_real.py",
            "bots/hedge/main.py",
        ], required=False),
        BotSpec("trend", [
            "launch_trend_beta.py",
            "run_trend_bot_beta_fixed.py",
            "run_trend_bot_beta.py",
            "bots/trend/main.py",
        ], required=False),
    ]


class HealthHTTPRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, orchestrator: "Orchestrator", *args, **kwargs):
        self.orchestrator = orchestrator
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == "/health":
            self._json(200 if self.orchestrator.is_healthy() else 503,
                       self.orchestrator.status_snapshot())
        elif self.path == "/ready":
            self._json(200 if self.orchestrator.is_ready() else 503,
                       self.orchestrator.status_snapshot())
        elif self.path == "/status":
            self._json(200, self.orchestrator.status_snapshot())
        else:
            self._json(404, {"error": "not found"})

    def log_message(self, format, *args):
        logger.info(f"[HEALTH] {format % args}")

    def _json(self, code: int, body: Any):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        out = json.dumps(body, indent=2, default=str)
        self.wfile.write(out.encode("utf-8"))


class Orchestrator:
    def __init__(self, metrics_port: int = 9100, health_port: int = 9124):
        self.metrics_port = metrics_port
        self.health_port = health_port
        self.start_time = time.time()
        self.stop_event = asyncio.Event()

        # Load shared env
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from orchestrator.env_loader import build_shared_env
        self.shared_env: Dict[str, str] = build_shared_env("configs/core/drift_client.yaml")
        # Ensure unbuffered child output for real-time logs
        self.shared_env.setdefault("PYTHONUNBUFFERED", "1")
        logger.info("Shared env summary: DRIFT_ENV=%s, RPC=%s, WS=%s, KEYPAIR=%s",
                    self.shared_env.get("DRIFT_ENV"),
                    self.shared_env.get("DRIFT_RPC_URL"),
                    self.shared_env.get("DRIFT_WS_URL"),
                    self.shared_env.get("DRIFT_KEYPAIR_PATH"))

        # Resolve bot scripts
        self.bots: Dict[str, BotRuntime] = {}
        for spec in resolve_specs():
            p = choose_best_script(spec.candidates)
            if not p:
                if spec.required:
                    raise FileNotFoundError(f"Required bot entry not found for {spec.role}")
                logger.warning(f"Optional bot {spec.role} not found; skipping")
                continue
            self.bots[spec.role] = BotRuntime(spec=spec, path=p)

        # Metrics
        self._orch_up = Gauge("orchestrator_up", "1 if orchestrator running")
        self._ready = Gauge("orchestrator_ready", "1 if all required bots running")
        self._bot_up = Gauge("bot_up", "1 if bot process running", ["role"])
        self._bot_restarts = Counter("bot_restarts_total", "bot restart count", ["role"])
        self._bot_exit = Gauge("bot_last_exit_code", "last exit code", ["role"])
        start_http_server(self.metrics_port)
        logger.info(f"Metrics server on :{self.metrics_port}")

        # Health HTTP server (background thread)
        def _handler(*args, **kwargs):
            return HealthHTTPRequestHandler(self, *args, **kwargs)
        self._http = HTTPServer(("0.0.0.0", self.health_port), _handler)
        t = threading.Thread(target=self._http.serve_forever, daemon=True)
        t.start()
        logger.info(f"Health server on :{self.health_port}")

        # Backoff config
        self.backoff_base = 1.0
        self.backoff_cap = 60.0
        self.max_restarts_5min = 5

    # ---- status helpers --------------------------------------------------
    def is_ready(self) -> bool:
        for br in self.bots.values():
            if br.spec.required and br.state != BotState.RUNNING:
                return False
        return True

    def is_healthy(self) -> bool:
        # Healthy if required bots are running
        return self.is_ready()

    def status_snapshot(self) -> Dict[str, Any]:
        now = time.time()
        bots = {}
        for role, br in self.bots.items():
            bots[role] = {
                "path": str(br.path),
                "state": br.state.value,
                "last_start": br.last_start_ts,
                "last_exit_code": br.last_exit_code,
                "restarts": br.restarts,
                "required": br.spec.required,
            }
        return {
            "uptime_seconds": now - self.start_time,
            "ready": self.is_ready(),
            "bots": bots,
        }

    # ---- process management ---------------------------------------------
    async def _stream(self, role: str, stream: asyncio.StreamReader, is_err: bool = False):
        while True:
            line = await stream.readline()
            if not line:
                break
            msg = line.decode(errors="replace").rstrip()
            if is_err:
                logger.error(f"[{role}-err] {msg}")
            else:
                logger.info(f"[{role}] {msg}")
            # Try to capture tx signatures from child logs
            try:
                self._maybe_report_sig(role, msg)
            except Exception:
                pass

    async def _launch(self, br: BotRuntime) -> None:
        env = os.environ.copy()
        env.update(self.shared_env)
        import sys  # Fix: import sys instead of using os.sys
        args = [sys.executable, str(br.path)]
        logger.info(f"Launching {br.spec.role}: {br.path.name}")
        if br.spec.role == "mm":
            await self._await_swift_sidecar_ready()
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(REPO_ROOT),
            env=env,
        )
        br.process = proc
        br.state = BotState.RUNNING
        br.last_start_ts = time.time()
        self._bot_up.labels(role=br.spec.role).set(1)
        if proc.stdout:
            asyncio.create_task(self._stream(br.spec.role, proc.stdout))
        if proc.stderr:
            asyncio.create_task(self._stream(br.spec.role, proc.stderr, True))

    def _too_many_restarts(self, br: BotRuntime) -> bool:
        # keep last 5 minutes
        now = time.time()
        br.restart_history = [t for t in br.restart_history if now - t <= 300]
        return len(br.restart_history) >= self.max_restarts_5min

    async def _watch(self, br: BotRuntime) -> None:
        while not self.stop_event.is_set():
            try:
                if br.process is None or br.process.returncode is not None:
                    # (re)launch
                    if br.process is not None and br.process.returncode is not None:
                        br.last_exit_code = br.process.returncode
                        self._bot_exit.labels(role=br.spec.role).set(br.last_exit_code or 0)
                        self._bot_up.labels(role=br.spec.role).set(0)

                        if self._too_many_restarts(br):
                            logger.error(f"{br.spec.role} exceeded restart limit; required={br.spec.required}")
                            if br.spec.required:
                                logger.error("Shutting down orchestrator due to required bot failing")
                                self.stop_event.set()
                                return
                            else:
                                br.state = BotState.ERROR
                                return

                        # backoff based on restarts
                        delay = min(self.backoff_cap, self.backoff_base * (2 ** br.restarts))
                        if br.restarts > 0:
                            logger.warning(f"Restarting {br.spec.role} in {delay:.1f}s (exit={br.last_exit_code})")
                            await asyncio.sleep(delay)
                        br.restarts += 1
                        br.restart_history.append(time.time())
                        self._bot_restarts.labels(role=br.spec.role).inc()

                    await self._launch(br)

                # wait a bit and poll again
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Watcher error for {br.spec.role}: {e}")
                await asyncio.sleep(2.0)

    async def start(self) -> int:
        # Pre-flight: place a tiny on-chain order per role for visibility on UI
        await self._smoke_trades()

        # Start watchers
        watchers = [asyncio.create_task(self._watch(br)) for br in self.bots.values()]

        # Signals
        def _sig(*_):
            logger.info("Signal received; stopping orchestrator")
            self.stop_event.set()
        for s in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
            if s is not None:
                try:
                    asyncio.get_running_loop().add_signal_handler(s, _sig)
                except NotImplementedError:
                    pass

        # Metrics main loop
        self._orch_up.set(1)
        while not self.stop_event.is_set():
            self._ready.set(1.0 if self.is_ready() else 0.0)
            await asyncio.sleep(2.0)

        # Shutdown: terminate processes
        for br in self.bots.values():
            if br.process and br.process.returncode is None:
                try:
                    br.state = BotState.STOPPING
                    br.process.terminate()
                except ProcessLookupError:
                    pass
        # Give them a moment
        await asyncio.sleep(3.0)
        for br in self.bots.values():
            if br.process and br.process.returncode is None:
                br.process.kill()
        for w in watchers:
            w.cancel()
        self._orch_up.set(0)
        try:
            self._http.shutdown()
        except Exception:
            pass
        return 0 if self.is_ready() else 1


    # ---- helpers ---------------------------------------------------------
    def _report_sig(self, role: str, sig: str, source: str = "child") -> None:
        try:
            path = REPO_ROOT / "tx_signatures.log"
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"{int(time.time())}\t{role}\t{source}\t{sig}\n")
        except Exception:
            pass

    def _maybe_report_sig(self, role: str, line: str) -> None:
        import re
        patterns = [
            r"REAL BLOCKCHAIN ORDER PLACED[:\s]+([1-9A-HJ-NP-Za-km-z]{32,88})",
            r"sig=([1-9A-HJ-NP-Za-km-z]{32,88})",
            r"Signature[:\s]+([1-9A-HJ-NP-Za-km-z]{32,88})",
        ]
        for pat in patterns:
            m = re.search(pat, line)
            if m:
                self._report_sig(role, m.group(1))
                return

    async def _await_swift_sidecar_ready(self) -> None:
        base = self.shared_env.get("SWIFT_SIDECAR_URL")
        if not base:
            return
        import urllib.request
        candidates = ["/health", "/ready", "/v1/health", "/status"]
        for attempt in range(6):
            for path in candidates:
                url = base.rstrip("/") + path
                try:
                    with urllib.request.urlopen(url, timeout=2) as resp:
                        if 200 <= resp.status < 500:
                            logger.info(f"Swift sidecar responsive at {url} (status {resp.status})")
                            return
                except Exception:
                    continue
            wait = min(10, 1 + attempt * 2)
            logger.info(f"Waiting for Swift sidecar at {base} ({wait}s)...")
            await asyncio.sleep(wait)
        logger.warning("Proceeding without confirmed Swift sidecar health")

    async def _smoke_trades(self) -> None:
        """Place one tiny order per role directly via drift client for visibility.

        This ensures at least one on-chain transaction appears on Devnet even if
        Swift sidecar is unavailable. MM continues to run via Swift for normal ops.
        """
        try:
            from libs.drift.client import build_client_from_config, Order
        except Exception as e:
            logger.warning(f"Smoke trade skipped: cannot import drift client: {e}")
            return

        config_path = str(REPO_ROOT / "configs/core/drift_client.yaml")
        roles = [r for r in ("mm", "hedge", "trend") if r in self.bots]
        if not roles:
            return

        try:
            client = await build_client_from_config(config_path)
            await client.initialize()
        except Exception as e:
            logger.warning(f"Smoke trade skipped: failed to init client: {e}")
            return

        try:
            ob = await client.get_orderbook(0)
            bids = ob.get("bids", []) if isinstance(ob, dict) else []
            asks = ob.get("asks", []) if isinstance(ob, dict) else []
            if not bids or not asks:
                logger.warning("Smoke trade: empty orderbook; using synthetic mid=100.0")
                mid = 100.0
                best_bid = 99.9
                best_ask = 100.1
            else:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                mid = (best_bid + best_ask) / 2.0

            for i, role in enumerate(roles):
                # Alternate sides for variety
                side = "buy" if i % 2 == 0 else "sell"
                # Place just inside the book to be maker
                price = best_bid * 0.999 if side == "buy" else best_ask * 1.001
                size_usd = 2.0
                try:
                    sig = await client.place_order(Order(side=side, price=price, size_usd=size_usd))
                    logger.info(f"[smoke] {role} order posted: side={side} px={price:.4f} size_usd={size_usd} sig={sig}")
                except Exception as e:
                    logger.warning(f"[smoke] {role} failed to post order: {e}")
                await asyncio.sleep(0.5)
        finally:
            try:
                if hasattr(client, "close"):
                    await client.close()
            except Exception:
                pass


async def main():
    p = argparse.ArgumentParser(description="Drift Orchestrator")
    p.add_argument("--metrics-port", type=int, default=int(os.getenv("METRICS_PORT", 9100)))
    p.add_argument("--health-port", type=int, default=int(os.getenv("HEALTH_PORT", 9124)))
    args = p.parse_args()

    orch = Orchestrator(metrics_port=args.metrics_port, health_port=args.health_port)
    code = await orch.start()
    raise SystemExit(code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except SystemExit as e:
        raise
    except Exception as e:
        logger.error(f"Fatal orchestrator error: {e}")
        raise
