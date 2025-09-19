/**
 * Configuration management for Hybrid Jitter Service
 */

import Joi from 'joi';
import { ShotgunConfig, SniperConfig, RegimeAllocationRules, RiskParameters } from './types.js';

export interface HybridJitterConfig {
  // Service configuration
  port: number;
  logLevel: string;
  
  // Drift configuration
  rpcUrl: string;
  driftEnv: 'devnet' | 'mainnet-beta';
  driftProgramId: string;
  jitProxyProgramId: string;
  makerKeypair: string; // JSON string of keypair bytes
  
  // Market configuration
  marketIndexes: number[];
  maxTotalExposureUsd: number;
  
  // Strategy configuration
  shotgun: ShotgunConfig;
  sniper: SniperConfig;
  regimeAllocation: RegimeAllocationRules;
  riskParameters: RiskParameters;
  
  // Feature flags
  enableShotgun: boolean;
  enableSniper: boolean;
  enableHybrid: boolean;
  enableCrashSentinel: boolean;
  enableHedgeCoordination: boolean;
  
  // Metrics configuration
  enableMetrics: boolean;
  metricsPort: number;
}

const configSchema = Joi.object<HybridJitterConfig>({
  // Service configuration
  port: Joi.number().integer().min(1000).max(65535).default(8788),
  logLevel: Joi.string().valid('error', 'warn', 'info', 'debug', 'trace').default('info'),
  
  // Drift configuration
  rpcUrl: Joi.string().uri().required(),
  driftEnv: Joi.string().valid('devnet', 'mainnet-beta').required(),
  driftProgramId: Joi.string().required(),
  jitProxyProgramId: Joi.string().required(),
  makerKeypair: Joi.string().required(),
  
  // Market configuration
  marketIndexes: Joi.array().items(Joi.number().integer().min(0)).min(1).required(),
  maxTotalExposureUsd: Joi.number().positive().default(2500),
  
  // Strategy configuration
  shotgun: Joi.object({
    enabled: Joi.boolean().default(true),
    sizeClip: Joi.number().positive().default(0.25),
    maxSizeClip: Joi.number().positive().default(0.5),
    minSizeThreshold: Joi.number().positive().default(0.01),
    maxExposureUsd: Joi.number().positive().default(500),
    maxPositionSol: Joi.number().positive().default(10),
    participationRate: Joi.number().min(0).max(1).default(0.95),
    skipSanitizedOrders: Joi.boolean().default(false),
    toxicityThreshold: Joi.number().min(0).max(1).default(0.8),
    maxSpreadBps: Joi.number().positive().default(50),
    minProfitBps: Joi.number().positive().default(0.5),
    maxLatencyMs: Joi.number().positive().default(150),
    cancelOnFill: Joi.boolean().default(true)
  }).required(),
  
  sniper: Joi.object({
    enabled: Joi.boolean().default(true),
    sizeClip: Joi.number().positive().default(2.5),
    maxSizeClip: Joi.number().positive().default(5.0),
    minSizeThreshold: Joi.number().positive().default(1.0),
    maxExposureUsd: Joi.number().positive().default(2000),
    maxPositionSol: Joi.number().positive().default(25),
    participationRate: Joi.number().min(0).max(1).default(0.3),
    skipSanitizedOrders: Joi.boolean().default(true),
    minOrderSizeSol: Joi.number().positive().default(5.0),
    maxOrderSizeSol: Joi.number().positive().default(100.0),
    toxicityThreshold: Joi.number().min(0).max(1).default(0.3),
    maxSpreadBps: Joi.number().positive().default(25),
    minProfitBps: Joi.number().positive().default(2.0),
    obiThreshold: Joi.number().min(0).max(1).default(0.6),
    depthAnalysis: Joi.boolean().default(true),
    spoofDetection: Joi.boolean().default(true),
    requireRegimeAlignment: Joi.boolean().default(true),
    trendAlignmentThreshold: Joi.number().min(0).max(1).default(0.7),
    maxLatencyMs: Joi.number().positive().default(100),
    cancelOnFill: Joi.boolean().default(false),
    minLifetimeMs: Joi.number().positive().default(500),
    useAuctionParams: Joi.boolean().default(true),
    auctionStartBufferSlots: Joi.number().integer().min(0).default(5),
    auctionEndBufferSlots: Joi.number().integer().min(0).default(10),
    minQualityScore: Joi.number().min(0).max(1).default(0.7)
  }).required(),
  
  regimeAllocation: Joi.object({
    calm: Joi.object({
      shotgunAllocation: Joi.number().min(0).max(1).default(0.8),
      sniperAllocation: Joi.number().min(0).max(1).default(0.2)
    }).required(),
    normal: Joi.object({
      shotgunAllocation: Joi.number().min(0).max(1).default(0.6),
      sniperAllocation: Joi.number().min(0).max(1).default(0.4)
    }).required(),
    volatile: Joi.object({
      shotgunAllocation: Joi.number().min(0).max(1).default(0.4),
      sniperAllocation: Joi.number().min(0).max(1).default(0.6)
    }).required(),
    trending: Joi.object({
      shotgunAllocation: Joi.number().min(0).max(1).default(0.3),
      sniperAllocation: Joi.number().min(0).max(1).default(0.7)
    }).required(),
    crash: Joi.object({
      shotgunAllocation: Joi.number().min(0).max(1).default(0.0),
      sniperAllocation: Joi.number().min(0).max(1).default(0.0)
    }).required()
  }).required(),
  
  riskParameters: Joi.object({
    maxTotalExposureUsd: Joi.number().positive().default(2500),
    exposureScalingFactor: Joi.number().min(0).max(1).default(0.8),
    emergencyHaltThreshold: Joi.number().positive().default(3.0),
    volatilityThreshold: Joi.number().positive().default(0.4),
    trendThreshold: Joi.number().positive().default(0.6)
  }).required(),
  
  // Feature flags
  enableShotgun: Joi.boolean().default(true),
  enableSniper: Joi.boolean().default(true),
  enableHybrid: Joi.boolean().default(true),
  enableCrashSentinel: Joi.boolean().default(true),
  enableHedgeCoordination: Joi.boolean().default(true),
  
  // Metrics configuration
  enableMetrics: Joi.boolean().default(true),
  metricsPort: Joi.number().integer().min(1000).max(65535).default(9090)
});

