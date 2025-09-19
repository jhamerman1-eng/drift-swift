import express from "express";
import pino from "pino";
import bs58 from "bs58";
import {
  BN, DriftClient, UserMap, SwiftOrderSubscriber, AuctionSubscriber,
  SlotSubscriber, JitProxyClient, getUserAccountPublicKey,
  isSignedMsgOrder, MarketType, getLimitOrderParams, PostOnlyParams,
  PRICE_PRECISION, BASE_PRECISION
} from "@drift-labs/sdk";
import { Connection, Keypair, PublicKey, ComputeBudgetProgram } from "@solana/web3.js";
import { metrics } from "./metrics.js";

const log = pino();
const app = express();
app.use(express.json({ limit: "512kb" }));

// ---- ENV / CONFIG ----
const RPC_URL = process.env.RPC_URL!;
const DRIFT_ENV = process.env.DRIFT_ENV || "mainnet-beta";
const JIT_PROXY_PROGRAM_ID = process.env.JIT_PROXY_PROGRAM_ID!;
const MAKER_KEYPAIR = Keypair.fromSecretKey(
  Uint8Array.from(JSON.parse(process.env.MAKER_KEYPAIR!))
);
const MARKET_INDEXES = (process.env.MARKET_INDEXES || "0,1,2").split(",").map(Number);
const SLOT_SKEW_MAX = Number(process.env.SLOT_SKEW_MAX || 30);
const TOMB_TTL_MS = Number(process.env.TOMB_TTL_MS || 800);

// ---- DRIFT WIRING ----
const connection = new Connection(RPC_URL, "confirmed");
const driftClient = new DriftClient({ connection, env: DRIFT_ENV as any, wallet: { payer: MAKER_KEYPAIR } as any });
const userMap = new UserMap({
  driftClient,
  connection,
  subscriptionConfig: { type: "websocket", resubTimeoutMs: 30000, commitment: "confirmed" },
  skipInitialLoad: false,
  includeIdle: false,
});

const slotSubscriber = new SlotSubscriber(connection, { resubTimeoutMs: 30000 });
const auctionSubscriber = new AuctionSubscriber({ 
  driftClient, 
  slotSubscriber, 
  markets: MARKET_INDEXES.map(i => ({ marketType: MarketType.PERP, marketIndex: i })) 
});
const jitProxyClient = new JitProxyClient({ driftClient, programId: new PublicKey(JIT_PROXY_PROGRAM_ID) });

const swiftOrderSubscriber = new SwiftOrderSubscriber({
  driftEnv: DRIFT_ENV as any,
  marketIndexes: MARKET_INDEXES,
  keypair: Keypair.generate(), // empty wallet OK
  driftClient,
  userAccountGetter: userMap
});

// ---- State: de-dupe & tombstones ----
type Key = string;
const dedupeSet = new Set<string>(); // For Swift order de-duplication
const tomb: Record<Key, number> = {}; // Tombstones for cancel/replace versioning
const orderVersions: Record<string, number> = {}; // Order versioning

const nowMs = () => Date.now();
const priceLevel = (pxTicks: BN) => pxTicks.toString();

const health = { swift: false, auction: false, drift: false, slot: false };

// ---- US-JIT-001: Unified event emission ----
interface UnifiedOrderEvent {
  uuid: string;
  takerAuthority: string;
  subAccountId: number;
  marketIndex: number;
  direction: "long" | "short";
  baseAssetAmount: string;
  auctionParams?: {
    startPrice?: string;
    endPrice?: string;
    duration?: number;
  };
  slot: number;
  source: "swift" | "auction";
}

const eventEmitter = {
  emit: (event: UnifiedOrderEvent) => {
    log.info({ event }, "Unified order event");
    metrics.increment("jit_unified_events_total", { source: event.source });
  }
};

