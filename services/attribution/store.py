#!/usr/bin/env python3
"""
PnL Attribution Store for Trend Bot v3.0
Tracks per-fill attribution for portfolio performance analysis

This module implements the attribution logging system to track
trend bot contribution to overall portfolio performance.

User Story: TREND-008
Persona: Researcher
Goal: Track trend contribution to portfolio Sharpe ratio
"""

from __future__ import annotations
import csv
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class FillSide(Enum):
    """Fill side enumeration"""
    BUY = "buy"
    SELL = "sell"

class FillType(Enum):
    """Fill type classification"""
    ENTRY = "entry"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MANUAL_EXIT = "manual_exit"

@dataclass
class AttributedFill:
    """Individual fill with attribution metadata"""
    fill_id: str
    timestamp: float
    symbol: str
    side: FillSide
    price: float
    size: float
    notional_usd: float
    
    # Attribution fields
    feature: str  # "trend", "jit", "hedge", etc.
    strategy: Optional[str] = None  # "macd_momentum", "mean_revert", etc.
    regime: Optional[str] = None    # "trending_up", "choppy", etc.
    fill_type: FillType = FillType.ENTRY
    
    # Context fields
    entry_reason: Optional[str] = None  # "macd_cross", "momentum_breakout"
    exit_reason: Optional[str] = None   # "stop_loss", "take_profit", "signal_reverse"
    confidence: Optional[float] = None  # Signal confidence 0-1
    risk_adjusted: bool = False         # Whether position was risk-adjusted
    
    # PnL tracking (populated later)
    unrealized_pnl_usd: Optional[float] = None
    realized_pnl_usd: Optional[float] = None
    holding_period_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert enums to strings
        data['side'] = self.side.value
        data['fill_type'] = self.fill_type.value
        return data

