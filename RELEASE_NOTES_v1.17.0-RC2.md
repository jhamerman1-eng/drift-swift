# 📦 v1.17.0‑RC2 — Hedge & Trend Bot Integration

## Overview

This release candidate builds on top of **v1.17.0‑RC** by
implementing full asynchronous trading loops for the Hedge and Trend
bots.  It also ports the proven v16.9 parameters for hedge routing
and trend filters into the new YAML configuration format.  The goal
is to demonstrate how the new primitives (async Drift client,
PositionTracker, OrderManager, RiskManager) can be composed into
production‑ready bots.

## ✨ What’s New

### Hedge Bot (`bots/hedge/main.py`)

* Implements an asynchronous hedging loop that monitors net exposure
  via `PositionTracker` and compares it to the `max_inventory_usd`
  threshold from the configuration.
* Decides between **passive** and **IOC** routes based on the
  `urgency_threshold` (0.7 by default).  High urgency triggers IOC
  orders with a wider slippage cap, while normal urgency hedges
  passively.
* Fetches top‑of‑book mid prices from the async `DriftClient` to
  compute limit prices with configurable slippage (bps).
* Records all placed orders in `OrderManager` and updates net
  exposure locally (in a real implementation this should wait for
  fill confirmations).
* Respects drawdown rails by querying the enhanced `RiskManager` on
  each iteration; if trading is disallowed it cancels all open
  orders.
* Configurable via `configs/hedge/routing.yaml`.  The YAML now
  includes `mode`, `max_inventory_usd`, `urgency_threshold`,
  `passive` and `ioc` sections (derived from v16.9) as well as
  venue definitions.

### Trend Bot (`bots/trend/main.py`)

* Introduces a fully asynchronous trend‑following loop that maintains
  rolling price histories to compute **MACD**, **signal line** and
  **momentum** indicators.
* Ports the v16.9 MACD parameters (fast=12, slow=26, signal=9) and
  momentum window (14) into `configs/trend/filters.yaml`.
* Optional ATR/ADX filtering configuration is retained but not yet
  implemented (disabled by default).
* Determines a trade signal by combining the MACD histogram and
  momentum; scales the notional size based on a `position_scaler`
  and `max_position_usd`.  Positive signals produce buys, negative
  signals produce sells.
* Uses the `RiskManager` to enforce drawdown rails and trend pause
  thresholds before placing each order.
* Records orders via `OrderManager` and updates net exposure via
  `PositionTracker`.
* Configurable via the updated trend YAML; new keys
  `max_position_usd` and `position_scaler` allow tuning of trade
  sizes.

### Config Updates

* `configs/hedge/routing.yaml` has been restructured to mirror v16.9:
  it now nests all hedge parameters under a `hedge` root key and
  defines `max_inventory_usd`, `urgency_threshold`, `passive` and
  `ioc` slippage caps and venue preferences.  This file also retains
  a `venues` list for fee assumptions.
* `configs/trend/filters.yaml` adopts the v16.9 trend structure:
  `use_macd`, `macd.{fast,slow,signal}`, `momentum_window` and
  `atr_adx_filters`.  New keys `max_position_usd` and
  `position_scaler` were added to control sizing.

### Library Enhancements

* Added an **async Drift client** in `libs/drift/client.py` with
  connection pooling and rate limiting, plus a `MockDriftClient` for
  offline development.
* Added `libs/order_management.py` providing `PositionTracker` and
  `OrderManager` classes.
* Extended `orchestrator/risk_manager.py` to track peak equity and
  return fine‑grained permissions (`allow_trading`, `allow_trend`,
  `tighten_quotes`).
* Updated `libs/risk/crash_detector.py` (Crash Sentinel V2) to
  implement a rolling sigma detector; thresholds can be tuned via
  YAML.

### CI & Dependencies

* Added dev dependencies (`aiohttp`, `websockets`, `numpy`) to
  `requirements.txt` to support asynchronous networking and
  numerical computations.
* Introduced `requirements-dev.txt` and a GitHub Actions workflow for
  linting (ruff), type checking (mypy) and tests (pytest).

## 🔧 Migration Notes

* To try the new bots, set `DRIFT_CFG` to your drift client YAML and
  optionally `HEDGE_CFG` and `TREND_CFG` to override the default
  config paths.
* For hedging, ensure that `max_inventory_usd` matches your risk
  tolerance and adjust `urgency_threshold`, `passive.max_slippage_bps`
  and `ioc.max_slippage_bps` according to market conditions.
* For trend‑following, tune `position_scaler` and
  `max_position_usd` to scale trades appropriately.
* Crash Sentinel thresholds can be adjusted in
  `configs/risk/crash.yaml` (sigma threshold, min_abs_move_bps) and
  integrated into the risk manager if desired.

## 🧪 Next Steps & Recommendations

1. **Integrate driftpy**: Implement `DriftpyClient` in
   `libs/drift/client.py` using the official `driftpy` library and
   wallet signing to connect to real markets.
2. **Backtest and tune**: Run the new hedge and trend bots in a
   controlled simulation or paper trading environment to calibrate
   urgency thresholds, slippage caps and sizing parameters.
3. **Enhance monitoring**: Add Prometheus metrics for order latency,
   fill rate, P&L attribution and crash sentinel triggers.  Hook
   metrics into your Grafana dashboards.
4. **Position management**: Extend `OrderManager` to reconcile
   partial fills and handle cancels/replacements.  Subscribe to
   exchange fill events to update `PositionTracker` accurately.
5. **Further risk controls**: Integrate the Crash Sentinel into the
   risk manager’s decision engine, implement trade kill switches and
   dynamic spread widening during volatility spikes.

This RC brings the project materially closer to a production‑ready
multi‑bot stack while preserving the operator‑friendly configuration
format from earlier versions.