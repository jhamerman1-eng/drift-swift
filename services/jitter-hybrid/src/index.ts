/**
 * Hybrid Jitter Service - Official Drift SDK Integration
 * 
 * Integrates official Drift SDK JitterShotgun and JitterSniper with our existing
 * custom JIT system, providing regime-driven allocation and comprehensive attribution.
 * 
 * Features:
 * - JitterShotgun for broad volume capture (small clips ~0.25 SOL)
 * - JitterSniper for selective high-quality fills (larger clips 2-5 SOL)
 * - Regime-driven dynamic allocation
 * - Unified risk management and crash sentinel integration
 * - Comprehensive metrics and attribution
 * - Toggle mechanism between strategies
 */

import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import pino from "pino";
import { Server } from "http";

import {
  DriftClient,
  UserMap,
  SwiftOrderSubscriber,
  AuctionSubscriber,
  SlotSubscriber,
  JitterShotgun,
  JitterSniper,
  JitProxyClient,
  getUserAccountPublicKey,
  isSignedMsgOrder,
  MarketType,
  PRICE_PRECISION,
  BASE_PRECISION,
  PositionDirection,
  OrderType
} from "@drift-labs/sdk";

import { Connection, Keypair, PublicKey } from "@solana/web3.js";

import { loadConfig, validateConfig, HybridJitterConfig } from "./config.js";
import { HybridJitterMetrics } from "./metrics.js";
import { 
  HybridJitterStrategy, 
  RegimeType, 
  FillEvent, 
  AllocationState,
  JitterMode,
  HealthStatus 
} from "./types.js";

// Initialize configuration and logger
const config = loadConfig();
validateConfig(config);

const logger = pino({
  level: config.logLevel,
  transport: {
    target: "pino-pretty",
    options: { colorize: true }
  }
});

class HybridJitterService {
  private app: express.Application;
  private server?: Server;
  private metrics: HybridJitterMetrics;
  
  // Drift SDK components
  private connection: Connection;
  private driftClient?: DriftClient;
  private userMap?: UserMap;
  private jitProxyClient?: JitProxyClient;
  
  // Subscribers
  private swiftOrderSubscriber?: SwiftOrderSubscriber;
  private auctionSubscriber?: AuctionSubscriber;
  private slotSubscriber?: SlotSubscriber;
  
  // Jitter instances
  private jitterShotgun?: JitterShotgun;
  private jitterSniper?: JitterSniper;
  
  // State management
  private currentStrategy: HybridJitterStrategy = HybridJitterStrategy.HYBRID;
  private currentRegime: RegimeType = RegimeType.NORMAL;
  private allocationState: AllocationState = {
    shotgunAllocation: 0.6,
    sniperAllocation: 0.4,
    regime: RegimeType.NORMAL,
    lastUpdate: Date.now(),
    totalExposure: 0
  };
  
  private fills: FillEvent[] = [];
  private isRunning = false;
  private crashSentinelActive = false;

  constructor() {
    this.app = express();
    this.metrics = new HybridJitterMetrics();
    this.connection = new Connection(config.rpcUrl, 'confirmed');
    
    this.setupMiddleware();
    this.setupRoutes();
  }

  private setupMiddleware(): void {
    this.app.use(helmet());
    this.app.use(cors());
    this.app.use(express.json({ limit: '10mb' }));
    
    // Rate limiting
    const limiter = rateLimit({
      windowMs: 60 * 1000, // 1 minute
      max: 1000, // Limit each IP to 1000 requests per windowMs
      message: 'Too many requests from this IP'
    });
    this.app.use(limiter);
  }