class AttributionStore:
    """
    Attribution data store with multiple storage backends
    
    Supports:
    - CSV files for simple analysis
    - SQLite for structured queries
    - JSON files for debugging
    """
    
    def __init__(self, 
                 base_dir: str = "data/attribution",
                 enable_csv: bool = True,
                 enable_sqlite: bool = True,
                 enable_json: bool = False):
        """
        Initialize attribution store
        
        Args:
            base_dir: Base directory for data files
            enable_csv: Enable CSV output
            enable_sqlite: Enable SQLite database
            enable_json: Enable JSON debug files
        """
        self.base_dir = Path(base_dir)
        self.enable_csv = enable_csv
        self.enable_sqlite = enable_sqlite
        self.enable_json = enable_json
        
        # Create directories
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage backends
        self.csv_path = self.base_dir / "trend_fills.csv"
        self.sqlite_path = self.base_dir / "attribution.db"
        self.json_dir = self.base_dir / "json"
        
        if self.enable_json:
            self.json_dir.mkdir(exist_ok=True)
        
        # Initialize backends
        self._init_csv()
        self._init_sqlite()
        
        # In-memory cache for performance analysis
        self.recent_fills: List[AttributedFill] = []
        self.max_cache_size = 1000
        
        logger.info(f"Attribution store initialized at {self.base_dir}")
        logger.info(f"Backends: CSV={enable_csv}, SQLite={enable_sqlite}, JSON={enable_json}")

    def _init_csv(self):
        """Initialize CSV file with headers"""
        if not self.enable_csv:
            return
        
        if not self.csv_path.exists():
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "fill_id", "timestamp", "iso_timestamp", "symbol", "side", "price", 
                    "size", "notional_usd", "feature", "strategy", "regime", "fill_type",
                    "entry_reason", "exit_reason", "confidence", "risk_adjusted",
                    "unrealized_pnl_usd", "realized_pnl_usd", "holding_period_seconds"
                ])
            logger.info(f"Created CSV file: {self.csv_path}")

    def _init_sqlite(self):
        """Initialize SQLite database with schema"""
        if not self.enable_sqlite:
            return
        
        try:
            conn = sqlite3.connect(str(self.sqlite_path))
            cursor = conn.cursor()
            
            # Create fills table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fills (
                    fill_id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    size REAL NOT NULL,
                    notional_usd REAL NOT NULL,
                    feature TEXT NOT NULL,
                    strategy TEXT,
                    regime TEXT,
                    fill_type TEXT NOT NULL,
                    entry_reason TEXT,
                    exit_reason TEXT,
                    confidence REAL,
                    risk_adjusted INTEGER,
                    unrealized_pnl_usd REAL,
                    realized_pnl_usd REAL,
                    holding_period_seconds REAL,
                    created_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            # Create performance summary table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    feature TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    total_fills INTEGER,
                    total_pnl_usd REAL,
                    win_rate REAL,
                    avg_holding_period REAL,
                    sharpe_ratio REAL,
                    max_drawdown REAL,
                    created_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fills_timestamp ON fills(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fills_feature ON fills(feature)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fills_symbol ON fills(symbol)")
            
            conn.commit()
            conn.close()
            
            logger.info(f"SQLite database initialized: {self.sqlite_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite: {e}")

    def log_fill(self,
                 symbol: str,
                 side: Union[str, FillSide],
                 price: float,
                 size: float,
                 notional_usd: float,
                 feature: str = "trend",
                 strategy: Optional[str] = None,
                 regime: Optional[str] = None,
                 fill_type: Union[str, FillType] = FillType.ENTRY,
                 **kwargs) -> str:
        """
        Log an attributed fill
        
        Args:
            symbol: Trading symbol
            side: Buy or sell
            price: Fill price
            size: Fill size
            notional_usd: Notional value in USD
            feature: Attribution feature (trend, jit, hedge)
            strategy: Strategy name
            regime: Market regime
            fill_type: Type of fill (entry, exit, etc.)
            **kwargs: Additional context fields
            
        Returns:
            Fill ID
        """
        try:
            # Generate unique fill ID
            fill_id = f"{feature}-{int(time.time() * 1000000)}"
            
            # Convert string enums
            if isinstance(side, str):
                side = FillSide(side.lower())
            if isinstance(fill_type, str):
                fill_type = FillType(fill_type.lower())
            
            # Create attributed fill
            fill = AttributedFill(
                fill_id=fill_id,
                timestamp=time.time(),
                symbol=symbol,
                side=side,
                price=price,
                size=size,
                notional_usd=notional_usd,
                feature=feature,
                strategy=strategy,
                regime=regime,
                fill_type=fill_type,
                entry_reason=kwargs.get("entry_reason"),
                exit_reason=kwargs.get("exit_reason"),
                confidence=kwargs.get("confidence"),
                risk_adjusted=kwargs.get("risk_adjusted", False),
                unrealized_pnl_usd=kwargs.get("unrealized_pnl_usd"),
                realized_pnl_usd=kwargs.get("realized_pnl_usd"),
                holding_period_seconds=kwargs.get("holding_period_seconds")
            )
            
            # Store in backends
            self._store_csv(fill)
            self._store_sqlite(fill)
            if self.enable_json:
                self._store_json(fill)
            
            # Add to cache
            self.recent_fills.append(fill)
            if len(self.recent_fills) > self.max_cache_size:
                self.recent_fills = self.recent_fills[-self.max_cache_size:]
            
            logger.info(f"Logged fill: {fill_id} {symbol} {side.value} {size:.4f} @ ${price:.4f}")
            logger.debug(f"Attribution: feature={feature}, strategy={strategy}, regime={regime}")
            
            return fill_id
            
        except Exception as e:
            logger.error(f"Failed to log fill: {e}")
            return ""

    def _store_csv(self, fill: AttributedFill):
        """Store fill in CSV file"""
        if not self.enable_csv:
            return
        
        try:
            with open(self.csv_path, "a", newline="") as f:
                writer = csv.writer(f)
                iso_timestamp = datetime.fromtimestamp(fill.timestamp, tz=timezone.utc).isoformat()
                writer.writerow([
                    fill.fill_id, fill.timestamp, iso_timestamp, fill.symbol,
                    fill.side.value, f"{fill.price:.6f}", f"{fill.size:.6f}",
                    f"{fill.notional_usd:.2f}", fill.feature, fill.strategy,
                    fill.regime, fill.fill_type.value, fill.entry_reason,
                    fill.exit_reason, fill.confidence, fill.risk_adjusted,
                    fill.unrealized_pnl_usd, fill.realized_pnl_usd,
                    fill.holding_period_seconds
                ])
        except Exception as e:
            logger.error(f"Failed to store CSV: {e}")

    def _store_sqlite(self, fill: AttributedFill):
        """Store fill in SQLite database"""
        if not self.enable_sqlite:
            return
        
        try:
            conn = sqlite3.connect(str(self.sqlite_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO fills (
                    fill_id, timestamp, symbol, side, price, size, notional_usd,
                    feature, strategy, regime, fill_type, entry_reason, exit_reason,
                    confidence, risk_adjusted, unrealized_pnl_usd, realized_pnl_usd,
                    holding_period_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fill.fill_id, fill.timestamp, fill.symbol, fill.side.value,
                fill.price, fill.size, fill.notional_usd, fill.feature,
                fill.strategy, fill.regime, fill.fill_type.value,
                fill.entry_reason, fill.exit_reason, fill.confidence,
                int(fill.risk_adjusted) if fill.risk_adjusted else 0,
                fill.unrealized_pnl_usd, fill.realized_pnl_usd,
                fill.holding_period_seconds
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store SQLite: {e}")

    def _store_json(self, fill: AttributedFill):
        """Store fill in JSON debug file"""
        try:
            date_str = datetime.fromtimestamp(fill.timestamp).strftime("%Y-%m-%d")
            json_path = self.json_dir / f"fills_{date_str}.json"
            
            # Load existing data
            fills_data = []
            if json_path.exists():
                with open(json_path, "r") as f:
                    fills_data = json.load(f)
            
            # Add new fill
            fills_data.append(fill.to_dict())
            
            # Save back
            with open(json_path, "w") as f:
                json.dump(fills_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to store JSON: {e}")

    def get_performance_summary(self,
                              feature: Optional[str] = None,
                              symbol: Optional[str] = None,
                              days_back: int = 30) -> Dict[str, Any]:
        """
        Get performance summary for attribution analysis
        
        Args:
            feature: Filter by feature (trend, jit, hedge)
            symbol: Filter by symbol
            days_back: Number of days to analyze
            
        Returns:
            Performance summary dictionary
        """
        if not self.enable_sqlite:
            logger.warning("Performance summary requires SQLite backend")
            return {}
        
        try:
            conn = sqlite3.connect(str(self.sqlite_path))
            cursor = conn.cursor()
            
            # Build query with filters
            where_clauses = ["timestamp >= ?"]
            params = [time.time() - (days_back * 24 * 3600)]
            
            if feature:
                where_clauses.append("feature = ?")
                params.append(feature)
            
            if symbol:
                where_clauses.append("symbol = ?")
                params.append(symbol)
            
            where_clause = " AND ".join(where_clauses)
            
            # Get summary statistics
            cursor.execute(f"""
                SELECT 
                    feature,
                    symbol,
                    COUNT(*) as total_fills,
                    SUM(CASE WHEN realized_pnl_usd IS NOT NULL THEN realized_pnl_usd ELSE 0 END) as total_pnl,
                    AVG(CASE WHEN realized_pnl_usd IS NOT NULL THEN realized_pnl_usd END) as avg_pnl,
                    SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate,
                    AVG(holding_period_seconds) as avg_holding_period,
                    MIN(timestamp) as first_fill,
                    MAX(timestamp) as last_fill
                FROM fills 
                WHERE {where_clause}
                GROUP BY feature, symbol
                ORDER BY total_pnl DESC
            """, params)
            
            results = cursor.fetchall()
            
            summary = {
                "query_params": {
                    "feature": feature,
                    "symbol": symbol,
                    "days_back": days_back
                },
                "features": []
            }
            
            for row in results:
                feature_summary = {
                    "feature": row[0],
                    "symbol": row[1],
                    "total_fills": row[2],
                    "total_pnl_usd": round(row[3], 2),
                    "avg_pnl_usd": round(row[4], 2) if row[4] else 0,
                    "win_rate": round(row[5] * 100, 1) if row[5] else 0,
                    "avg_holding_period_hours": round(row[6] / 3600, 2) if row[6] else 0,
                    "first_fill": row[7],
                    "last_fill": row[8]
                }
                summary["features"].append(feature_summary)
            
            # Calculate overall summary
            if summary["features"]:
                summary["overall"] = {
                    "total_pnl_usd": sum(f["total_pnl_usd"] for f in summary["features"]),
                    "total_fills": sum(f["total_fills"] for f in summary["features"]),
                    "avg_win_rate": sum(f["win_rate"] for f in summary["features"]) / len(summary["features"])
                }
            
            conn.close()
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate performance summary: {e}")
            return {}

    def update_fill_pnl(self, fill_id: str, unrealized_pnl: Optional[float] = None, realized_pnl: Optional[float] = None):
        """
        Update PnL for an existing fill
        
        Args:
            fill_id: Fill ID to update
            unrealized_pnl: Unrealized PnL in USD
            realized_pnl: Realized PnL in USD
        """
        if not self.enable_sqlite:
            return
        
        try:
            conn = sqlite3.connect(str(self.sqlite_path))
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if unrealized_pnl is not None:
                updates.append("unrealized_pnl_usd = ?")
                params.append(unrealized_pnl)
            
            if realized_pnl is not None:
                updates.append("realized_pnl_usd = ?")
                params.append(realized_pnl)
            
            if updates:
                params.append(fill_id)
                cursor.execute(f"""
                    UPDATE fills 
                    SET {', '.join(updates)}
                    WHERE fill_id = ?
                """, params)
                
                conn.commit()
                logger.debug(f"Updated PnL for fill {fill_id}: unrealized={unrealized_pnl}, realized={realized_pnl}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update fill PnL: {e}")

    def export_to_parquet(self, output_path: str, days_back: Optional[int] = None):
        """
        Export attribution data to Parquet for analysis
        
        Args:
            output_path: Output Parquet file path
            days_back: Number of days to export (None for all data)
        """
        try:
            import pandas as pd
            
            if not self.enable_sqlite:
                logger.error("Parquet export requires SQLite backend")
                return
            
            conn = sqlite3.connect(str(self.sqlite_path))
            
            query = "SELECT * FROM fills"
            params = []
            
            if days_back:
                query += " WHERE timestamp >= ?"
                params.append(time.time() - (days_back * 24 * 3600))
            
            query += " ORDER BY timestamp"
            
            df = pd.read_sql_query(query, conn, params=params)
            
            # Convert timestamp to datetime
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
            
            df.to_parquet(output_path, index=False)
            logger.info(f"Exported {len(df)} fills to {output_path}")
            
            conn.close()
            
        except ImportError:
            logger.error("Parquet export requires pandas: pip install pandas pyarrow")
        except Exception as e:
            logger.error(f"Failed to export to Parquet: {e}")

    def get_recent_fills(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent fills from cache"""
        return [fill.to_dict() for fill in self.recent_fills[-count:]]

    def cleanup_old_data(self, days_to_keep: int = 90):
        """
        Clean up old attribution data
        
        Args:
            days_to_keep: Number of days of data to keep
        """
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        try:
            if self.enable_sqlite:
                conn = sqlite3.connect(str(self.sqlite_path))
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM fills WHERE timestamp < ?", (cutoff_time,))
                deleted_count = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                logger.info(f"Cleaned up {deleted_count} old fills (older than {days_to_keep} days)")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")



