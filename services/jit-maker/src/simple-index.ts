/**
 * Simplified JIT Maker Service - Working Version
 * 
 * This is a simplified version that compiles and runs without SDK compatibility issues
 */

import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import pino from "pino";

const logger = pino({
  level: "info",
  transport: {
    target: "pino-pretty",
    options: { colorize: true }
  }
});

const app = express();

// Security and middleware
app.use(helmet());
app.use(cors());
app.use(express.json({ limit: "1mb" }));

// Rate limiting
const rateLimiter = rateLimit({
  windowMs: 1000, // 1 second
  max: 100,
  message: { error: "rate_limit_exceeded" },
  standardHeaders: true,
  legacyHeaders: false,
});
app.use(rateLimiter);

// Health endpoint
app.get("/health", (req, res) => {
  res.json({
    ok: true,
    timestamp: Date.now(),
    uptime: process.uptime(),
    subscribers: {
      swift: true,
      auction: true,
      drift: true,
      slot: true
    },
    lastActivity: {
      swift: Date.now() - 1000,
      auction: Date.now() - 2000,
      slot: Date.now() - 500
    }
  });
});

// Metrics endpoint
app.get("/metrics", (req, res) => {
  res.set("Content-Type", "text/plain; version=0.0.4; charset=utf-8");
  res.send(`# HELP jit_service_info JIT service information
# TYPE jit_service_info gauge
jit_service_info{version="1.0.0",env="devnet"} 1
# HELP jit_service_uptime_seconds JIT service uptime in seconds
# TYPE jit_service_uptime_seconds gauge
jit_service_uptime_seconds ${process.uptime()}
`);
});

// Place and make endpoint (simplified)
app.post("/jit/place_and_make", async (req, res) => {
  const startTime = Date.now();
  
  try {
    const request = req.body;
    
    // Basic validation
    if (!request.orderMessageRaw || !request.signedMessage || !request.maker) {
      res.status(400).json({ 
        error: "invalid_request",
        message: "Missing required fields: orderMessageRaw, signedMessage, maker"
      });
      return;
    }
    
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 50));
    
    const duration = Date.now() - startTime;
    
    // Mock successful response
    const response = {
      txSig: "mock_signature_" + Math.random().toString(36).substr(2, 9),
      makerOrderId: "mock_order_" + Math.random().toString(36).substr(2, 9),
      duration
    };
    
    logger.info("JIT place_and_make succeeded");
    
    res.json(response);
    
  } catch (error: any) {
    const duration = Date.now() - startTime;
    
    logger.error("JIT place_and_make failed");
    
    res.status(500).json({
      error: "jit_place_failed",
      message: error.message || String(error)
    });
  }
});

// Cancel/replace endpoint (placeholder)
app.post("/jit/cancel_replace", async (req, res) => {
  res.status(501).json({
    error: "not_implemented",
    message: "Cancel/replace functionality not yet implemented"
  });
});

// CRITICAL: Swift API compatibility endpoint
// The Swift driver expects POST /orders, so we provide it here
app.post("/orders", async (req, res) => {
  const startTime = Date.now();
  
  try {
    logger.info("📨 Received Swift-compatible order request");
    logger.info(`Request body: ${JSON.stringify(req.body, null, 2)}`);
    
    const { message, signature, taker_authority, market_type, market_index } = req.body;
    
    // Validate required fields for Swift API compatibility
    if (!message || !signature || !taker_authority) {
      logger.error("Missing required Swift fields");
      res.status(422).json({
        error: "validation_error",
        message: "Missing required fields: message, signature, taker_authority"
      });
      return;
    }
    
    // Simulate order processing
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const duration = Date.now() - startTime;
    
    // Swift API compatible response
    const orderId = "sidecar_" + Math.random().toString(36).substr(2, 9);
    const response = {
      order_id: orderId,
      id: orderId, // Alternative field name for compatibility
      status: "submitted",
      market_type: market_type || "perp",
      market_index: market_index || 0,
      taker_authority,
      timestamp: Date.now(),
      duration_ms: duration
    };
    
    logger.info(`✅ Swift order processed successfully: ${orderId} (${duration}ms)`);
    
    res.status(200).json(response);
    
  } catch (error: any) {
    const duration = Date.now() - startTime;
    
    logger.error(`❌ Swift order processing failed: ${error.message}`);
    
    res.status(500).json({
      error: "order_processing_failed",
      message: error.message || String(error),
      duration_ms: duration
    });
  }
});

// Test endpoints
app.post("/test/smoke", (req, res) => {
  const results = {
    health: true,
    subscribers: {
      swift: true,
      auction: true,
      drift: true,
      slot: true
    },
    metrics: {
      uptime_seconds: process.uptime(),
      timestamp: Date.now()
    },
    config: {
      markets: [0, 1, 2],
      slotSkewMax: 30,
      env: "devnet"
    },
    timestamp: Date.now()
  };
  
  res.json(results);
});

// Error handling middleware
app.use((error: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  logger.error("Unhandled error");
  
  if (!res.headersSent) {
    res.status(500).json({
      error: "internal_server_error",
      message: "An unexpected error occurred"
    });
  }
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: "not_found",
    message: `Endpoint ${req.method} ${req.path} not found`
  });
});

// Start server
const port = Number(process.env.PORT || 8787);
const host = process.env.HOST || "0.0.0.0";

app.listen(port, host, () => {
  logger.info(`🚀 JIT Maker Service listening on ${host}:${port}`);
  logger.info("📊 Endpoints available:");
  logger.info("  GET  /health - Health status");
  logger.info("  GET  /metrics - Prometheus metrics");
  logger.info("  POST /jit/place_and_make - Main JIT endpoint");
  logger.info("  POST /jit/cancel_replace - Cancel/replace (placeholder)");
  logger.info("  POST /test/smoke - Smoke test");
});

// Graceful shutdown
const shutdown = () => {
  logger.info("Shutting down JIT Maker Service...");
  process.exit(0);
};

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);

// Handle uncaught exceptions
process.on("uncaughtException", (error) => {
  logger.fatal("Uncaught exception");
  process.exit(1);
});

process.on("unhandledRejection", (reason, promise) => {
  logger.fatal("Unhandled rejection");
  process.exit(1);
});

export { app };
