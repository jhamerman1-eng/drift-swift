/**
 * Jitter Control Endpoint for Swift MM Sidecar
 * 
 * This extends the existing Swift MM sidecar with a /control/jitter endpoint
 * that accepts live configuration updates from the Python HybridJitter system.
 */

import { Request, Response } from 'express';
import pino from 'pino';

const logger = pino({ name: 'jitter-control' });

// Configuration state
interface JitterConfig {
  allocation: {
    shotgun_weight: number;
    sniper_weight: number;
  };
  shotgun: {
    enabled: boolean;
    markets: string[];
    clip_size: number;
    min_notional_usd: number;
    toxicity_max: number;
    priority_fee_micro_lamports: number;
    compute_unit_limit: number;
    max_open_exposure_usd: number;
    auction: {
      use: boolean;
      duration_ms: number;
      max_width_bps: number;
    };
  };
  sniper: {
    enabled: boolean;
    markets: string[];
    clip_size: number;
    min_notional_usd: number;
    toxicity_max: number;
    direction_filter: string;
    priority_fee_micro_lamports: number;
    compute_unit_limit: number;
    max_open_exposure_usd: number;
    auction: {
      use: boolean;
      duration_ms: number;
      max_width_bps: number;
    };
  };
  metadata?: {
    timestamp: number;
    regime: string;
    attribution_enabled: boolean;
  };
}

// Global configuration state
let currentJitterConfig: JitterConfig | null = null;
let lastConfigUpdate = 0;

/**
 * POST /control/jitter
 * 
 * Accepts jitter configuration from Python HybridJitter system.
 * This is control-plane only - not latency critical.
 */
export function handleJitterControl(req: Request, res: Response): void {
  try {
    const config: JitterConfig = req.body;
    
    // Validate required fields
    if (!config.allocation || !config.shotgun || !config.sniper) {
      return res.status(400).json({
        error: 'Missing required fields: allocation, shotgun, sniper'
      });
    }
    
    // Validate allocation weights
    const { shotgun_weight, sniper_weight } = config.allocation;
    if (typeof shotgun_weight !== 'number' || typeof sniper_weight !== 'number') {
      return res.status(400).json({
        error: 'Invalid allocation weights - must be numbers'
      });
    }
    
    // Store configuration
    currentJitterConfig = config;
    lastConfigUpdate = Date.now();
    
    logger.info('📊 Jitter configuration updated:', {
      regime: config.metadata?.regime || 'unknown',
      shotgun_weight: shotgun_weight.toFixed(1),
      sniper_weight: sniper_weight.toFixed(1),
      shotgun_enabled: config.shotgun.enabled,
      sniper_enabled: config.sniper.enabled,
      shotgun_clip_size: config.shotgun.clip_size,
      sniper_clip_size: config.sniper.clip_size
    });
    
    // Success response
    res.status(200).json({
      status: 'success',
      message: 'Jitter configuration updated',
      timestamp: lastConfigUpdate,
      config_summary: {
        regime: config.metadata?.regime,
        shotgun_weight,
        sniper_weight,
        shotgun_enabled: config.shotgun.enabled,
        sniper_enabled: config.sniper.enabled
      }
    });
    
  } catch (error) {
    logger.error('❌ Failed to update jitter configuration:', error);
    res.status(500).json({
      error: 'Internal server error',
      message: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}

/**
 * GET /control/jitter
 * 
 * Returns current jitter configuration for debugging.
 */
export function getJitterConfig(req: Request, res: Response): void {
  try {
    if (!currentJitterConfig) {
      return res.status(404).json({
        error: 'No jitter configuration set',
        last_update: lastConfigUpdate
      });
    }
    
    res.status(200).json({
      status: 'success',
      config: currentJitterConfig,
      last_update: lastConfigUpdate,
      age_seconds: (Date.now() - lastConfigUpdate) / 1000
    });
    
  } catch (error) {
    logger.error('❌ Failed to get jitter configuration:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
}

/**
 * Get current jitter configuration for use in order processing.
 * This is called by the actual order processing logic.
 */
export function getCurrentJitterConfig(): JitterConfig | null {
  return currentJitterConfig;
}

/**
 * Check if shotgun strategy should process an order.
 */
export function shouldProcessShotgun(orderData: any): boolean {
  if (!currentJitterConfig?.shotgun.enabled) {
    return false;
  }
  
  const config = currentJitterConfig.shotgun;
  
  // Market filter
  if (!config.markets.includes(orderData.market)) {
    return false;
  }
  
  // Notional filter
  const notional = orderData.size * orderData.price;
  if (notional < config.min_notional_usd) {
    return false;
  }
  
  // Toxicity filter
  if (orderData.toxicity_score > config.toxicity_max) {
    return false;
  }
  
  // Use allocation weight to determine participation
  const participation_chance = currentJitterConfig.allocation.shotgun_weight;
  return Math.random() < participation_chance;
}

/**
 * Check if sniper strategy should process an order.
 */
export function shouldProcessSniper(orderData: any): boolean {
  if (!currentJitterConfig?.sniper.enabled) {
    return false;
  }
  
  const config = currentJitterConfig.sniper;
  
  // Market filter
  if (!config.markets.includes(orderData.market)) {
    return false;
  }
  
  // Notional filter
  const notional = orderData.size * orderData.price;
  if (notional < config.min_notional_usd) {
    return false;
  }
  
  // Toxicity filter (stricter for sniper)
  if (orderData.toxicity_score > config.toxicity_max) {
    return false;
  }
  
  // Direction filter
  if (config.direction_filter === 'with_regime') {
    // TODO: Implement regime direction checking
  } else if (config.direction_filter === 'against_regime') {
    // TODO: Implement counter-regime checking
  }
  
  // Use allocation weight to determine participation
  const participation_chance = currentJitterConfig.allocation.sniper_weight;
  return Math.random() < participation_chance;
}

/**
 * Get clip size for a strategy.
 */
export function getClipSize(strategy: 'shotgun' | 'sniper'): number {
  if (!currentJitterConfig) {
    return strategy === 'shotgun' ? 0.25 : 2.0; // Defaults
  }
  
  return currentJitterConfig[strategy].clip_size;
}

/**
 * Get auction configuration for a strategy.
 */
export function getAuctionConfig(strategy: 'shotgun' | 'sniper') {
  if (!currentJitterConfig) {
    return { use: true, duration_ms: 150, max_width_bps: 8 }; // Defaults
  }
  
  return currentJitterConfig[strategy].auction;
}

/**
 * Health check for jitter control system.
 */
export function getJitterHealth() {
  return {
    config_set: currentJitterConfig !== null,
    last_update: lastConfigUpdate,
    age_seconds: lastConfigUpdate > 0 ? (Date.now() - lastConfigUpdate) / 1000 : null,
    shotgun_enabled: currentJitterConfig?.shotgun.enabled || false,
    sniper_enabled: currentJitterConfig?.sniper.enabled || false,
    current_regime: currentJitterConfig?.metadata?.regime || 'unknown'
  };
}




