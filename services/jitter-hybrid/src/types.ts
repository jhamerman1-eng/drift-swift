/**
 * Type definitions for Hybrid Jitter Service
 */

export enum HybridJitterStrategy {
  SHOTGUN_ONLY = "shotgun_only",
  SNIPER_ONLY = "sniper_only", 
  HYBRID = "hybrid",
  DISABLED = "disabled",
  CUSTOM = "custom"
}

export enum RegimeType {
  CALM = "calm",
  NORMAL = "normal",
  VOLATILE = "volatile",
  TRENDING = "trending",
  CRASH = "crash"
}

export enum JitterMode {
  SHOTGUN = "shotgun",
  SNIPER = "sniper"
}

export interface FillEvent {
  source: JitterMode;
  size: number;
  price: number;
  side: 'buy' | 'sell';
  market: string;
  timestamp: number;
  orderId: string;
  regime: RegimeType;
  qualityScore?: number;
  pnl?: number;
}

export interface AllocationState {
  shotgunAllocation: number;
  sniperAllocation: number;
  regime: RegimeType;
  lastUpdate: number;
  totalExposure: number;
}

export interface HealthStatus {
  healthy: boolean;
  timestamp: number;
  services: {
    driftClient: boolean;
    userMap: boolean;
    jitProxyClient: boolean;
    swiftSubscriber: boolean;
    auctionSubscriber: boolean;
    slotSubscriber: boolean;
    jitterShotgun: boolean;
    jitterSniper: boolean;
  };
  strategy: HybridJitterStrategy;
  regime: RegimeType;
  allocation: AllocationState;
  crashSentinelActive: boolean;
}

export interface MarketData {
  volatility: number;
  trend: number;
  price: number;
  spread: number;
  volume: number;
  timestamp: number;
}

export interface QualityScoreFactors {
  sizeWeight: number;
  toxicityWeight: number;
  obiWeight: number;
  regimeWeight: number;
}

export interface HedgeCoordinationEvent {
  fillSource: JitterMode;
  urgency: 'fast' | 'opportunistic';
  hedgeRatio: number;
  timestamp: number;
  fillId: string;
}

export interface PerformanceMetrics {
  totalFills: number;
  shotgunFills: number;
  sniperFills: number;
  totalVolume: number;
  avgFillSize: number;
  winRate: number;
  pnl: number;
  vwapImprovement: number;
}

export interface RegimeAllocationRules {
  calm: {
    shotgunAllocation: number;
    sniperAllocation: number;
  };
  normal: {
    shotgunAllocation: number;
    sniperAllocation: number;
  };
  volatile: {
    shotgunAllocation: number;
    sniperAllocation: number;
  };
  trending: {
    shotgunAllocation: number;
    sniperAllocation: number;
  };
  crash: {
    shotgunAllocation: number;
    sniperAllocation: number;
  };
}

export interface RiskParameters {
  maxTotalExposureUsd: number;
  exposureScalingFactor: number;
  emergencyHaltThreshold: number;
  volatilityThreshold: number;
  trendThreshold: number;
}

export interface ShotgunConfig {
  enabled: boolean;
  sizeClip: number;
  maxSizeClip: number;
  minSizeThreshold: number;
  maxExposureUsd: number;
  maxPositionSol: number;
  participationRate: number;
  skipSanitizedOrders: boolean;
  toxicityThreshold: number;
  maxSpreadBps: number;
  minProfitBps: number;
  maxLatencyMs: number;
  cancelOnFill: boolean;
}

export interface SniperConfig {
  enabled: boolean;
  sizeClip: number;
  maxSizeClip: number;
  minSizeThreshold: number;
  maxExposureUsd: number;
  maxPositionSol: number;
  participationRate: number;
  skipSanitizedOrders: boolean;
  minOrderSizeSol: number;
  maxOrderSizeSol: number;
  toxicityThreshold: number;
  maxSpreadBps: number;
  minProfitBps: number;
  obiThreshold: number;
  depthAnalysis: boolean;
  spoofDetection: boolean;
  requireRegimeAlignment: boolean;
  trendAlignmentThreshold: number;
  maxLatencyMs: number;
  cancelOnFill: boolean;
  minLifetimeMs: number;
  useAuctionParams: boolean;
  auctionStartBufferSlots: number;
  auctionEndBufferSlots: number;
  minQualityScore: number;
}

export interface ErrorEvent {
  type: string;
  message: string;
  timestamp: number;
  context?: any;
}

export interface StrategyToggleEvent {
  oldStrategy: HybridJitterStrategy;
  newStrategy: HybridJitterStrategy;
  timestamp: number;
  reason?: string;
}