  private setupRoutes(): void {
    // Health check
    this.app.get('/health', (req, res) => {
      const health = this.getHealthStatus();
      res.status(health.healthy ? 200 : 503).json(health);
    });

    // Metrics endpoint
    this.app.get('/metrics', async (req, res) => {
      try {
        const metrics = await this.metrics.getMetrics();
        res.set('Content-Type', 'text/plain');
        res.send(metrics);
      } catch (error) {
        logger.error('Failed to generate metrics', error);
        res.status(500).json({ error: 'Failed to generate metrics' });
      }
    });

    // Strategy control
    this.app.post('/strategy/toggle', (req, res) => {
      try {
        const { strategy } = req.body;
        if (!Object.values(HybridJitterStrategy).includes(strategy)) {
          return res.status(400).json({ error: 'Invalid strategy' });
        }
        
        const oldStrategy = this.currentStrategy;
        this.currentStrategy = strategy;
        
        logger.info(`Strategy toggled: ${oldStrategy} -> ${strategy}`);
        this.metrics.recordStrategyToggle(oldStrategy, strategy);
        
        res.json({ 
          success: true, 
          oldStrategy, 
          newStrategy: strategy,
          timestamp: Date.now()
        });
      } catch (error) {
        logger.error('Failed to toggle strategy', error);
        res.status(500).json({ error: 'Failed to toggle strategy' });
      }
    });

    // Performance summary
    this.app.get('/performance', (req, res) => {
      try {
        const summary = this.getPerformanceSummary();
        res.json(summary);
      } catch (error) {
        logger.error('Failed to get performance summary', error);
        res.status(500).json({ error: 'Failed to get performance summary' });
      }
    });

    // Allocation status
    this.app.get('/allocation', (req, res) => {
      res.json(this.allocationState);
    });

    // Force allocation update
    this.app.post('/allocation/update', async (req, res) => {
      try {
        await this.updateAllocation();
        res.json({ 
          success: true, 
          allocation: this.allocationState,
          timestamp: Date.now()
        });
      } catch (error) {
        logger.error('Failed to update allocation', error);
        res.status(500).json({ error: 'Failed to update allocation' });
      }
    });

    // Emergency controls
    this.app.post('/emergency/halt', (req, res) => {
      try {
        this.emergencyHalt();
        res.json({ success: true, message: 'Emergency halt activated' });
      } catch (error) {
        logger.error('Failed to execute emergency halt', error);
        res.status(500).json({ error: 'Failed to execute emergency halt' });
      }
    });

    this.app.post('/emergency/resume', (req, res) => {
      try {
        this.emergencyResume();
        res.json({ success: true, message: 'Emergency halt deactivated' });
      } catch (error) {
        logger.error('Failed to resume from emergency halt', error);
        res.status(500).json({ error: 'Failed to resume from emergency halt' });
      }
    });
  }

  async initialize(): Promise<void> {
    logger.info('🚀 Initializing Hybrid Jitter Service...');

    try {
      // Initialize Drift client
      const keypair = Keypair.fromSecretKey(
        new Uint8Array(JSON.parse(config.makerKeypair))
      );

      this.driftClient = new DriftClient({
        connection: this.connection,
        wallet: { publicKey: keypair.publicKey, signTransaction: async (tx) => tx, signAllTransactions: async (txs) => txs },
        programID: new PublicKey(config.driftProgramId),
        env: config.driftEnv as any,
      });

      await this.driftClient.subscribe();
      logger.info('✅ DriftClient initialized and subscribed');

      // Initialize UserMap
      this.userMap = new UserMap({
        driftClient: this.driftClient,
        connection: this.connection,
        commitmentConfig: { commitment: 'confirmed' }
      });
      await this.userMap.subscribe();
      logger.info('✅ UserMap initialized and subscribed');

      // Initialize JitProxyClient
      this.jitProxyClient = new JitProxyClient({
        driftClient: this.driftClient,
        programId: new PublicKey(config.jitProxyProgramId),
      });
      logger.info('✅ JitProxyClient initialized');

      // Initialize subscribers
      await this.initializeSubscribers();

      // Initialize Jitter instances
      await this.initializeJitters();

      this.isRunning = true;
      logger.info('✅ Hybrid Jitter Service fully initialized');

    } catch (error) {
      logger.error('❌ Failed to initialize Hybrid Jitter Service', error);
      throw error;
    }
  }

