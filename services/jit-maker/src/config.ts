/**
 * Configuration management for JIT Maker Service
 * Handles environment variables and validation
 */

import { PublicKey, Keypair } from "@solana/web3.js";
import Joi from "joi";

export interface ServiceConfig {
  // Environment
  rpcUrl: string;
  driftEnv: "mainnet-beta" | "devnet";
  
  // JIT Proxy
  jitProxyProgramId: PublicKey;
  
  // Maker keypair
  makerKeypair: Keypair;
  
  // Markets
  marketIndexes: number[];
  
  // Validation
  slotSkewMax: number;
  
  // Server
  port: number;
  host: string;
  
  // Timeouts and limits
  requestTimeoutMs: number;
  maxConcurrentRequests: number;
  
  // Metrics
  metricsEnabled: boolean;
  
  // Development
  isDevelopment: boolean;
  logLevel: string;
}

const configSchema = Joi.object({
  rpcUrl: Joi.string().uri().required(),
  driftEnv: Joi.string().valid("mainnet-beta", "devnet").default("mainnet-beta"),
  jitProxyProgramId: Joi.string().required(),
  makerKeypair: Joi.string().required(),
  marketIndexes: Joi.string().default("0,1,2"),
  slotSkewMax: Joi.number().integer().positive().default(30),
  port: Joi.number().integer().min(1024).max(65535).default(8787),
  host: Joi.string().default("0.0.0.0"),
  requestTimeoutMs: Joi.number().integer().positive().default(5000),
  maxConcurrentRequests: Joi.number().integer().positive().default(100),
  metricsEnabled: Joi.boolean().default(true),
  logLevel: Joi.string().valid("trace", "debug", "info", "warn", "error").default("info"),
});

export function loadConfig(): ServiceConfig {
  const rawConfig = {
    rpcUrl: process.env.RPC_URL,
    driftEnv: process.env.DRIFT_ENV,
    jitProxyProgramId: process.env.JIT_PROXY_PROGRAM_ID,
    makerKeypair: process.env.MAKER_KEYPAIR,
    marketIndexes: process.env.MARKET_INDEXES,
    slotSkewMax: process.env.SLOT_SKEW_MAX ? parseInt(process.env.SLOT_SKEW_MAX) : undefined,
    port: process.env.PORT ? parseInt(process.env.PORT) : undefined,
    host: process.env.HOST,
    requestTimeoutMs: process.env.REQUEST_TIMEOUT_MS ? parseInt(process.env.REQUEST_TIMEOUT_MS) : undefined,
    maxConcurrentRequests: process.env.MAX_CONCURRENT_REQUESTS ? parseInt(process.env.MAX_CONCURRENT_REQUESTS) : undefined,
    metricsEnabled: process.env.METRICS_ENABLED !== "false",
    logLevel: process.env.LOG_LEVEL,
  };

  const { error, value } = configSchema.validate(rawConfig, { 
    allowUnknown: false,
    stripUnknown: true 
  });

  if (error) {
    throw new Error(`Configuration validation failed: ${error.details.map(d => d.message).join(", ")}`);
  }

  // Parse complex fields
  const makerKeypairData = JSON.parse(value.makerKeypair);
  const makerKeypair = Keypair.fromSecretKey(
    makerKeypairData.length === 64 
      ? Uint8Array.from(makerKeypairData)
      : Uint8Array.from([...makerKeypairData, ...Array(32).fill(0)].slice(0, 64))
  );

  const marketIndexes = value.marketIndexes
    .split(",")
    .map((s: string) => parseInt(s.trim()))
    .filter((n: number) => !isNaN(n));

  const jitProxyProgramId = new PublicKey(value.jitProxyProgramId);

  return {
    rpcUrl: value.rpcUrl,
    driftEnv: value.driftEnv,
    jitProxyProgramId,
    makerKeypair,
    marketIndexes,
    slotSkewMax: value.slotSkewMax,
    port: value.port,
    host: value.host,
    requestTimeoutMs: value.requestTimeoutMs,
    maxConcurrentRequests: value.maxConcurrentRequests,
    metricsEnabled: value.metricsEnabled,
    isDevelopment: process.env.NODE_ENV !== "production",
    logLevel: value.logLevel,
  };
}

export function validateConfig(config: ServiceConfig): void {
  // Additional validation that requires the parsed config
  if (!config.makerKeypair.publicKey) {
    throw new Error("Invalid maker keypair: missing public key");
  }

  if (config.marketIndexes.length === 0) {
    throw new Error("At least one market index must be specified");
  }

  if (config.marketIndexes.some(idx => idx < 0 || idx > 255)) {
    throw new Error("Market indexes must be between 0 and 255");
  }
}