// ---- Enhanced subscribers with de-duplication ----
async function bringUp() {
  await driftClient.subscribe();
  await userMap.subscribe();
  await slotSubscriber.subscribe();
  
  // US-JIT-001: Auction subscriber with Swift order filtering
  await auctionSubscriber.subscribe({ 
    auctionSubscriberIgnoresSwiftOrders: true 
  });
  
  auctionSubscriber.eventEmitter.on("auctionRecord", (record: any) => {
    // Skip if this is a Swift order (de-duplication)
    if (isSignedMsgOrder(record)) {
      metrics.increment("jit_dedup_drops_total", { reason: "swift_order_in_auction" });
      return;
    }
    
    const unifiedEvent: UnifiedOrderEvent = {
      uuid: record.uuid || `auction_${record.slot}_${record.ts}`,
      takerAuthority: record.taker.toString(),
      subAccountId: record.subAccountId || 0,
      marketIndex: record.marketIndex,
      direction: record.direction?.long ? "long" : "short",
      baseAssetAmount: record.baseAssetAmount.toString(),
      auctionParams: {
        startPrice: record.auctionStartPrice?.toString(),
        endPrice: record.auctionEndPrice?.toString(),
        duration: record.auctionDuration
      },
      slot: record.slot,
      source: "auction"
    };
    
    eventEmitter.emit(unifiedEvent);
  });
  
  // US-JIT-001: Swift subscriber with de-duplication
  await swiftOrderSubscriber.subscribe(async (orderMessageRaw: any, signedMessage: any, isDelegate?: boolean) => {
    const orderKey = `${orderMessageRaw.uuid}_${orderMessageRaw.taker_authority}`;
    
    // De-duplication check
    if (dedupeSet.has(orderKey)) {
      metrics.increment("jit_dedup_drops_total", { reason: "duplicate_swift_order" });
      return;
    }
    
    dedupeSet.add(orderKey);
    metrics.increment("jit_swift_orders_total");
    
    // Clean up old dedupe entries (keep last 1000)
    if (dedupeSet.size > 1000) {
      const entries = Array.from(dedupeSet);
      entries.slice(0, 100).forEach(key => dedupeSet.delete(key));
    }
    
    const unifiedEvent: UnifiedOrderEvent = {
      uuid: orderMessageRaw.uuid,
      takerAuthority: orderMessageRaw.taker_authority,
      subAccountId: signedMessage.subAccountId || 0,
      marketIndex: signedMessage.signedMsgOrderParams?.marketIndex || 0,
      direction: signedMessage.signedMsgOrderParams?.direction?.long ? "long" : "short",
      baseAssetAmount: signedMessage.signedMsgOrderParams?.baseAssetAmount?.toString() || "0",
      auctionParams: {
        startPrice: signedMessage.signedMsgOrderParams?.auctionStartPrice?.toString(),
        endPrice: signedMessage.signedMsgOrderParams?.auctionEndPrice?.toString(),
        duration: signedMessage.signedMsgOrderParams?.auctionDuration
      },
      slot: await connection.getSlot("confirmed"),
      source: "swift"
    };
    
    eventEmitter.emit(unifiedEvent);
  });
  
  health.swift = health.auction = health.drift = health.slot = true;
  log.info("Enhanced JIT Maker online with unified events and de-duplication");
}

bringUp().catch(e => { log.error(e); process.exit(1); });

// ---- Tombstone management for US-JIT-004 ----
function cleanupTombstones() {
  const now = nowMs();
  Object.keys(tomb).forEach(key => {
    if (now - tomb[key] > TOMB_TTL_MS) {
      delete tomb[key];
    }
  });
}

setInterval(cleanupTombstones, TOMB_TTL_MS / 2);

function getTombstoneKey(marketIndex: number, side: string, level: string): string {
  return `${marketIndex}_${side}_${level}`;
}

function checkTombstone(marketIndex: number, side: string, priceLevel: string): boolean {
  const key = getTombstoneKey(marketIndex, side, priceLevel);
  return tomb[key] !== undefined;
}

function setTombstone(marketIndex: number, side: string, priceLevel: string) {
  const key = getTombstoneKey(marketIndex, side, priceLevel);
  tomb[key] = nowMs();
}

// ---- Helpers ----
function computeBudgetIxs(units = 1_000_000, microLamports = 2000) {
  return [
    ComputeBudgetProgram.setComputeUnitLimit({ units }),
    ComputeBudgetProgram.setComputeUnitPrice({ microLamports })
  ];
}

async function getTakerInfo(orderMessageRaw: any, signedMessage: any) {
  const takerAuthority = new PublicKey(orderMessageRaw["taker_authority"]);
  const subAccountId = signedMessage.subAccountId ?? 0;
  const takerUserPubkey = await getUserAccountPublicKey(driftClient.program.programId, takerAuthority, subAccountId);
  const takerUserAccount = (await userMap.mustGet(takerUserPubkey.toString())).getUserAccount();
  const takerStats = await driftClient.getUserStatsAccountPublicKey(takerUserAccount.authority);
  const signingAuthority = new PublicKey(orderMessageRaw["signing_authority"] ?? takerAuthority.toBase58());
  return { taker: takerUserPubkey, takerStats, takerUserAccount, signingAuthority, subAccountId };
}

// ---- REST: health with subscriber status ----
app.get("/health", (_req, res) => {
  res.json({ 
    ok: health.swift && health.auction && health.drift && health.slot,
    subscribers: health,
    metrics: {
      swift_orders_total: metrics.get("jit_swift_orders_total"),
      dedup_drops_total: metrics.get("jit_dedup_drops_total"),
      unified_events_total: metrics.get("jit_unified_events_total")
    }
  });
});

// ---- REST: metrics endpoint ----
app.get("/metrics", (_req, res) => {
  const allMetrics = metrics.getAll();
  res.set("Content-Type", "text/plain");
  res.send(
    Object.entries(allMetrics)
      .map(([name, value]) => `# TYPE ${name} counter\n${name} ${value}`)
      .join("\n")
  );
});

