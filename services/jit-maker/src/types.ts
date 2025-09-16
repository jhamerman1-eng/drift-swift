/**
 * Type definitions for JIT Maker Service
 */

import { PublicKey } from "@solana/web3.js";

export interface HealthStatus {
  ok: boolean;
  timestamp: number;
  uptime: number;
  subscribers: {
    swift: boolean;
    auction: boolean;
    drift: boolean;
    slot: boolean;
  };
  lastActivity: {
    swift: number | null;
    auction: number | null;
    slot: number | null;
  };
}

export interface PlaceAndMakeRequest {
  orderMessageRaw: {
    uuid: string;
    taker_authority: string;
    order_message: string; // hex-encoded
    order_signature: string; // base64-encoded
    signing_authority?: string;
  };
  signedMessage: {
    signedMsgOrderParams: {
      marketIndex: number;
      direction: { long?: boolean; short?: boolean };
      baseAssetAmount: string;
      price?: string;
      auctionStartSlot?: number;
      auctionEndSlot?: number;
      auctionStartPrice?: string;
      auctionEndPrice?: string;
    };
    subAccountId?: number;
    slot?: number;
  };
  maker: {
    price: number;
    size: number;
    postOnly?: boolean;
    ioc?: boolean;
  };
  precedingIxs?: string[]; // base64-encoded instructions
  overrideCustomIxIndex?: number;
}

export interface PlaceAndMakeResponse {
  txSig: string;
  makerOrderId?: string;
  duration?: number;
}

export interface ErrorResponse {
  error: string;
  message?: string;
  details?: Record<string, unknown>;
}

export interface CancelReplaceRequest {
  orderId: string;
  newOrder: {
    marketIndex: number;
    side: "buy" | "sell";
    price: number;
    size: number;
    postOnly?: boolean;
  };
}

export interface CancelReplaceResponse {
  newOrderId: string;
  tombstoneSet: boolean;
}

export interface MetricsData {
  jit_place_total: Record<string, number>;
  jit_cancel_replace_total: Record<string, number>;
  jit_request_duration_ms: {
    count: number;
    sum: number;
    p50: number;
    p95: number;
    p99: number;
  };
  jit_health_status: number;
  jit_active_subscribers: Record<string, number>;
}

export interface TakerInfo {
  authority: PublicKey;
  userAccount: PublicKey;
  stats: PublicKey;
  signingAuthority: PublicKey;
  subAccountId: number;
}

export interface SlotValidation {
  current: number;
  signed: number;
  skew: number;
  valid: boolean;
}