export function loadConfig(): HybridJitterConfig {
  const config: Partial<HybridJitterConfig> = {
    // Service configuration
    port: parseInt(process.env.PORT || '8788'),
    logLevel: process.env.LOG_LEVEL || 'info',
    
    // Drift configuration
    rpcUrl: process.env.RPC_URL || '',
    driftEnv: (process.env.DRIFT_ENV as 'devnet' | 'mainnet-beta') || 'devnet',
    driftProgramId: process.env.DRIFT_PROGRAM_ID || 'dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH',
    jitProxyProgramId: process.env.JIT_PROXY_PROGRAM_ID || '',
    makerKeypair: process.env.MAKER_KEYPAIR || '',
    
    // Market configuration
    marketIndexes: process.env.MARKET_INDEXES ? 
      JSON.parse(process.env.MARKET_INDEXES) : [0, 1, 2],
    maxTotalExposureUsd: parseFloat(process.env.MAX_TOTAL_EXPOSURE_USD || '2500'),
    
    // Strategy configuration (defaults will be applied by schema)
    shotgun: {
      enabled: process.env.SHOTGUN_ENABLED !== 'false',
      sizeClip: parseFloat(process.env.SHOTGUN_SIZE_CLIP || '0.25'),
      maxSizeClip: parseFloat(process.env.SHOTGUN_MAX_SIZE_CLIP || '0.5'),
      minSizeThreshold: parseFloat(process.env.SHOTGUN_MIN_SIZE || '0.01'),
      maxExposureUsd: parseFloat(process.env.SHOTGUN_MAX_EXPOSURE || '500'),
      maxPositionSol: parseFloat(process.env.SHOTGUN_MAX_POSITION || '10'),
      participationRate: parseFloat(process.env.SHOTGUN_PARTICIPATION_RATE || '0.95'),
      skipSanitizedOrders: process.env.SHOTGUN_SKIP_SANITIZED === 'true',
      toxicityThreshold: parseFloat(process.env.SHOTGUN_TOXICITY_THRESHOLD || '0.8'),
      maxSpreadBps: parseFloat(process.env.SHOTGUN_MAX_SPREAD_BPS || '50'),
      minProfitBps: parseFloat(process.env.SHOTGUN_MIN_PROFIT_BPS || '0.5'),
      maxLatencyMs: parseInt(process.env.SHOTGUN_MAX_LATENCY_MS || '150'),
      cancelOnFill: process.env.SHOTGUN_CANCEL_ON_FILL !== 'false'
    },
    
    sniper: {
      enabled: process.env.SNIPER_ENABLED !== 'false',
      sizeClip: parseFloat(process.env.SNIPER_SIZE_CLIP || '2.5'),
      maxSizeClip: parseFloat(process.env.SNIPER_MAX_SIZE_CLIP || '5.0'),
      minSizeThreshold: parseFloat(process.env.SNIPER_MIN_SIZE || '1.0'),
      maxExposureUsd: parseFloat(process.env.SNIPER_MAX_EXPOSURE || '2000'),
      maxPositionSol: parseFloat(process.env.SNIPER_MAX_POSITION || '25'),
      participationRate: parseFloat(process.env.SNIPER_PARTICIPATION_RATE || '0.3'),
      skipSanitizedOrders: process.env.SNIPER_SKIP_SANITIZED !== 'false',
      minOrderSizeSol: parseFloat(process.env.SNIPER_MIN_ORDER_SIZE || '5.0'),
      maxOrderSizeSol: parseFloat(process.env.SNIPER_MAX_ORDER_SIZE || '100.0'),
      toxicityThreshold: parseFloat(process.env.SNIPER_TOXICITY_THRESHOLD || '0.3'),
      maxSpreadBps: parseFloat(process.env.SNIPER_MAX_SPREAD_BPS || '25'),
      minProfitBps: parseFloat(process.env.SNIPER_MIN_PROFIT_BPS || '2.0'),
      obiThreshold: parseFloat(process.env.SNIPER_OBI_THRESHOLD || '0.6'),
      depthAnalysis: process.env.SNIPER_DEPTH_ANALYSIS !== 'false',
      spoofDetection: process.env.SNIPER_SPOOF_DETECTION !== 'false',
      requireRegimeAlignment: process.env.SNIPER_REQUIRE_REGIME_ALIGNMENT !== 'false',
      trendAlignmentThreshold: parseFloat(process.env.SNIPER_TREND_ALIGNMENT || '0.7'),
      maxLatencyMs: parseInt(process.env.SNIPER_MAX_LATENCY_MS || '100'),
      cancelOnFill: process.env.SNIPER_CANCEL_ON_FILL === 'true',
      minLifetimeMs: parseInt(process.env.SNIPER_MIN_LIFETIME_MS || '500'),
      useAuctionParams: process.env.SNIPER_USE_AUCTION_PARAMS !== 'false',
      auctionStartBufferSlots: parseInt(process.env.SNIPER_AUCTION_START_BUFFER || '5'),
      auctionEndBufferSlots: parseInt(process.env.SNIPER_AUCTION_END_BUFFER || '10'),
      minQualityScore: parseFloat(process.env.SNIPER_MIN_QUALITY_SCORE || '0.7')
    },
    
    regimeAllocation: {
      calm: {
        shotgunAllocation: parseFloat(process.env.CALM_SHOTGUN_ALLOCATION || '0.8'),
        sniperAllocation: parseFloat(process.env.CALM_SNIPER_ALLOCATION || '0.2')
      },
      normal: {
        shotgunAllocation: parseFloat(process.env.NORMAL_SHOTGUN_ALLOCATION || '0.6'),
        sniperAllocation: parseFloat(process.env.NORMAL_SNIPER_ALLOCATION || '0.4')
      },
      volatile: {
        shotgunAllocation: parseFloat(process.env.VOLATILE_SHOTGUN_ALLOCATION || '0.4'),
        sniperAllocation: parseFloat(process.env.VOLATILE_SNIPER_ALLOCATION || '0.6')
      },
      trending: {
        shotgunAllocation: parseFloat(process.env.TRENDING_SHOTGUN_ALLOCATION || '0.3'),
        sniperAllocation: parseFloat(process.env.TRENDING_SNIPER_ALLOCATION || '0.7')
      },
      crash: {
        shotgunAllocation: parseFloat(process.env.CRASH_SHOTGUN_ALLOCATION || '0.0'),
        sniperAllocation: parseFloat(process.env.CRASH_SNIPER_ALLOCATION || '0.0')
      }
    },
    
    riskParameters: {
      maxTotalExposureUsd: parseFloat(process.env.MAX_TOTAL_EXPOSURE_USD || '2500'),
      exposureScalingFactor: parseFloat(process.env.EXPOSURE_SCALING_FACTOR || '0.8'),
      emergencyHaltThreshold: parseFloat(process.env.EMERGENCY_HALT_THRESHOLD || '3.0'),
      volatilityThreshold: parseFloat(process.env.VOLATILITY_THRESHOLD || '0.4'),
      trendThreshold: parseFloat(process.env.TREND_THRESHOLD || '0.6')
    },
    
    // Feature flags
    enableShotgun: process.env.ENABLE_SHOTGUN !== 'false',
    enableSniper: process.env.ENABLE_SNIPER !== 'false',
    enableHybrid: process.env.ENABLE_HYBRID !== 'false',
    enableCrashSentinel: process.env.ENABLE_CRASH_SENTINEL !== 'false',
    enableHedgeCoordination: process.env.ENABLE_HEDGE_COORDINATION !== 'false',
    
    // Metrics configuration
    enableMetrics: process.env.ENABLE_METRICS !== 'false',
    metricsPort: parseInt(process.env.METRICS_PORT || '9090')
  };

  return config as HybridJitterConfig;
}

export function validateConfig(config: HybridJitterConfig): void {
  const { error } = configSchema.validate(config, { 
    abortEarly: false,
    allowUnknown: false 
  });
  
  if (error) {
    const errorMessages = error.details.map(detail => detail.message).join('; ');
    throw new Error(`Configuration validation failed: ${errorMessages}`);
  }
  
  // Additional custom validations
  if (!config.rpcUrl) {
    throw new Error('RPC_URL environment variable is required');
  }
  
  if (!config.makerKeypair) {
    throw new Error('MAKER_KEYPAIR environment variable is required');
  }
  
  if (!config.jitProxyProgramId) {
    throw new Error('JIT_PROXY_PROGRAM_ID environment variable is required');
  }
  
  // Validate allocation totals
  Object.entries(config.regimeAllocation).forEach(([regime, allocation]) => {
    const total = allocation.shotgunAllocation + allocation.sniperAllocation;
    if (total > 1.0) {
      throw new Error(`Allocation for regime ${regime} exceeds 100%: ${total * 100}%`);
    }
  });
}