// ---- REST: place_and_make (Enhanced US-JIT-002) ----
app.post("/jit/place_and_make", async (req, res) => {
  const startTime = nowMs();
  try {
    const { orderMessageRaw, signedMessage, maker, precedingIxs, overrideCustomIxIndex } = req.body;

    // US-JIT-002: Slot skew guard
    const signedSlot = Number(signedMessage.signedMsgOrderParams?.auctionStartSlot ?? signedMessage.slot ?? 0);
    const currentSlot = await connection.getSlot("confirmed");
    if (currentSlot - signedSlot > SLOT_SKEW_MAX) {
      metrics.increment("jit_place_total", { result: "fail", reason: "stale_slot" });
      return res.status(409).json({ error: "stale_signed_slot", detail: { currentSlot, signedSlot } });
    }

    const takerInfo = await getTakerInfo(orderMessageRaw, signedMessage);

    // maker params
    const isOrderLong = signedMessage.signedMsgOrderParams.direction.long === true;
    const limitPx = new BN(Math.round(maker.price * PRICE_PRECISION.toNumber()));
    const baseAmt = new BN(Math.round(maker.size * BASE_PRECISION.toNumber()));
    const makerParams = getLimitOrderParams({
      marketType: MarketType.PERP,
      marketIndex: signedMessage.signedMsgOrderParams.marketIndex,
      direction: isOrderLong ? "short" as any : "long" as any,
      baseAssetAmount: baseAmt,
      price: limitPx,
      postOnly: maker.postOnly ? PostOnlyParams.MUST_POST_ONLY : PostOnlyParams.NONE,
      immediateOrCancel: !!maker.ioc
    });

    const signedMsgOrderParamsBuf = Buffer.from(orderMessageRaw["order_message"]);
    const signatureBuf = Buffer.from(orderMessageRaw["order_signature"], "base64");
    const uuid = Buffer.from(orderMessageRaw["uuid"], "utf8");
    
    // US-JIT-003: Priority fee handling
    const preIxs = (precedingIxs?.length ? 
      precedingIxs.map(b64 => Buffer.from(b64, "base64")) : 
      computeBudgetIxs()
    ).map(ix => ix as any);

    const ixs = await driftClient.getPlaceAndMakeSignedMsgPerpOrderIxs(
      { orderParams: signedMsgOrderParamsBuf, signature: signatureBuf },
      uuid,
      takerInfo,
      makerParams,
      undefined, // referrer
      takerInfo.subAccountId,
      preIxs,
      overrideCustomIxIndex
    );

    const tx = await driftClient.buildTransaction(ixs.flat());
    const sig = await driftClient.sendTransaction(tx, [], { skipPreflight: true });
    
    const duration = nowMs() - startTime;
    metrics.increment("jit_place_total", { result: "ok", reason: "success" });
    
    return res.json({ txSig: sig, makerOrderId: null, duration });
  } catch (e: any) {
    const duration = nowMs() - startTime;
    const msg = e?.message || String(e);
    metrics.increment("jit_place_total", { result: "fail", reason: "error" });
    
    return res.status(500).json({ error: "jit_place_failed", message: msg, duration });
  }
});

// ---- REST: cancel_replace (Enhanced US-JIT-004) ----
app.post("/jit/cancel_replace", async (req, res) => {
  try {
    const { orderId, newOrder } = req.body;
    
    if (!orderId || !newOrder) {
      return res.status(400).json({ error: "missing_required_fields" });
    }
    
    const { marketIndex, side, price } = newOrder;
    const priceStr = priceLevel(new BN(Math.round(price * PRICE_PRECISION.toNumber())));
    
    // US-JIT-004: Check tombstone
    if (checkTombstone(marketIndex, side, priceStr)) {
      metrics.increment("jit_cancel_replace_total", { phase: "blocked", result: "tombstone" });
      return res.status(409).json({ error: "tombstone_active", detail: { marketIndex, side, priceLevel: priceStr } });
    }
    
    // US-JIT-004: Create versioned client_order_id
    const currentVersion = orderVersions[orderId] || 0;
    const newVersion = currentVersion + 1;
    const versionedOrderId = `${orderId}_v${newVersion}`;
    orderVersions[orderId] = newVersion;
    
    // Set tombstone
    setTombstone(marketIndex, side, priceStr);
    
    metrics.increment("jit_cancel_replace_total", { phase: "execute", result: "ok" });
    
    // Note: Actual cancel/replace logic would go here
    // This is a placeholder that shows the structure
    
    res.json({ 
      success: true, 
      newOrderId: versionedOrderId,
      tombstoneSet: true
    });
    
  } catch (e: any) {
    metrics.increment("jit_cancel_replace_total", { phase: "execute", result: "fail" });
    res.status(500).json({ error: "cancel_replace_failed", message: e.message });
  }
});

const port = Number(process.env.PORT || 8787);
app.listen(port, () => log.info({ port }, "Enhanced JIT service listening"));



