import argparse
import asyncio
import os
import time
import yaml
from pathlib import Path
from loguru import logger
from libs.metrics import start_metrics, LOOP_LATENCY, ORDERS_PLACED
from libs.drift.client import build_client_from_config
from libs.drift.client import Order
import random

HEDGE_CFG = Path("configs/hedge/routing.yaml")
CORE_CFG = os.getenv("DRIFT_CFG", "configs/core/drift_client.yaml")

async def run(env: str = "testnet", metrics_port: int | None = 9102, cfg_path: str = CORE_CFG):
    if metrics_port:
        start_metrics(metrics_port)
    hed = yaml.safe_load(Path(HEDGE_CFG).read_text())["hedge"]
    client = await build_client_from_config(cfg_path)
    logger.info(f"Hedge bot (mode={hed['mode']}) starting – env={env}")
    logger.info(f"Risk params: urgency_threshold={hed['urgency_threshold']}, max_exposure=${hed.get('max_exposure_usd', 1000)}")
    
    # Risk tracking
    current_exposure = 0.0
    last_hedge_time = 0.0
    
    try:
        while True:
            t0 = time.perf_counter()
            
            # Get current market state
            ob = await client.get_orderbook() if hasattr(client, 'get_orderbook') and asyncio.iscoroutinefunction(client.get_orderbook) else client.get_orderbook()
            
            if ob.bids and ob.asks:
                mid = (ob.bids[0][0] + ob.asks[0][0]) / 2.0
                
                # Calculate current exposure (simplified - in real implementation this would come from position data)
                # For now, simulate some exposure changes
                if random.random() < 0.1:  # 10% chance of exposure change
                    exposure_change = random.uniform(-100, 100)
                    current_exposure += exposure_change
                    logger.info(f"[HEDGE] Exposure changed by ${exposure_change:+.2f} to ${current_exposure:.2f}")
                
                # Risk assessment
                urgency = 0.0
                if abs(current_exposure) > hed.get('max_exposure_usd', 1000):
                    urgency = 0.9  # High urgency for over-exposure
                elif abs(current_exposure) > hed.get('max_exposure_usd', 1000) * 0.7:
                    urgency = 0.6  # Medium urgency
                elif abs(current_exposure) > 0:
                    urgency = 0.3  # Low urgency
                
                # Determine hedge action
                if urgency >= hed["urgency_threshold"]:
                    route = "ioc" if urgency >= 0.8 else "passive"
                    
                    # Calculate hedge size (reduce exposure by 50-80%)
                    hedge_size = min(abs(current_exposure) * random.uniform(0.5, 0.8), 500)  # Cap at $500
                    
                    # Determine hedge direction
                    hedge_side = "sell" if current_exposure > 0 else "buy"
                    
                    logger.info(f"[HEDGE] Risk alert: urgency={urgency:.2f}, exposure=${current_exposure:.2f}, route={route}")
                    
                    # Place hedge order
                    try:
                        order = Order(
                            side=hedge_side,
                            price=mid,  # Market order approximation
                            size_usd=hedge_size
                        )
                        
                        order_id = await client.place_order(order) if asyncio.iscoroutinefunction(client.place_order) else client.place_order(order)
                        logger.info(f"[HEDGE] Hedge order placed: {hedge_side.upper()} {order_id} @ ${mid:.4f} for ${hedge_size:.2f}")
                        
                        # Update exposure (simplified)
                        if hedge_side == "sell" and current_exposure > 0:
                            current_exposure -= hedge_size
                        elif hedge_side == "buy" and current_exposure < 0:
                            current_exposure += hedge_size
                        
                        ORDERS_PLACED.inc()
                        last_hedge_time = time.time()
                        
                    except Exception as e:
                        logger.error(f"[HEDGE] Failed to place hedge order: {e}")
                        ORDERS_PLACED.inc(0)
                else:
                    route = "passive"
                    logger.info(f"[HEDGE] No action needed: urgency={urgency:.2f}, exposure=${current_exposure:.2f} → route={route}")
                
                # Log status periodically
                if time.time() - last_hedge_time > 30:  # Log every 30 seconds if no recent hedge
                    logger.info(f"[HEDGE] Status: exposure=${current_exposure:.2f}, urgency={urgency:.2f}, route={route}")
            
            LOOP_LATENCY.observe(time.perf_counter() - t0)
            await asyncio.sleep(2.0)
            
    except KeyboardInterrupt:
        logger.info("Hedge bot shutdown requested")
    except Exception as e:
        logger.error(f"Hedge bot error: {e}")
        raise
    finally:
        close = getattr(client, "close", None)
        if asyncio.iscoroutinefunction(close):
            await close()
        elif callable(close):
            close()
        logger.info("Hedge bot shutdown complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=os.getenv("DRIFT_ENV", "testnet"))
    parser.add_argument("--metrics-port", type=int, default=9102)
    parser.add_argument("--cfg", default=CORE_CFG)
    args = parser.parse_args()
    try:
        asyncio.run(run(env=args.env, metrics_port=args.metrics_port, cfg_path=args.cfg))
    except KeyboardInterrupt:
        logger.info("Hedge bot shutdown")