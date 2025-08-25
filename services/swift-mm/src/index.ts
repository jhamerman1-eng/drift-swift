import 'dotenv/config';
import express from 'express';
import bodyParser from 'body-parser';
import { Connection, Keypair } from '@solana/web3.js';
import { DriftClient, Wallet, BN, OrderType, PositionDirection } from '@drift-labs/sdk';
import { register, httpLatency, orderRequests } from './metrics.js';
import { loadMarketMeta, toTicks, toLots } from './market.js';

const RPC_URL = process.env.RPC_URL!;
const WS_URL  = process.env.WS_URL!;
const CLUSTER = process.env.SOLANA_CLUSTER || 'devnet';
const PORT = Number(process.env.SWIFT_SIDECAR_PORT || 8787);
const API_KEY = process.env.SWIFT_API_KEY;

// Dev-only maker key (optional)
const SECRET_KEY = process.env.SWIFT_MAKER_SECRET
  ? Uint8Array.from(JSON.parse(process.env.SWIFT_MAKER_SECRET))
  : Keypair.generate().secretKey;

const wallet = new Wallet(Keypair.fromSecretKey(SECRET_KEY));
const connection = new Connection(RPC_URL, { wsEndpoint: WS_URL, commitment: 'confirmed' });

const client = new DriftClient({
  connection,
  wallet,
  env: CLUSTER as any,
});

let metaCache: Record<number, {tickSize: number; lotSize: number}> = {};

async function init() {
  await client.subscribe();
  console.log('[swift-mm] subscribed. cluster=%s rpc=%s', CLUSTER, RPC_URL);
}

const app = express();
app.use(bodyParser.json());

// Auth (optional)
app.use((req, res, next) => {
  if (!API_KEY) return next();
  const auth = req.headers['authorization'];
  if (auth && typeof auth === 'string' && auth.startsWith('Bearer ')) {
    const token = auth.slice('Bearer '.length);
    if (token === API_KEY) return next();
  }
  return res.status(401).json({ ok: false, error: 'unauthorized' });
});

// Latency wrapper
function timed(route: string, handler: any) {
  return async (req: any, res: any) => {
    const end = httpLatency.startTimer({ route, method: req.method });
    try {
      await handler(req, res);
    } finally {
      end({ status: String(res.statusCode) });
    }
  };
}

app.post('/health', timed('health', async (_req, res) => {
  res.json({ ok: true, driver: 'swift', cluster: CLUSTER });
}));

app.get('/metrics', async (_req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

app.post('/place', timed('place', async (req, res) => {
  try {
    const { marketIndex = 0, price, size, postOnly = true, reduceOnly = false, side = 'bid', ioc = false } = req.body || {};
    if (price == null || size == null) return res.status(400).json({ ok: false, error: 'price/size required' });

    if (!metaCache[marketIndex]) metaCache[marketIndex] = await loadMarketMeta(client, marketIndex);

    const ticks = toTicks(Number(price), metaCache[marketIndex].tickSize);
    const lots  = toLots(Number(size),  metaCache[marketIndex].lotSize);

    const txSig = await client.placePerpOrder({
      marketIndex,
      price: ticks,
      baseAssetAmount: lots,
      direction: side === 'ask' ? PositionDirection.SHORT : PositionDirection.LONG,
      orderType: ioc ? OrderType.IOC : OrderType.LIMIT,
      postOnly,
      reduceOnly,
    });

    orderRequests.inc({ action: 'place' });
    return res.json({ ok: true, txSig });
  } catch (e: any) {
    console.error('place error', e);
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
}));

app.post('/cancelReplace', timed('cancelReplace', async (req, res) => {
  try {
    const { orderId, marketIndex = 0, newPrice, newSize } = req.body || {};
    if (!orderId) return res.status(400).json({ ok: false, error: 'orderId required' });

    await client.cancelOrder(orderId);

    if (newPrice != null && newSize != null) {
      if (!metaCache[marketIndex]) metaCache[marketIndex] = await loadMarketMeta(client, marketIndex);
      const ticks = toTicks(Number(newPrice), metaCache[marketIndex].tickSize);
      const lots  = toLots(Number(newSize),  metaCache[marketIndex].lotSize);
      const txSig = await client.placePerpOrder({
        marketIndex,
        price: ticks,
        baseAssetAmount: lots,
        orderType: OrderType.LIMIT,
      });
      orderRequests.inc({ action: 'cancelReplace' });
      return res.json({ ok: true, txSig });
    }
    orderRequests.inc({ action: 'cancelReplace' });
    return res.json({ ok: true });
  } catch (e: any) {
    console.error('cancelReplace error', e);
    return res.status(500).json({ ok: false, error: String(e?.message || e) });
  }
}));

init().then(() => app.listen(PORT, () => {
  console.log(`[swift-mm] HTTP listening on :${PORT}`);
})).catch((e) => {
  console.error('failed to init swift-mm', e);
  process.exit(1);
});
