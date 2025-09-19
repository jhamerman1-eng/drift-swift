#!/usr/bin/env python3
"""
DLOB Auction Parameters Integration
Fetches optimal auction parameters for Swift orders to maximize edge
"""

import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def fetch_auction_params(cfg: Dict[str, Any], order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Fetch auction parameters from DLOB API for optimal Swift order execution
    
    Args:
        cfg: Configuration dictionary with DLOB settings
        order: Order parameters (market_index, market_type, direction, amount)
        
    Returns:
        Dict with auction_duration, auction_start_price, auction_end_price or None
    """
    try:
        if not cfg.get("dlob", {}).get("enabled", True):
            logger.debug("DLOB auction params disabled in config")
            return None
            
        base_url = cfg.get("dlob", {}).get("base_url", "https://dlob.drift.trade")
        timeout = cfg.get("dlob", {}).get("timeout_seconds", 0.6)
        
        # Prepare query parameters
        query_params = {
            "marketIndex": order["market_index"],
            "marketType": order["market_type"],
            "direction": order["direction"],
            "assetType": "base"
        }
        
        # Add amount (prefer base_asset_amount)
        if "base_asset_amount" in order:
            query_params["amount"] = order["base_asset_amount"]
        elif "quote_asset_amount" in order:
            query_params["amount"] = order["quote_asset_amount"]
            query_params["assetType"] = "quote"
        else:
            logger.warning("No amount field found in order for auction params")
            return None
        
        # Fetch auction parameters
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{base_url}/auctionParams", params=query_params)
            
        if response.status_code != 200:
            logger.debug(f"DLOB auction params failed: {response.status_code}")
            return None
            
        data = response.json()
        
        # Validate response
        required_fields = ["auctionDuration", "auctionStartPrice", "auctionEndPrice"]
        if not all(field in data for field in required_fields):
            logger.warning(f"DLOB response missing required fields: {list(data.keys())}")
            return None
        
        # Convert to Swift format
        auction_params = {
            "auction_duration": int(data["auctionDuration"]),
            "auction_start_price": int(data["auctionStartPrice"]),
            "auction_end_price": int(data["auctionEndPrice"])
        }
        
        logger.info(f"✅ DLOB auction params: duration={auction_params['auction_duration']}ms, "
                   f"start=${auction_params['auction_start_price']/1e6:.4f}, "
                   f"end=${auction_params['auction_end_price']/1e6:.4f}")
        
        return auction_params
        
    except httpx.TimeoutException:
        logger.warning("DLOB auction params request timed out")
        return None
    except httpx.RequestError as e:
        logger.warning(f"DLOB auction params network error: {e}")
        return None
    except Exception as e:
        logger.warning(f"DLOB auction params error: {e}")
        return None

def get_conservative_auction_defaults(order: Dict[str, Any]) -> Dict[str, Any]:
    """
    Provide conservative auction parameter defaults when DLOB is unavailable
    
    Args:
        order: Order parameters with price information
        
    Returns:
        Conservative auction parameters
    """
    # Use a small auction window with tight price bounds
    base_price = order.get("price", 0)
    if base_price <= 0:
        logger.warning("No price in order for conservative auction defaults")
        return {
            "auction_duration": 100,  # 100ms minimum
            "auction_start_price": 0,
            "auction_end_price": 0
        }
    
    # Conservative 0.1% price range
    price_buffer = int(base_price * 0.001)
    
    return {
        "auction_duration": 150,  # 150ms conservative window
        "auction_start_price": base_price - price_buffer,
        "auction_end_price": base_price + price_buffer
    }

def should_use_auction_params(order: Dict[str, Any], cfg: Dict[str, Any]) -> bool:
    """
    Determine if auction parameters should be used for this order
    
    Args:
        order: Order parameters
        cfg: Configuration
        
    Returns:
        True if auction params should be used
    """
    # Check feature flag
    if not cfg.get("feature", {}).get("swift", {}).get("auction_params", True):
        return False
    
    # Only use for marketable orders (not post-only)
    if order.get("intent") == "post_only":
        return False
        
    # Only use for certain order types
    order_type = order.get("order_type", "limit").lower()
    if order_type not in ["market", "limit"]:
        return False
        
    return True