  private async initializeSubscribers(): Promise<void> {
    if (!this.driftClient || !this.userMap) {
      throw new Error('DriftClient and UserMap must be initialized first');
    }

    // Initialize SwiftOrderSubscriber
    this.swiftOrderSubscriber = new SwiftOrderSubscriber({
      driftEnv: config.driftEnv as any,
      marketIndexes: config.marketIndexes,
      keypair: Keypair.fromSecretKey(new Uint8Array(JSON.parse(config.makerKeypair))),
      driftClient: this.driftClient,
      userAccountGetter: this.userMap,
    });

    // Initialize AuctionSubscriber
    this.auctionSubscriber = new AuctionSubscriber({
      driftClient: this.driftClient,
      connection: this.connection,
    });

    // Initialize SlotSubscriber
    this.slotSubscriber = new SlotSubscriber(this.connection, {
      resubTimeoutMs: 30_000
    });

    await this.swiftOrderSubscriber.subscribe();
    await this.auctionSubscriber.subscribe();
    await this.slotSubscriber.subscribe();

    logger.info('✅ All subscribers initialized and subscribed');
  }

  private async initializeJitters(): Promise<void> {
    if (!this.driftClient || !this.jitProxyClient || !this.swiftOrderSubscriber || 
        !this.auctionSubscriber || !this.slotSubscriber) {
      throw new Error('All required components must be initialized first');
    }

    // Initialize JitterShotgun
    this.jitterShotgun = new JitterShotgun({
      auctionSubscriber: this.auctionSubscriber,
      driftClient: this.driftClient,
      jitProxyClient: this.jitProxyClient,
      swiftOrderSubscriber: this.swiftOrderSubscriber,
      slotSubscriber: this.slotSubscriber,
      auctionSubscriberIgnoresSwiftOrders: true,
    });

    // Initialize JitterSniper  
    this.jitterSniper = new JitterSniper({
      auctionSubscriber: this.auctionSubscriber,
      driftClient: this.driftClient,
      jitProxyClient: this.jitProxyClient,
      swiftOrderSubscriber: this.swiftOrderSubscriber,
      slotSubscriber: this.slotSubscriber,
      auctionSubscriberIgnoresSwiftOrders: true,
    });

    // Set up order handlers
    this.setupOrderHandlers();

    await this.jitterShotgun.subscribe();
    await this.jitterSniper.subscribe();

    logger.info('✅ JitterShotgun and JitterSniper initialized and subscribed');
  }

  private setupOrderHandlers(): void {
    if (!this.jitterShotgun || !this.jitterSniper) return;

    // Shotgun order handler
    this.jitterShotgun.setOnTakeOrder(async (orderMessageRaw, signedMessage, isDelegateSignedMessage) => {
      await this.handleShotgunOrder(orderMessageRaw, signedMessage, isDelegateSignedMessage);
    });

    // Sniper order handler
    this.jitterSniper.setOnTakeOrder(async (orderMessageRaw, signedMessage, isDelegateSignedMessage) => {
      await this.handleSniperOrder(orderMessageRaw, signedMessage, isDelegateSignedMessage);
    });
  }

  private async handleShotgunOrder(orderMessageRaw: any, signedMessage: any, isDelegateSignedMessage: boolean): Promise<void> {
    try {
      // Check if shotgun is enabled in current strategy
      if (this.currentStrategy === HybridJitterStrategy.SNIPER_ONLY || 
          this.currentStrategy === HybridJitterStrategy.DISABLED ||
          this.crashSentinelActive) {
        return;
      }

      // Check allocation
      if (this.allocationState.shotgunAllocation <= 0) {
        return;
      }

      // Apply shotgun-specific filters
      if (!await this.shouldProcessShotgunOrder(orderMessageRaw, signedMessage)) {
        this.metrics.recordOrderSkipped(JitterMode.SHOTGUN, 'filters');
        return;
      }

      // Calculate clip size based on allocation
      const baseClipSize = config.shotgun.sizeClip;
      const clipSize = baseClipSize * this.allocationState.shotgunAllocation;

      logger.info(`🔫 Shotgun processing order: ${clipSize.toFixed(3)} SOL clip`);

      // Record the fill (simplified - in real implementation this would come from actual fill)
      const fill: FillEvent = {
        source: JitterMode.SHOTGUN,
        size: clipSize,
        price: signedMessage.signedMsgOrderParams.price / PRICE_PRECISION,
        side: signedMessage.signedMsgOrderParams.direction === PositionDirection.Long ? 'buy' : 'sell',
        market: this.getMarketName(signedMessage.signedMsgOrderParams.marketIndex),
        timestamp: Date.now(),
        orderId: `shotgun_${Date.now()}`,
        regime: this.currentRegime,
        qualityScore: undefined
      };

      this.fills.push(fill);
      this.metrics.recordFill(fill);

      // Coordinate with hedge bot
      await this.coordinateHedge(fill);

    } catch (error) {
      logger.error('Shotgun order handling failed', error);
      this.metrics.recordError('shotgun_order_error');
    }
  }

