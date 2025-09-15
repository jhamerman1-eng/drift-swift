#!/usr/bin/env python3
"""
Master bot orchestrator that launches three bots concurrently as isolated
subprocesses and streams their logs:
- MM: run_swift_mm_complete.py (or best available fallback)
- Hedge: launch_hedge_beta_real.py (or bots/hedge/main.py)
- Trend: launch_trend_beta.py (or best available fallback)

Primary goals:
- Be robust and cross‑platform (Windows friendly)
- Avoid type errors and odd console encodings
- Gracefully handle shutdown and surface per‑bot exit codes
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import logging

# Setup centralized logging with comprehensive fallback
# AUDIT_COMPLIANT: Uses centralized logging with file and console handlers
try:
    from libs.logging_config import setup_critical_logging
    logger = setup_critical_logging("orchestrator")  # Includes RotatingFileHandler + StreamHandler
except ImportError:
    # Fallback to basic logging with file output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/orchestrator_fallback.log", encoding="utf-8")
        ]
    )
    logger = logging.getLogger("orchestrator")
except Exception as e:
    # Ultimate fallback
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    logger = logging.getLogger("orchestrator")
    logger.warning(f"Logging setup failed, using basic config: {e}")


# ---- Bot discovery ---------------------------------------------------------

REPO_ROOT = Path(__file__).parent


def choose_best_script(candidates: List[str]) -> Optional[Path]:
    """Return the first existing script from candidates (repo‑relative)."""
    for rel in candidates:
        p = REPO_ROOT / rel
        if p.exists():
            return p
    return None


def resolve_entries() -> Dict[str, Path]:
    """Pick the best entry for each bot role based on repository contents."""
    mapping: Dict[str, List[str]] = {
        # Market Maker
        "mm": [
            "run_swift_mm_complete.py",
            "run_swift_mm_complete_fixed.py",
            "run_mm_bot_swift_sidecar_enhanced.py",
            "run_mm_bot_swift_official.py",
        ],
        # Hedge
        "hedge": [
            "launch_hedge_beta_real.py",
            "bots/hedge/main.py",
        ],
        # Trend
        "trend": [
            "launch_trend_beta.py",
            "run_trend_bot_beta_fixed.py",
            "run_trend_bot_beta.py",
            "bots/trend/main.py",
        ],
    }

    out: Dict[str, Path] = {}
    for role, candidates in mapping.items():
        p = choose_best_script(candidates)
        if p is None:
            raise FileNotFoundError(f"No entry script found for role '{role}' (checked: {candidates})")
        out[role] = p
    return out


# ---- Subprocess runner -----------------------------------------------------

@dataclass
class BotProc:
    role: str
    path: Path
    process: asyncio.subprocess.Process


async def _stream(prefix: str, stream: asyncio.StreamReader) -> None:
    """Stream a subprocess pipe to our logger with a prefix."""
    while True:
        line = await stream.readline()
        if not line:
            break
        try:
            msg = line.decode(errors="replace").rstrip()
        except Exception:
            msg = str(line).rstrip()
        logger.info("[%s] %s", prefix, msg)


async def launch_bot(role: str, path: Path, extra_args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None) -> BotProc:
    """Launch a bot script as a subprocess and start stdout/stderr streamers."""
    args = [sys.executable, str(path)] + (extra_args or [])
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)

    logger.info("Launching %s: %s", role, path.name)
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=proc_env,
        cwd=str(REPO_ROOT),
    )

    # Stream logs
    assert proc.stdout and proc.stderr
    asyncio.create_task(_stream(role, proc.stdout))
    asyncio.create_task(_stream(role + "-err", proc.stderr))

    return BotProc(role=role, path=path, process=proc)


async def terminate_bot(bot: BotProc, timeout: float = 10.0) -> int:
    """Terminate a bot gracefully; return exit code."""
    if bot.process.returncode is not None:
        return bot.process.returncode
    try:
        bot.process.terminate()
    except ProcessLookupError:
        return bot.process.returncode or 0
    try:
        return await asyncio.wait_for(bot.process.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        bot.process.kill()
        return await bot.process.wait()


# ---- Orchestrator main -----------------------------------------------------

async def main() -> int:
    entries = resolve_entries()

    # Centralized env from unified config
    try:
        from orchestrator.env_loader import build_shared_env
        shared_env = build_shared_env("configs/core/drift_client.yaml")
    except Exception:
        shared_env = {
            "DRIFT_ENV": os.getenv("DRIFT_ENV", "devnet"),
            "USE_MOCK": os.getenv("USE_MOCK", "false"),
        }

    # Launch bots
    bots: List[BotProc] = []
    try:
        bots.append(await launch_bot("mm", entries["mm"], env=shared_env))
        bots.append(await launch_bot("hedge", entries["hedge"], env=shared_env))
        bots.append(await launch_bot("trend", entries["trend"], env=shared_env))

        logger.info("All bots launched. Press Ctrl+C to stop.")

        # Handle signals for graceful shutdown
        stop_event = asyncio.Event()

        def _signal_handler(*_):
            logger.info("Shutdown signal received")
            stop_event.set()

        for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
            if sig is not None:
                try:
                    asyncio.get_running_loop().add_signal_handler(sig, _signal_handler)
                except NotImplementedError:
                    pass

        # Wait until any process exits or we get a signal
        async def any_exit(proc: asyncio.subprocess.Process) -> Tuple[str, int]:
            code = await proc.wait()
            return ("exit", code)

        wait_tasks = [asyncio.create_task(any_exit(b.process)) for b in bots]
        done, pending = await asyncio.wait(
            wait_tasks + [asyncio.create_task(stop_event.wait())],
            return_when="FIRST_COMPLETED",
        )

        # If a stop was requested, fall through to shutdown
        # If a bot exited, log and begin shutdown
        for d in done:
            if d is not None and not d.cancelled():
                try:
                    result = d.result()
                    if isinstance(result, tuple) and result and result[0] == "exit":
                        logger.warning("A bot exited with code %s; shutting down", result[1])
                except Exception:
                    pass

    finally:
        # Terminate all
        exit_codes: Dict[str, int] = {}
        for b in bots:
            code = await terminate_bot(b)
            exit_codes[b.role] = code
            logger.info("%s exited with code %s", b.role, code)

        # Choose overall exit code: non‑zero if any failed
        return 0 if all(c == 0 for c in exit_codes.values()) else 1


if __name__ == "__main__":
    try:
        code = asyncio.run(main())
        sys.exit(code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
