/**
 * Metrics collection for Hybrid Jitter Service
 */

import { 
  register, 
  Counter, 
  Gauge, 
  Histogram,
  collectDefaultMetrics 
} from 'prom-client';

import { 
  FillEvent, 
  JitterMode, 
  HybridJitterStrategy, 
  AllocationState,
  RegimeType 
} from './types.js';

export class HybridJitterMetrics {
  // Fill metrics
  private fillsTotal: Counter<string>;
  private fillVolumeTotal: Counter<string>;
  private fillPnlTotal: Counter<string>;
  
  // Performance metrics
  private winRate: Gauge<string>;
  private vwapImprovement: Histogram<string>;
  private latencyHistogram: Histogram<string>;
  
  // Allocation metrics
  private allocationRatio: Gauge<string>;
  private regimeGauge: Gauge<string>;
  private strategyGauge: Gauge<string>;
  
  // Order processing metrics
  private ordersReceived: Counter<string>;
  private ordersSkipped: Counter<string>;
  private ordersProcessed: Counter<string>;
  
  // System metrics
  private errorTotal: Counter<string>;
  private strategyToggles: Counter<string>;
  private emergencyHalts: Counter<string>;
  private hedgeCoordinations: Counter<string>;
  
  // Exposure tracking
  private currentExposure: Gauge<string>;
  private maxExposure: Gauge<string>;
  
  constructor() {
    // Enable default metrics
    collectDefaultMetrics({ prefix: 'hybrid_jitter_' });
    
    // Fill metrics
    this.fillsTotal = new Counter({
      name: 'hybrid_jitter_fills_total',
      help: 'Total number of fills by strategy',
      labelNames: ['mode', 'market', 'side', 'regime']
    });
    
    this.fillVolumeTotal = new Counter({
      name: 'hybrid_jitter_fill_volume_total',
      help: 'Total fill volume by strategy',
      labelNames: ['mode', 'market', 'side']
    });
    
    this.fillPnlTotal = new Counter({
      name: 'hybrid_jitter_fill_pnl_total',
      help: 'Total PnL from fills by strategy',
      labelNames: ['mode', 'market']
    });
    
    // Performance metrics
    this.winRate = new Gauge({
      name: 'hybrid_jitter_win_rate',
      help: 'Win rate by strategy',
      labelNames: ['mode']
    });
    
    this.vwapImprovement = new Histogram({
      name: 'hybrid_jitter_vwap_improvement_bps',
      help: 'VWAP improvement in basis points',
      labelNames: ['mode'],
      buckets: [-50, -20, -10, -5, -1, 0, 1, 5, 10, 20, 50]
    });
    
    this.latencyHistogram = new Histogram({
      name: 'hybrid_jitter_latency_seconds',
      help: 'Order processing latency',
      labelNames: ['mode', 'operation'],
      buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
    });
    
    // Allocation metrics
    this.allocationRatio = new Gauge({
      name: 'hybrid_jitter_allocation_ratio',
      help: 'Current allocation ratio by strategy',
      labelNames: ['mode', 'regime']
    });
    
    this.regimeGauge = new Gauge({
      name: 'hybrid_jitter_current_regime',
      help: 'Current market regime (encoded as number)',
      labelNames: ['regime']
    });
    
    this.strategyGauge = new Gauge({
      name: 'hybrid_jitter_current_strategy',
      help: 'Current active strategy (encoded as number)',
      labelNames: ['strategy']
    });
    
    // Order processing metrics
    this.ordersReceived = new Counter({
      name: 'hybrid_jitter_orders_received_total',
      help: 'Total orders received',
      labelNames: ['source', 'market']
    });
    
    this.ordersSkipped = new Counter({
      name: 'hybrid_jitter_orders_skipped_total',
      help: 'Total orders skipped by reason',
      labelNames: ['mode', 'reason']
    });
    
    this.ordersProcessed = new Counter({
      name: 'hybrid_jitter_orders_processed_total',
      help: 'Total orders successfully processed',
      labelNames: ['mode', 'market']
    });
    
    // System metrics
    this.errorTotal = new Counter({
      name: 'hybrid_jitter_errors_total',
      help: 'Total errors by type',
      labelNames: ['type', 'component']
    });
    
    this.strategyToggles = new Counter({
      name: 'hybrid_jitter_strategy_toggles_total',
      help: 'Total strategy toggle events',
      labelNames: ['from_strategy', 'to_strategy']
    });
    
    this.emergencyHalts = new Counter({
      name: 'hybrid_jitter_emergency_halts_total',
      help: 'Total emergency halt events',
      labelNames: ['type']
    });
    
    this.hedgeCoordinations = new Counter({
      name: 'hybrid_jitter_hedge_coordinations_total',
      help: 'Total hedge coordination events',
      labelNames: ['fill_source', 'urgency']
    });
    
    // Exposure tracking
    this.currentExposure = new Gauge({
      name: 'hybrid_jitter_current_exposure_usd',
      help: 'Current USD exposure by strategy',
      labelNames: ['mode']
    });
    
    this.maxExposure = new Gauge({
      name: 'hybrid_jitter_max_exposure_usd',
      help: 'Maximum allowed USD exposure',
      labelNames: ['mode']
    });
  }
  
  recordFill(fill: FillEvent): void {
    const { source, market, side, regime, size, pnl } = fill;
    
    this.fillsTotal.labels(source, market, side, regime).inc();
    this.fillVolumeTotal.labels(source, market, side).inc(size);
    
    if (pnl !== undefined) {
      this.fillPnlTotal.labels(source, market).inc(pnl);
    }
  }
  