  private async handleSniperOrder(orderMessageRaw: any, signedMessage: any, isDelegateSignedMessage: boolean): Promise<void> {
    try {
      // Check if sniper is enabled in current strategy
      if (this.currentStrategy === HybridJitterStrategy.SHOTGUN_ONLY || 
          this.currentStrategy === HybridJitterStrategy.DISABLED ||
          this.crashSentinelActive) {
        return;
      }

      // Check allocation
      if (this.allocationState.sniperAllocation <= 0) {
        return;
      }

      // Calculate quality score
      const qualityScore = await this.calculateQualityScore(orderMessageRaw, signedMessage);
      
      // Apply sniper-specific filters
      if (!await this.shouldProcessSniperOrder(orderMessageRaw, signedMessage, qualityScore)) {
        this.metrics.recordOrderSkipped(JitterMode.SNIPER, 'filters');
        return;
      }

      // Calculate clip size based on allocation and quality
      const baseClipSize = config.sniper.sizeClip;
      const clipSize = baseClipSize * this.allocationState.sniperAllocation * qualityScore;

      logger.info(`🎯 Sniper processing order: ${clipSize.toFixed(3)} SOL clip (quality: ${(qualityScore * 100).toFixed(1)}%)`);

      // Record the fill
      const fill: FillEvent = {
        source: JitterMode.SNIPER,
        size: clipSize,
        price: signedMessage.signedMsgOrderParams.price / PRICE_PRECISION,
        side: signedMessage.signedMsgOrderParams.direction === PositionDirection.Long ? 'buy' : 'sell',
        market: this.getMarketName(signedMessage.signedMsgOrderParams.marketIndex),
        timestamp: Date.now(),
        orderId: `sniper_${Date.now()}`,
        regime: this.currentRegime,
        qualityScore
      };

      this.fills.push(fill);
      this.metrics.recordFill(fill);

      // Coordinate with hedge bot
      await this.coordinateHedge(fill);

    } catch (error) {
      logger.error('Sniper order handling failed', error);
      this.metrics.recordError('sniper_order_error');
    }
  }

  private async shouldProcessShotgunOrder(orderMessageRaw: any, signedMessage: any): Promise<boolean> {
    const orderParams = signedMessage.signedMsgOrderParams;
    
    // Size filter
    const size = orderParams.baseAssetAmount / BASE_PRECISION;
    if (size < config.shotgun.minSizeThreshold) {
      return false;
    }

    // Participation rate (high for shotgun)
    if (Math.random() > config.shotgun.participationRate) {
      return false;
    }

    // Skip sanitized orders if configured
    if (config.shotgun.skipSanitizedOrders && orderMessageRaw.willSanitize) {
      return false;
    }

    return true;
  }

  private async shouldProcessSniperOrder(orderMessageRaw: any, signedMessage: any, qualityScore: number): Promise<boolean> {
    const orderParams = signedMessage.signedMsgOrderParams;
    
    // Size filter (stricter for sniper)
    const size = orderParams.baseAssetAmount / BASE_PRECISION;
    if (size < config.sniper.minOrderSizeSol || size > config.sniper.maxOrderSizeSol) {
      return false;
    }

    // Quality score threshold
    if (qualityScore < config.sniper.minQualityScore) {
      return false;
    }

    // Participation rate (lower for sniper)
    if (Math.random() > config.sniper.participationRate) {
      return false;
    }

    // Always skip sanitized orders for sniper
    if (orderMessageRaw.willSanitize) {
      return false;
    }

    return true;
  }

