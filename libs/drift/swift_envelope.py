#!/usr/bin/env python3
"""
Swift Envelope Creator and Processor
Handles Swift order envelope creation and processing using proper DriftPy types
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass
from solders.keypair import Keypair

# Set up logger
logger = logging.getLogger(__name__)

# Import centralized configuration manager
try:
    from ..configs.centralized_config_manager import (
        get_compute_budget_for_strategy,
        TradingStrategy,
        MarketCondition
    )
    CENTRALIZED_CONFIG_AVAILABLE = True
except ImportError:
    CENTRALIZED_CONFIG_AVAILABLE = False
    logger.warning("Centralized configuration manager not available")

# Import DriftPy types for proper Swift integration
try:
    from driftpy.types import (
        OrderParams, OrderType, MarketType, PositionDirection,
        PostOnlyParams, SignedMsgOrderParamsMessage
    )
    from driftpy.constants.numeric_constants import PRICE_PRECISION, BASE_PRECISION
    DRIFTPY_AVAILABLE = True
except ImportError:
    DRIFTPY_AVAILABLE = False
    # Set to None when not available
    OrderParams = None  # type: ignore
    OrderType = None  # type: ignore
    MarketType = None  # type: ignore
    PositionDirection = None  # type: ignore
    PostOnlyParams = None  # type: ignore
    SignedMsgOrderParamsMessage = None  # type: ignore

@dataclass
class SwiftOrderParams:
    """Parameters for Swift order creation with compute budget optimization"""
    market_index: int
    market_type: str
    side: str
    price: float
    size: float
    taker_authority: str
    sub_account_id: int = 0
    order_type: str = "limit"
    post_only: bool = True
    reduce_only: bool = False

    # Compute budget optimization parameters
    compute_unit_limit: Optional[int] = None
    compute_unit_price: Optional[int] = None
    priority_level: Optional[str] = None

    # Trading strategy for optimization
    trading_strategy: Optional[TradingStrategy] = None
    market_condition: Optional[MarketCondition] = None

    def apply_compute_budget_optimization(self) -> None:
        """
        Apply compute budget optimization based on trading strategy and market conditions

        This method uses the centralized configuration manager to determine optimal
        compute budget parameters for the current order.
        """
        if not CENTRALIZED_CONFIG_AVAILABLE:
            logger.debug("Centralized configuration not available for compute budget optimization")
            return

        try:
            # Determine strategy and market condition
            strategy = self.trading_strategy or TradingStrategy.MARKET_MAKING
            market_condition = self.market_condition or MarketCondition.NORMAL

            # Get optimized compute budget
            compute_budget = get_compute_budget_for_strategy(
                strategy=strategy,
                market_condition=market_condition,
                priority_level=self.priority_level or "medium"
            )

            # Apply optimization if successful
            if not compute_budget.get('fallback', True):
                self.compute_unit_limit = compute_budget['compute_unit_limit']
                self.compute_unit_price = compute_budget['compute_unit_price']
                self.priority_level = compute_budget['priority_level']

                logger.debug(
                    f"Applied compute budget optimization for {strategy.value}: "
                    f"{self.compute_unit_limit} units @ {self.compute_unit_price} µL"
                )
            else:
                logger.debug("Using default compute budget parameters")

        except Exception as e:
            logger.warning(f"Failed to apply compute budget optimization: {e}")

    def get_envelope_metadata(self) -> Dict[str, Any]:
        """Get metadata for envelope creation including compute budget info"""
        metadata = {
            "sub_account_id": self.sub_account_id,
            "timestamp": int(time.time() * 1000),
            "order_type": self.order_type,
            "post_only": self.post_only,
            "reduce_only": self.reduce_only
        }

        # Add compute budget information if available
        if self.compute_unit_limit is not None:
            metadata["compute_unit_limit"] = self.compute_unit_limit
        if self.compute_unit_price is not None:
            metadata["compute_unit_price"] = self.compute_unit_price
        if self.priority_level is not None:
            metadata["priority_level"] = self.priority_level

        return metadata

class SwiftEnvelopeCreator:
    """Creates Swift order envelopes"""
    
    def __init__(self):
        self.envelope_version = "1.0"
    
    def create_order_envelope(
        self,
        params: SwiftOrderParams,
        keypair: Keypair,
        drift_client=None,
        cluster: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Swift order envelope using centralized configuration and compute budget optimization

        Args:
            params: Swift order parameters
            keypair: Keypair for signing
            drift_client: Drift client for envelope creation
            cluster: Cluster override (uses centralized config if None)

        Returns:
            Swift API compatible envelope
        """
        # Pre-validate parameters
        if not all([
            params.market_index is not None,
            params.market_type,
            params.side,
            params.price is not None,
            params.size is not None,
            params.taker_authority
        ]):
            raise ValueError("Missing required order parameters")

        # Apply compute budget optimization using centralized configuration
        params.apply_compute_budget_optimization()

        # Get cluster from centralized configuration if not provided
        if cluster is None and CENTRALIZED_CONFIG_AVAILABLE:
            try:
                from ..configs.centralized_config_manager import get_drift_config
                drift_config = get_drift_config()
                cluster = drift_config.env
                logger.debug(f"Using centralized configuration for cluster: {cluster}")
            except Exception as e:
                logger.debug(f"Could not get cluster from centralized config: {e}")
                cluster = "devnet"

        try:
            # FIXED: Try DriftPy envelope first, fallback to JSON if needed
            if not DRIFTPY_AVAILABLE or not drift_client:
                logger.warning("[ENVELOPE] DriftPy not available, using JSON fallback")
                return self._create_json_envelope(params, keypair, cluster or "devnet")

            logger.info("[ENVELOPE] Creating DriftPy envelope with centralized config and compute budget optimization")
            envelope = self._create_driftpy_envelope(params, keypair, drift_client, cluster or "devnet")

            validation_result = self._validate_envelope(envelope)
            if not validation_result["valid"]:
                logger.error(f"[ENVELOPE] Validation failed: {validation_result['errors']}")
                logger.warning("[ENVELOPE] Falling back to JSON envelope due to validation failure")
                return self._create_json_envelope(params, keypair, cluster or "devnet")

            logger.info("[ENVELOPE] DriftPy envelope created and validated successfully")
            return envelope

        except Exception as e:
            logger.error(f"Failed to create DriftPy envelope: {e}")
            logger.warning("Falling back to JSON envelope creation")
            return self._create_json_envelope(params, keypair, cluster or "devnet")
    
    def _create_driftpy_envelope(self, params: SwiftOrderParams, keypair: Keypair, drift_client, cluster: str = "devnet") -> Dict[str, Any]:
        """Create envelope using proper Swift-compatible byte signing"""
        import base64
        import asyncio

        # Convert to DriftPy OrderParams - Use None for Option types (DriftPy handles conversion)
        auction_duration_option = None  # Use None - DriftPy handles conversion
        max_ts_option = None  # Use None - DriftPy handles conversion
        
        # Use DriftPy precision helpers for proper scaling
        try:
            # Use drift client's precision conversion methods
            price_precision = drift_client.convert_to_price_precision(params.price)
            size_precision = drift_client.convert_to_perp_precision(params.size)
        except Exception as e:
            logger.warning(f"Could not get market info for precision conversion: {e}")
            # Fallback to manual precision
            price_precision = int(params.price * PRICE_PRECISION)
            size_precision = int(params.size * BASE_PRECISION)
        
        # DEBUG: Log both raw and scaled values
        logger.info(f"🔍 DRIFTPY DEBUG - Raw price: ${params.price:.6f}, Raw size: {params.size:.6f}")
        logger.info(f"🔍 DRIFTPY DEBUG - Scaled price: {price_precision}, Scaled size: {size_precision}")
        logger.info(f"🔍 DRIFTPY DEBUG - Verification: {price_precision / PRICE_PRECISION:.6f} should equal {params.price:.6f}")
        
        # CRITICAL FIX: Ensure auction prices are never None to prevent signature verification failures
        auction_start_price = price_precision if price_precision is not None else 0
        auction_end_price = price_precision if price_precision is not None else 0

        order_params = OrderParams(  # type: ignore
            order_type=OrderType.Limit(),  # type: ignore
            market_type=MarketType.Perp(),  # type: ignore
            direction=PositionDirection.Long() if params.side.lower() == 'buy' else PositionDirection.Short(),  # type: ignore
            market_index=params.market_index,
            base_asset_amount=size_precision,  # Use DriftPy precision helper
            price=price_precision,  # Use DriftPy precision helper
            user_order_id=0,
            post_only=PostOnlyParams.MustPostOnly() if params.post_only else PostOnlyParams.TryPostOnly(),  # type: ignore
            reduce_only=params.reduce_only,
            auction_duration=auction_duration_option,  # FIXED: Consistent None usage
            auction_start_price=auction_start_price,  # Use safe auction price
            auction_end_price=auction_end_price,  # Use safe auction price
            max_ts=max_ts_option  # FIXED: Consistent None usage
        )

        # Get current slot
        slot = 0
        try:
            if hasattr(drift_client, 'connection') and drift_client.connection:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    slot_task = loop.create_task(drift_client.connection.get_slot())
                    slot_response = loop.run_until_complete(slot_task)
                    slot = slot_response.value
                except RuntimeError:
                    slot_response = asyncio.run(drift_client.connection.get_slot())
                    slot = slot_response.value
                except Exception as e:
                    print(f"Warning: Could not get current slot: {e}, using timestamp")
                    slot = int(time.time() * 1000)
            else:
                slot = int(time.time() * 1000)
        except Exception as e:
            print(f"Warning: Slot retrieval failed: {e}, using timestamp")
            slot = int(time.time() * 1000)

        # Generate UUID as bytes
        order_uuid_bytes = uuid.uuid4().bytes[:8]
        order_uuid_str = str(uuid.uuid4())

        # Create the signed message structure for DriftPy - FIXED: Proper Option handling
        msg = SignedMsgOrderParamsMessage(  # type: ignore
            signed_msg_order_params=order_params,  # type: ignore
            sub_account_id=params.sub_account_id,
            slot=slot,
            uuid=order_uuid_bytes,
            stop_loss_order_params=None,  # Option type: None is valid
            take_profit_order_params=None,  # Option type: None is valid
        )

        # DEBUG: Log the order_params to identify serialization issues
        logger.info(f"[ENVELOPE] OrderParams created: market_index={order_params.market_index}, direction={order_params.direction}")
        logger.info(f"[ENVELOPE] OrderParams: base_asset_amount={order_params.base_asset_amount}, price={order_params.price}")
        logger.info(f"[ENVELOPE] OrderParams: post_only={order_params.post_only}, reduce_only={order_params.reduce_only}")
        logger.info(f"[ENVELOPE] OrderParams: auction_duration={order_params.auction_duration}, max_ts={order_params.max_ts}")
        logger.info("[ENVELOPE] CRITICAL FIX: auction_duration and max_ts are now properly set to None for Option handling")

        # CRITICAL FIX: Safely format auction prices to avoid None formatting errors
        try:
            auction_start_str = str(order_params.auction_start_price) if order_params.auction_start_price is not None else "None"
            auction_end_str = str(order_params.auction_end_price) if order_params.auction_end_price is not None else "None"
            logger.debug(f"[ENVELOPE] Auction params: start={auction_start_str}, end={auction_end_str}")
        except Exception as e:
            logger.debug(f"[ENVELOPE] Could not format auction params: {e}")

        # CRITICAL FIX: Encode the COMPLETE SignedMsgOrderParamsMessage for Swift verification
        # Swift verifies the Borsh-encoded bytes of the entire message, not just order_params
        message_bytes = drift_client.encode_signed_msg_order_params_message(msg)
        
        # Sign the complete encoded message with the same keypair
        sig_obj = keypair.sign_message(message_bytes)
        sig_bytes = bytes(sig_obj)  # Must be exactly 64 bytes
        signature_b64 = base64.b64encode(sig_bytes).decode("ascii")

        # Get the user account public key (different from wallet public key)
        from driftpy.addresses import get_user_account_public_key
        user_account_pubkey = get_user_account_public_key(
            drift_client.program_id,
            keypair.pubkey(),
            params.sub_account_id
        )

        # Build envelope with centralized configuration and compute budget optimization
        envelope = {
            # Swift API expects these exact field names and format
            "market_index": params.market_index,  # Required: The type of order e.g. market, limit
            "market_type": params.market_type.lower(),  # Required: The market to place order in
            "message": message_bytes.hex(),  # Required: Signed order message (hex-encoded)
            "signature": signature_b64,  # Required: Signature from signing the message
            "taker_authority": str(user_account_pubkey),  # Required: Public key of user account
            "signing_authority": str(keypair.pubkey()),  # Optional: Public key of signing authority (delegate)
            # Legacy aliases for backward compatibility (CRITICAL FIX)
            "order_message": message_bytes.hex(),  # Legacy field name used by some Swift integrations
            "order_signature": signature_b64,  # Legacy field name used by some Swift integrations
            # Additional metadata for compatibility
            "sub_account_id": params.sub_account_id,
            "slot": slot,
            "ts": int(time.time() * 1000),
            "cluster": cluster
        }

        # Add compute budget optimization if available
        if params.compute_unit_limit is not None:
            envelope["compute_unit_limit"] = params.compute_unit_limit
            logger.debug(f"Added compute unit limit to envelope: {params.compute_unit_limit}")

        if params.compute_unit_price is not None:
            envelope["compute_unit_price"] = params.compute_unit_price
            logger.debug(f"Added compute unit price to envelope: {params.compute_unit_price}")

        if params.priority_level is not None:
            envelope["priority_level"] = params.priority_level
            logger.debug(f"Added priority level to envelope: {params.priority_level}")

        # Add trading strategy metadata for analytics
        if params.trading_strategy is not None:
            envelope["trading_strategy"] = params.trading_strategy.value
        if params.market_condition is not None:
            envelope["market_condition"] = params.market_condition.value

        return envelope
    
    def _create_json_envelope(self, params: SwiftOrderParams, keypair: Keypair, cluster: str = "devnet") -> Dict[str, Any]:
        """Fallback JSON-based envelope creation with proper signature padding"""
        # Import DriftPy constants for proper precision
        try:
            from driftpy.constants.numeric_constants import PRICE_PRECISION, BASE_PRECISION
        except ImportError:
            # Fallback values if DriftPy not available
            BASE_PRECISION = int(1e9)  # 1e9 for base asset amount
            PRICE_PRECISION = int(1e6)  # 1e6 for price
        
        # CRITICAL FIX: Handle None values safely to prevent signature verification failures
        price_value = params.price if params.price is not None else 0
        size_value = params.size if params.size is not None else 0

        # Convert using proper precision
        price_precision = int(price_value * PRICE_PRECISION)
        size_precision = int(size_value * BASE_PRECISION)
        
        # CRITICAL FIX: Safe debug logging to prevent None formatting errors
        try:
            price_str = f"${params.price:.6f}" if params.price is not None else "None"
            size_str = f"{params.size:.6f}" if params.size is not None else "None"
            logger.info(f"🔍 JSON FALLBACK DEBUG - Raw price: {price_str}, Raw size: {size_str}")
            logger.info(f"🔍 JSON FALLBACK DEBUG - Scaled price: {price_precision}, Scaled size: {size_precision}")

            if params.price is not None:
                expected_price = price_precision / PRICE_PRECISION
                logger.info(f"🔍 JSON FALLBACK DEBUG - Verification: {expected_price:.6f} should equal {params.price:.6f}")
        except Exception as e:
            logger.debug(f"[ENVELOPE] Could not log JSON fallback debug info: {e}")
        
        # Get the derived user account public key for proper taker_authority
        from driftpy.addresses import get_user_account_public_key
        from driftpy.constants.config import DRIFT_PROGRAM_ID
        # Note: For JSON fallback, we need to use a default program ID since we don't have drift_client
        program_id = DRIFT_PROGRAM_ID  # Default Drift program ID
        user_account_pubkey = get_user_account_public_key(
            program_id,
            keypair.pubkey(),
            params.sub_account_id
        )
        
        # Create simplified envelope for Swift API compatibility
        import base64
        
        # Create the order message in Swift's expected format (MINIMAL for consistency)
        order_message = {
            "marketIndex": int(params.market_index),
            "marketType": "perp", 
            "direction": "long" if params.side == "buy" else "short",
            "baseAssetAmount": str(size_precision),  # Use properly scaled size
            "price": str(price_precision),  # Use properly scaled price
            "postOnly": params.post_only,
            "reduceOnly": params.reduce_only
            # CRITICAL FIX: Removed auction fields to match signing consistency
            # Swift API should handle these as defaults, not explicit nulls
        }
        
        # Convert to compact JSON for signing
        message_json = json.dumps(order_message, separators=(',', ':'))
        message_bytes = message_json.encode('utf-8')
        
        # Sign the message
        signature = keypair.sign_message(message_bytes)
        
        # CRITICAL FIX: Ensure proper base64 signature encoding with padding
        signature_b64 = base64.b64encode(bytes(signature)).decode('ascii')
        # Ensure proper padding (base64 strings should be multiple of 4 chars)
        while len(signature_b64) % 4:
            signature_b64 += '='
        
        logger.debug(f"🔧 Signature padding ensured: {len(signature_b64)} chars")
        
        # Create envelope in Swift's expected format matching official Drift Labs specification
        envelope = {
            "market_index": int(params.market_index),  # Required: The type of order e.g. market, limit
            "market_type": "perp",  # Required: The market to place order in
            "message": message_json,  # Required: Signed order message (JSON for fallback)
            "signature": signature_b64,  # Required: Signature from signing the message
            "taker_authority": str(user_account_pubkey),  # Required: Public key of user account
            "signing_authority": str(keypair.pubkey()),  # Optional: Public key of signing authority (delegate)
            # Legacy aliases for backward compatibility (CRITICAL FIX)
            "order_message": message_json,  # Legacy field name used by some Swift integrations
            "order_signature": signature_b64,  # Legacy field name used by some Swift integrations
            # Additional metadata for compatibility
            "sub_account_id": int(params.sub_account_id),
            "slot": int(time.time() * 1000),  # Current timestamp as slot
            "ts": int(time.time() * 1000),
            "cluster": cluster or "devnet"  # Use provided cluster or default
        }

        # Add compute budget optimization to JSON envelope
        if params.compute_unit_limit is not None:
            envelope["compute_unit_limit"] = params.compute_unit_limit
            logger.debug(f"Added compute unit limit to JSON envelope: {params.compute_unit_limit}")

        if params.compute_unit_price is not None:
            envelope["compute_unit_price"] = params.compute_unit_price
            logger.debug(f"Added compute unit price to JSON envelope: {params.compute_unit_price}")

        if params.priority_level is not None:
            envelope["priority_level"] = params.priority_level
            logger.debug(f"Added priority level to JSON envelope: {params.priority_level}")

        # Add trading strategy metadata for analytics
        if params.trading_strategy is not None:
            envelope["trading_strategy"] = params.trading_strategy.value
        if params.market_condition is not None:
            envelope["market_condition"] = params.market_condition.value
        
        # Validate envelope before returning
        validation_result = self._validate_envelope(envelope)
        if not validation_result["valid"]:
            logger.error(f"[ENVELOPE] JSON envelope validation failed: {validation_result['errors']}")
            raise ValueError(f"Invalid envelope: {validation_result['errors']}")
        
        logger.info("[ENVELOPE] ✅ JSON envelope created and validated with official Swift format")
        return envelope
    
    def create_cancel_envelope(self, order_id: str, taker_authority: str, keypair: Keypair) -> Dict[str, Any]:
        """Create a Swift cancel envelope"""
        # Pre-validate parameters
        if not order_id or not taker_authority:
            raise ValueError("Missing required cancel parameters")

        try:
            # Create cancel message
            cancel_message = {
                "action": "cancel_order",
                "order_id": str(order_id),
                "taker_authority": str(taker_authority),
                "timestamp": int(time.time() * 1000)
            }
            
            # Serialize to bytes
            message_bytes = json.dumps(cancel_message, separators=(',', ':')).encode('utf-8')
            
            # Sign the message
            signature = keypair.sign_message(message_bytes)
            
            # Create the envelope
            envelope = {
                "signed_message": message_bytes.hex(),  # Hex-encoded message
                "signature": bytes(signature).hex(),  # Hex-encoded signature
                "public_key": str(keypair.pubkey())
            }
            
            return envelope
            
        except Exception as e:
            raise Exception(f"Failed to create Swift cancel envelope: {e}")

    def _validate_swift_envelope(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Swift envelope structure and content with signature padding checks"""
        errors = []
        
        # Check required fields for Swift API format
        required_fields = ['takerAuthority', 'signature', 'orderMessage', 'marketIndex', 'marketType']
        for field in required_fields:
            if field not in envelope:
                errors.append(f"Missing required field: {field}")
        
        # Validate signature format and padding
        if 'signature' in envelope:
            signature = envelope['signature']
            if not isinstance(signature, str):
                errors.append("Signature must be a string")
            elif len(signature) % 4 != 0:
                errors.append(f"Signature has invalid base64 padding: {len(signature)} chars (must be multiple of 4)")
            else:
                # Try to decode the signature to verify it's valid base64
                try:
                    import base64
                    base64.b64decode(signature)
                except Exception as e:
                    errors.append(f"Invalid base64 signature: {e}")
        
        # Validate order message format
        if 'orderMessage' in envelope:
            try:
                import json
                order_msg = json.loads(envelope['orderMessage'])
                # Check for required order message fields
                required_order_fields = ['marketIndex', 'marketType', 'direction', 'baseAssetAmount', 'price']
                for field in required_order_fields:
                    if field not in order_msg:
                        errors.append(f"Missing order message field: {field}")
            except json.JSONDecodeError as e:
                errors.append(f"Invalid JSON in orderMessage: {e}")
        
        return {"valid": len(errors) == 0, "errors": errors}

    def _validate_envelope(self, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Swift envelope structure and content matching official format"""
        errors = []
        
        # Check required fields for Swift API envelope format (matching official spec)
        required_fields = ['message', 'signature', 'taker_authority', 'market_index', 'market_type']
        for field in required_fields:
            if field not in envelope:
                errors.append(f"Missing required field: {field}")
        
        # Validate signature format (must be valid base64)
        if 'signature' in envelope:
            try:
                import base64
                signature_bytes = base64.b64decode(envelope['signature'])
                if len(signature_bytes) != 64:  # Ed25519 signatures are 64 bytes
                    errors.append(f"Invalid signature length: {len(signature_bytes)} (expected 64)")
            except Exception as e:
                errors.append(f"Invalid signature format: {e}")
        
        # Validate message format (can be hex for DriftPy or JSON for fallback)
        if 'message' in envelope:
            message = envelope['message']
            try:
                # Try hex format first (DriftPy envelope)
                message_bytes = bytes.fromhex(message)
                if len(message_bytes) < 10:  # Minimum reasonable message size
                    errors.append(f"Message too short: {len(message_bytes)} bytes")
            except ValueError:
                # If hex fails, try JSON format (fallback envelope)
                try:
                    import json
                    json.loads(message)  # Validate it's valid JSON
                    if len(message) < 10:  # Minimum reasonable message size
                        errors.append(f"JSON message too short: {len(message)} chars")
                except json.JSONDecodeError as e:
                    errors.append(f"Invalid message format (neither hex nor JSON): {e}")
        
        # Validate taker_authority (must be valid base58 pubkey)
        if 'taker_authority' in envelope:
            try:
                from solders.pubkey import Pubkey
                Pubkey.from_string(envelope['taker_authority'])
            except Exception as e:
                errors.append(f"Invalid taker_authority format: {e}")
        
        # Validate market_index (must be integer)
        if 'market_index' in envelope and not isinstance(envelope['market_index'], int):
            errors.append("market_index must be an integer")
        
        # Validate market_type (must be string)
        if 'market_type' in envelope and not isinstance(envelope['market_type'], str):
            errors.append("market_type must be a string")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

class SwiftOrderProcessor:
    """Processes incoming Swift orders"""
    
    def __init__(self, drift_client, keypair: Keypair):
        self.drift_client = drift_client
        self.keypair = keypair
        self.stats = {
            "orders_processed": 0,
            "orders_accepted": 0,
            "orders_rejected": 0,
            "errors": 0
        }
    
    async def process_order(self, order_message: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming Swift order"""
        try:
            self.stats["orders_processed"] += 1
            
            # Extract order data
            order_data = order_message.get("data", {})
            side = order_data.get("side")
            price = order_data.get("price")
            size = order_data.get("size")
            
            if not all([side, price, size]):
                self.stats["orders_rejected"] += 1
                return {
                    "status": "rejected",
                    "reason": "Missing required order data"
                }
            
            # Validate order
            if not self._validate_order(order_data):
                self.stats["orders_rejected"] += 1
                return {
                    "status": "rejected",
                    "reason": "Order validation failed"
                }
            
            # Execute JIT trade
            result = await self._execute_jit_trade(order_data)
            
            if result["success"]:
                self.stats["orders_accepted"] += 1
                return {
                    "status": "success",
                    "message": f"JIT trade executed: {side} {size} @ {price}",
                    "trade_id": result.get("trade_id")
                }
            else:
                self.stats["orders_rejected"] += 1
                return {
                    "status": "rejected",
                    "reason": result.get("error", "Trade execution failed")
                }
                
        except Exception as e:
            self.stats["errors"] += 1
            return {
                "status": "error",
                "reason": str(e)
            }
    
    def _validate_order(self, order_data: Dict[str, Any]) -> bool:
        """Validate order data"""
        try:
            # Check required fields
            required_fields = ["side", "price", "size", "market_index"]
            for field in required_fields:
                if field not in order_data:
                    return False
            
            # Validate side
            if order_data["side"] not in ["buy", "sell"]:
                return False
            
            # Validate price and size
            if order_data["price"] <= 0 or order_data["size"] <= 0:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _execute_jit_trade(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute JIT trade against the order"""
        try:
            # This is a placeholder for actual JIT trade execution
            # In a real implementation, this would:
            # 1. Check if we have a matching order on the other side
            # 2. Execute the trade at the specified price
            # 3. Update our position and orders
            
            side = order_data["side"]
            price = order_data["price"]
            size = order_data["size"]
            
            # Simulate trade execution
            trade_id = f"JIT-{int(time.time() * 1000000) % 999999:06d}"
            
            # Log the trade
            print(f" JIT TRADE EXECUTED: {side.upper()} {size} @ {price} (ID: {trade_id})")
            
            return {
                "success": True,
                "trade_id": trade_id,
                "side": side,
                "price": price,
                "size": size
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self.stats.copy()


class SwiftMessageSerializer:
    """Serialize order parameters for Swift protocol"""

    @staticmethod
    def create_order_message(order_params: Dict[str, Any]) -> bytes:
        """Create a binary message matching Swift's SignedMsgOrderParamsMessage format"""
        import struct
        import hashlib

        # Create discriminator (first 8 bytes)
        discriminator = hashlib.sha256(b'global:SignedMsgOrderParamsMessage').digest()[:8]

        buffer = bytearray()
        buffer.extend(discriminator)

        # Add subAccountId (u16)
        buffer.extend(struct.pack('<H', order_params.get('subAccountId', 0)))

        # Add direction (1 byte: 0=long, 1=short)
        direction = 0 if order_params.get('direction', 'long') == 'long' else 1
        buffer.extend(struct.pack('<B', direction))

        # Add marketType (1 byte: 0=spot, 1=perp)
        buffer.extend(struct.pack('<B', 1))  # Always perp for Swift MM

        # Add marketIndex (u16)
        buffer.extend(struct.pack('<H', order_params.get('marketIndex', 0)))

        # Add baseAssetAmount (i64)
        base_amount = int(order_params.get('baseAssetAmount', 0))
        buffer.extend(struct.pack('<q', base_amount))

        # Add price (i64) - can be 0 for market orders
        price = int(order_params.get('price', 0))
        buffer.extend(struct.pack('<q', price))

        # Add orderType (1 byte: 0=market, 1=limit)
        buffer.extend(struct.pack('<B', 1))  # Limit order

        # Add userOrderId (u8)
        buffer.extend(struct.pack('<B', order_params.get('userOrderId', 0)))

        # Add reduceOnly (1 byte boolean)
        buffer.extend(struct.pack('<B', 1 if order_params.get('reduceOnly', False) else 0))

        # Add postOnly (1 byte: 0=none, 1=must_post_only, 2=try_post_only)
        buffer.extend(struct.pack('<B', 1))  # Must post only

        # Add immediateOrCancel (1 byte boolean)
        buffer.extend(struct.pack('<B', 0))

        # Add triggerPrice (i64) - 0 for non-trigger orders
        buffer.extend(struct.pack('<q', 0))

        # Add triggerCondition (1 byte: 0=above, 1=below, 2=triggered_above, 3=triggered_below)
        buffer.extend(struct.pack('<B', 0))

        # Add auctionDuration (u8)
        buffer.extend(struct.pack('<B', order_params.get('auctionDuration', 10)))

        # Add auctionStartPrice (i64)
        auction_start = int(order_params.get('auctionStartPrice', price))
        buffer.extend(struct.pack('<q', auction_start))

        # Add auctionEndPrice (i64)
        auction_end = int(order_params.get('auctionEndPrice', price))
        buffer.extend(struct.pack('<q', auction_end))

        # Add maxTs (i64) - 0 means no expiry
        buffer.extend(struct.pack('<q', order_params.get('maxTs', 0)))

        return bytes(buffer)