#!/usr/bin/env python3
"""
JIT Orchestrator Main Entry Point
Integrates with the new JIT v3 Engine
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any

from prometheus_client import Counter, Histogram, start_http_server

from bots.jit.engine import JITEngine
from libs.drift.mock_drivers import build_mock_client_from_config
from libs.drift.real_client_adapter import build_real_client_adapter
from libs.config.config_loader import load_yaml_with_env

# Metrics
BOT_ITER = Counter("bot_iterations_total", "Bot iterations", ["name"])
TICK_TO_QUOTE = Histogram("tick_to_quote_seconds", "Time from tick to quote", ["name"])

logger = logging.getLogger("orchestrator.main")

async def run_jit_bot(client, cfg: Dict[str, Any], name: str = "jit"):
    """
    Main JIT bot orchestration loop with new JIT v3 Engine
    """
    logger.info(f"Starting JIT bot '{name}' with v3 engine")
    
    # Initialize JIT Engine
    market = cfg.get("market", "SOL-PERP")
    jit_config = cfg.get("jit", {})
    engine = JITEngine(client, jit_config, market)
    
    last_quote_price = None
    i = 0
    
    while True:
        try:
            # Execute one engine step
            decision = await engine.step()
            
            if decision and decision.should_quote:
                # Convert spread_bps to absolute spread
                abs_spread = (decision.spread_bps / 10000.0) * decision.ref_price
                
                # Execute quotes via client (supports size-aware quoting if implemented)
                with TICK_TO_QUOTE.labels(name).time():
                    await client.quote_two_sided(
                        decision.ref_price,
                        abs_spread,
                        decision.size_multiplier,
                        True,  # do_cr since CR gate already passed
                        bid_size=decision.bid_size,
                        ask_size=decision.ask_size
                    )
                
                last_quote_price = decision.ref_price
                BOT_ITER.labels(name).inc()
                i += 1
                
                logger.info(f"JIT iteration {i}: ref=${decision.ref_price:.4f}, "
                          f"spread={decision.spread_bps:.1f}bps, "
                          f"regime={decision.regime.value}, "
                          f"toxicity={decision.toxicity_score:.3f}")
            else:
                logger.debug(f"JIT step skipped: {decision.reason if decision else 'no decision'}")
            
            await asyncio.sleep(cfg.get("loop_secs", 0.9))
            
        except Exception as e:
            logger.exception(f"JIT Bot error: {e}")
            await asyncio.sleep(2.0)

def _setup_signals(loop, stop_evt: asyncio.Event):
    """Setup signal handlers for graceful shutdown"""
    def _sig(name):
        def _inner(): 
            logger.info(f"Received {name}, shutting down...")
            stop_evt.set()
        return _inner
    try: 
        loop.add_signal_handler(signal.SIGINT, _sig("SIGINT"))
        loop.add_signal_handler(signal.SIGTERM, _sig("SIGTERM"))
    except NotImplementedError:
        # Windows doesn't support signal handlers in event loops
        pass

async def main():
    """Main orchestrator entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JIT Orchestrator v3.0")
    parser.add_argument("--client-config", required=True, help="Path to client config YAML")
    parser.add_argument("--metrics-port", type=int, default=9109, help="Prometheus metrics port")
    parser.add_argument("--name", default="jit", help="Bot instance name")
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    )
    
    # Start metrics server
    try:
        start_http_server(args.metrics_port)
        logger.info(f"Started Prometheus metrics server on port {args.metrics_port}")
    except Exception as e:
        logger.warning(f"Failed to start metrics server: {e}")
    
    # Load configuration
    cfg = load_yaml_with_env(args.client_config)
    logger.info(f"Loaded config from {args.client_config}")
    
    # Build client based on configuration
    driver = cfg.get("driver", "mock")
    if driver == "real_drift":
        client = await build_real_client_adapter(args.client_config)
        logger.info(f"Built real DriftPy client adapter: {type(client).__name__}")
    else:
        client = await build_mock_client_from_config(args.client_config)
        logger.info(f"Built mock client: {type(client).__name__}")
    
    # Setup graceful shutdown
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()
    _setup_signals(loop, stop_event)
    
    # Run JIT bot
    jit_task = asyncio.create_task(run_jit_bot(client, cfg, args.name))
    
    try:
        # Wait for shutdown signal
        await stop_event.wait()
        logger.info("Shutdown signal received, stopping JIT bot...")
        
        # Cancel JIT task
        jit_task.cancel()
        try:
            await jit_task
        except asyncio.CancelledError:
            pass
            
        logger.info("JIT bot stopped successfully")
        
    except Exception as e:
        logger.exception(f"Orchestrator error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