  private async calculateQualityScore(orderMessageRaw: any, signedMessage: any): Promise<number> {
    // Simplified quality scoring - in real implementation this would be more sophisticated
    const orderParams = signedMessage.signedMsgOrderParams;
    const size = orderParams.baseAssetAmount / BASE_PRECISION;
    
    let score = 0;
    
    // Size factor (favor medium-large orders)
    const sizeFactor = Math.min(1, Math.max(0, (size - 1) / 10)); // 1-10 SOL range
    score += sizeFactor * 0.4;
    
    // Price factor (favor non-zero prices)
    const priceFactor = orderParams.price > 0 ? 1 : 0.5;
    score += priceFactor * 0.3;
    
    // Market factor (favor main markets)
    const marketFactor = config.marketIndexes.includes(orderParams.marketIndex) ? 1 : 0.5;
    score += marketFactor * 0.3;
    
    return Math.min(1, score);
  }

  private async coordinateHedge(fill: FillEvent): Promise<void> {
    // TODO: Integrate with actual hedge bot
    logger.info(`🔄 Coordinating hedge for ${fill.source} fill: ${fill.size} ${fill.market}`);
    
    // Different urgency based on source
    const urgency = fill.source === JitterMode.SHOTGUN ? 'fast' : 'opportunistic';
    const hedgeRatio = fill.source === JitterMode.SHOTGUN ? 1.0 : 0.7;
    
    this.metrics.recordHedgeCoordination(fill.source, urgency, hedgeRatio);
  }

  private async updateAllocation(): Promise<void> {
    try {
      // Simplified regime detection - in real implementation this would use actual market data
      const mockMarketData = {
        volatility: Math.random() * 0.5,
        trend: Math.random() * 2 - 1,
        price: 140 + Math.random() * 20 - 10
      };

      // Determine regime
      let newRegime = RegimeType.NORMAL;
      if (mockMarketData.volatility > 0.4) {
        newRegime = RegimeType.VOLATILE;
      } else if (mockMarketData.volatility < 0.15) {
        newRegime = RegimeType.CALM;
      } else if (Math.abs(mockMarketData.trend) > 0.6) {
        newRegime = RegimeType.TRENDING;
      }

      // Update allocations based on regime
      let shotgunAlloc = 0.6;
      let sniperAlloc = 0.4;

      switch (newRegime) {
        case RegimeType.CALM:
          shotgunAlloc = 0.8;
          sniperAlloc = 0.2;
          break;
        case RegimeType.VOLATILE:
          shotgunAlloc = 0.4;
          sniperAlloc = 0.6;
          break;
        case RegimeType.TRENDING:
          shotgunAlloc = 0.3;
          sniperAlloc = 0.7;
          break;
        case RegimeType.CRASH:
          shotgunAlloc = 0.0;
          sniperAlloc = 0.0;
          break;
      }

      // Apply risk scaling
      const riskScaling = this.calculateRiskScaling(mockMarketData);
      shotgunAlloc *= riskScaling;
      sniperAlloc *= riskScaling;

      this.allocationState = {
        shotgunAllocation: shotgunAlloc,
        sniperAllocation: sniperAlloc,
        regime: newRegime,
        lastUpdate: Date.now(),
        totalExposure: this.allocationState.totalExposure
      };

      this.currentRegime = newRegime;
      this.metrics.recordAllocationUpdate(this.allocationState);

      logger.info(`📊 Allocation updated: ${newRegime} -> Shotgun: ${(shotgunAlloc * 100).toFixed(1)}%, Sniper: ${(sniperAlloc * 100).toFixed(1)}%`);

    } catch (error) {
      logger.error('Failed to update allocation', error);
    }
  }

  private calculateRiskScaling(marketData: any): number {
    let scaling = 1.0;
    
    // Scale down on high volatility
    if (marketData.volatility > 0.5) {
      scaling *= 0.7;
    }
    
    // Scale down if exposure is high
    const exposureRatio = this.allocationState.totalExposure / config.maxTotalExposureUsd;
    if (exposureRatio > 0.8) {
      scaling *= (1.0 - exposureRatio * 0.5);
    }
    
    return Math.max(0.1, scaling);
  }