  recordOrderReceived(source: 'swift' | 'auction', market: string): void {
    this.ordersReceived.labels(source, market).inc();
  }
  
  recordOrderSkipped(mode: JitterMode, reason: string): void {
    this.ordersSkipped.labels(mode, reason).inc();
  }
  
  recordOrderProcessed(mode: JitterMode, market: string): void {
    this.ordersProcessed.labels(mode, market).inc();
  }
  
  recordLatency(mode: JitterMode, operation: string, latencySeconds: number): void {
    this.latencyHistogram.labels(mode, operation).observe(latencySeconds);
  }
  
  recordVwapImprovement(mode: JitterMode, improvementBps: number): void {
    this.vwapImprovement.labels(mode).observe(improvementBps);
  }
  
  updateWinRate(mode: JitterMode, winRate: number): void {
    this.winRate.labels(mode).set(winRate);
  }
  
  recordAllocationUpdate(allocation: AllocationState): void {
    const { shotgunAllocation, sniperAllocation, regime } = allocation;
    
    this.allocationRatio.labels(JitterMode.SHOTGUN, regime).set(shotgunAllocation);
    this.allocationRatio.labels(JitterMode.SNIPER, regime).set(sniperAllocation);
    
    // Update regime gauge (encode regime as number for Prometheus)
    this.regimeGauge.labels(regime).set(this.encodeRegime(regime));
  }
  
  recordStrategyToggle(oldStrategy: HybridJitterStrategy, newStrategy: HybridJitterStrategy): void {
    this.strategyToggles.labels(oldStrategy, newStrategy).inc();
    this.strategyGauge.labels(newStrategy).set(this.encodeStrategy(newStrategy));
  }
  
  recordError(type: string, component: string = 'general'): void {
    this.errorTotal.labels(type, component).inc();
  }
  
  recordEmergencyHalt(): void {
    this.emergencyHalts.labels('activated').inc();
  }
  
  recordEmergencyResume(): void {
    this.emergencyHalts.labels('deactivated').inc();
  }
  
  recordHedgeCoordination(fillSource: JitterMode, urgency: string, hedgeRatio: number): void {
    this.hedgeCoordinations.labels(fillSource, urgency).inc();
  }
  
  updateCurrentExposure(mode: JitterMode, exposureUsd: number): void {
    this.currentExposure.labels(mode).set(exposureUsd);
  }
  
  updateMaxExposure(mode: JitterMode, maxExposureUsd: number): void {
    this.maxExposure.labels(mode).set(maxExposureUsd);
  }
  
  private encodeRegime(regime: RegimeType): number {
    const regimeMap: { [key in RegimeType]: number } = {
      [RegimeType.CALM]: 1,
      [RegimeType.NORMAL]: 2,
      [RegimeType.VOLATILE]: 3,
      [RegimeType.TRENDING]: 4,
      [RegimeType.CRASH]: 5
    };
    return regimeMap[regime] || 0;
  }
  
  private encodeStrategy(strategy: HybridJitterStrategy): number {
    const strategyMap: { [key in HybridJitterStrategy]: number } = {
      [HybridJitterStrategy.SHOTGUN_ONLY]: 1,
      [HybridJitterStrategy.SNIPER_ONLY]: 2,
      [HybridJitterStrategy.HYBRID]: 3,
      [HybridJitterStrategy.DISABLED]: 4,
      [HybridJitterStrategy.CUSTOM]: 5
    };
    return strategyMap[strategy] || 0;
  }
  
  async getMetrics(): Promise<string> {
    return register.metrics();
  }
  
  getRegistry() {
    return register;
  }
  
  reset(): void {
    register.clear();
  }
  
  // Utility methods for performance calculations
  calculatePerformanceMetrics(fills: FillEvent[]): {
    shotgunMetrics: any;
    sniperMetrics: any;
    combined: any;
  } {
    const shotgunFills = fills.filter(f => f.source === JitterMode.SHOTGUN);
    const sniperFills = fills.filter(f => f.source === JitterMode.SNIPER);
    
    const calculateMetrics = (fillsSubset: FillEvent[]) => {
      if (fillsSubset.length === 0) {
        return {
          totalFills: 0,
          totalVolume: 0,
          avgFillSize: 0,
          winRate: 0,
          totalPnl: 0,
          avgPnl: 0
        };
      }
      
      const totalVolume = fillsSubset.reduce((sum, f) => sum + f.size, 0);
      const fillsWithPnl = fillsSubset.filter(f => f.pnl !== undefined);
      const winningFills = fillsWithPnl.filter(f => f.pnl! > 0);
      const totalPnl = fillsWithPnl.reduce((sum, f) => sum + (f.pnl || 0), 0);
      
      return {
        totalFills: fillsSubset.length,
        totalVolume,
        avgFillSize: totalVolume / fillsSubset.length,
        winRate: fillsWithPnl.length > 0 ? winningFills.length / fillsWithPnl.length : 0,
        totalPnl,
        avgPnl: fillsWithPnl.length > 0 ? totalPnl / fillsWithPnl.length : 0
      };
    };
    
    return {
      shotgunMetrics: calculateMetrics(shotgunFills),
      sniperMetrics: calculateMetrics(sniperFills),
      combined: calculateMetrics(fills)
    };
  }
}