  private getMarketName(marketIndex: number): string {
    const marketNames: { [key: number]: string } = {
      0: 'SOL-PERP',
      1: 'BTC-PERP', 
      2: 'ETH-PERP'
    };
    return marketNames[marketIndex] || `MARKET-${marketIndex}`;
  }

  private emergencyHalt(): void {
    logger.warn('🚨 Emergency halt activated');
    this.crashSentinelActive = true;
    this.currentStrategy = HybridJitterStrategy.DISABLED;
    this.metrics.recordEmergencyHalt();
  }

  private emergencyResume(): void {
    logger.info('✅ Emergency halt deactivated');
    this.crashSentinelActive = false;
    this.currentStrategy = HybridJitterStrategy.HYBRID;
    this.metrics.recordEmergencyResume();
  }

  private getHealthStatus(): HealthStatus {
    return {
      healthy: this.isRunning && !this.crashSentinelActive,
      timestamp: Date.now(),
      services: {
        driftClient: !!this.driftClient,
        userMap: !!this.userMap,
        jitProxyClient: !!this.jitProxyClient,
        swiftSubscriber: !!this.swiftOrderSubscriber,
        auctionSubscriber: !!this.auctionSubscriber,
        slotSubscriber: !!this.slotSubscriber,
        jitterShotgun: !!this.jitterShotgun,
        jitterSniper: !!this.jitterSniper
      },
      strategy: this.currentStrategy,
      regime: this.currentRegime,
      allocation: this.allocationState,
      crashSentinelActive: this.crashSentinelActive
    };
  }

  private getPerformanceSummary(): any {
    const shotgunFills = this.fills.filter(f => f.source === JitterMode.SHOTGUN);
    const sniperFills = this.fills.filter(f => f.source === JitterMode.SNIPER);

    return {
      totalFills: this.fills.length,
      shotgunFills: shotgunFills.length,
      sniperFills: sniperFills.length,
      currentStrategy: this.currentStrategy,
      currentRegime: this.currentRegime,
      allocation: this.allocationState,
      recentFills: this.fills.slice(-10), // Last 10 fills
      uptime: this.isRunning ? Date.now() - this.allocationState.lastUpdate : 0
    };
  }

  async start(): Promise<void> {
    await this.initialize();
    
    // Start allocation update loop
    setInterval(() => {
      this.updateAllocation().catch(error => {
        logger.error('Allocation update failed', error);
      });
    }, 30000); // Update every 30 seconds

    const port = config.port || 8788;
    this.server = this.app.listen(port, () => {
      logger.info(`🚀 Hybrid Jitter Service running on port ${port}`);
    });
  }

  async stop(): Promise<void> {
    logger.info('🛑 Stopping Hybrid Jitter Service...');

    if (this.jitterShotgun) {
      await this.jitterShotgun.unsubscribe();
    }
    
    if (this.jitterSniper) {
      await this.jitterSniper.unsubscribe();
    }

    if (this.swiftOrderSubscriber) {
      await this.swiftOrderSubscriber.unsubscribe();
    }

    if (this.auctionSubscriber) {
      await this.auctionSubscriber.unsubscribe();
    }

    if (this.slotSubscriber) {
      await this.slotSubscriber.unsubscribe();
    }

    if (this.driftClient) {
      await this.driftClient.unsubscribe();
    }

    if (this.server) {
      this.server.close();
    }

    this.isRunning = false;
    logger.info('✅ Hybrid Jitter Service stopped');
  }
}

// Main execution
async function main() {
  const service = new HybridJitterService();
  
  // Graceful shutdown
  process.on('SIGINT', async () => {
    logger.info('Received SIGINT, shutting down gracefully...');
    await service.stop();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    logger.info('Received SIGTERM, shutting down gracefully...');
    await service.stop();
    process.exit(0);
  });

  try {
    await service.start();
  } catch (error) {
    logger.error('Failed to start Hybrid Jitter Service', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main().catch(error => {
    console.error('Unhandled error:', error);
    process.exit(1);
  });
}

export { HybridJitterService };
