const express = require('express');
const client = require('prom-client');
const { WebSocket: WSWebSocket, WebSocketServer } = require('ws');
const { fetch: undiciFetch } = require('undici');
const { ulid } = require('ulid');
const { subscribe: subscribeToMarket, placeOrder: placeOrderFn, getBook: getBookFn } = require('./market');
const { metrics } = require('./metrics');

const app = express();
const register = new client.Registry();
client.collectDefaultMetrics({ register });
app.use(express.json());

const PORT = parseInt(process.env.PORT || '8787', 10);
const FORWARD_BASE = process.env.SWIFT_FORWARD_BASE?.replace(/\/$/, '');
const FORWARD_WS = process.env.SWIFT_FORWARD_WS || (FORWARD_BASE ? FORWARD_BASE.replace(/^http/, 'ws') + '/ws' : undefined);
const API_KEY = process.env.SWIFT_API_KEY;

// Broadcast helper (wired after WSS creation)
let wssRef: typeof WebSocketServer | null = null;
function broadcast(obj: any) {
  const msg = JSON.stringify(obj);
  if (!wssRef) return;
  for (const client of wssRef.clients) {
    // @ts-ignore ws type
    if ((client as any).readyState === WebSocket.OPEN) (client as any).send(msg);
  }
}

// Local stub order store
type OrderStatus = 'accepted' | 'cancelled' | 'rejected' | 'unknown';
const localOrders = new Map<string, { status: OrderStatus; created: number }>();

// Health
app.get('/health', async (_req: any, res: any) => {
  if (!FORWARD_BASE) return res.json({ ok: true, ts: Date.now(), mode: 'local' }); // type: ignore
  try {
    const r = await undiciFetch(`${FORWARD_BASE}/health`, { headers: API_KEY ? { Authorization: `Bearer ${API_KEY}` } : undefined });
    const body = await r.json().catch(() => ({}));
    return res.json({ ok: r.ok, upstream: body, mode: 'forward' }); // type: ignore
  } catch (e: any) {
    return res.status(200).json({ ok: true, mode: 'degraded', error: String(e) }); // type: ignore
  }
});

// Metrics
app.get('/metrics', async (_req: any, res: any) => {
  res.set('Content-Type', register.contentType); // type: ignore
  res.end(await register.metrics()); // type: ignore
});

// Market data stub
app.get('/markets/:symbol', (req: any, res: any) => {
  const symbol = req.params.symbol; // type: ignore
  subscribeToMarket(symbol);
  res.json(getBookFn(symbol)); // type: ignore
});

// Order relay (forward if configured, otherwise stub)
app.post('/orders', async (req: any, res: any) => {
  try {
    if (FORWARD_BASE) {
      const started = Date.now();
      const r = await undiciFetch(`${FORWARD_BASE}/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {}),
        },
        body: JSON.stringify(req.body),
      });
      const text = await r.text();
      metrics.submit_total.inc({ mode: 'forward', status: r.ok ? 'success' : 'error' });
      try { broadcast({ type: 'order_ack', mode: 'forward', ts: Date.now(), status: r.ok ? 'accepted' : 'rejected' }); } catch {}
      res.status(r.status).send(text); // type: ignore
      metrics.submit_seconds.observe({ mode: 'forward' }, (Date.now() - started) / 1000);
      return;
    }
    // Local stub fallback
    placeOrderFn(req.body);
    metrics.submit_total.inc({ mode: 'local', status: 'success' });
    const id = ulid();
    localOrders.set(id, { status: 'accepted', created: Date.now() });
    try { broadcast({ type: 'order_ack', mode: 'local', ts: Date.now(), status: 'accepted', id }); } catch {}
    return res.json({ ok: true, status: 'accepted', id }); // type: ignore
  } catch (error) {
    console.error('[swift-mm] Order placement error:', error);
    metrics.submit_total.inc({ mode: FORWARD_BASE ? 'forward' : 'local', status: 'error' });
    return res.status(400).json({ // type: ignore
      error: error instanceof Error ? error.message : 'Unknown error',
      status: 'rejected'
    });
  }
});

// Cancel relay
app.post('/orders/:id/cancel', async (req: any, res: any) => {
  const { id } = req.params; // type: ignore
  try {
    if (FORWARD_BASE) {
      const r = await undiciFetch(`${FORWARD_BASE}/orders/${id}/cancel`, {
        method: 'POST',
        headers: API_KEY ? { Authorization: `Bearer ${API_KEY}` } : undefined,
      });
      const text = await r.text();
      metrics.cancel_total.inc({ mode: 'forward', status: r.ok ? 'success' : 'error' });
      try { broadcast({ type: 'cancel_ack', mode: 'forward', ts: Date.now(), status: r.ok ? 'cancelled' : 'rejected', id }); } catch {}
      return res.status(r.status).send(text); // type: ignore
    }
    // Local stub
    metrics.cancel_total.inc({ mode: 'local', status: 'success' });
    if (localOrders.has(id)) {
      const prev = localOrders.get(id)!;
      localOrders.set(id, { status: 'cancelled', created: prev.created });
    }
    try { broadcast({ type: 'cancel_ack', mode: 'local', ts: Date.now(), status: 'cancelled', id }); } catch {}
    return res.json({ ok: true, status: 'cancelled', id }); // type: ignore
  } catch (error) {
    console.error('[swift-mm] Cancel error:', error);
    metrics.cancel_total.inc({ mode: FORWARD_BASE ? 'forward' : 'local', status: 'error' });
    return res.status(400).json({ status: 'error', error: error instanceof Error ? error.message : 'Unknown error' }); // type: ignore
  }
});

// Order status (forward if configured, otherwise stub)
app.get('/orders/:id/status', async (req: any, res: any) => {
  const { id } = req.params; // type: ignore
  try {
    if (FORWARD_BASE) {
      const r = await undiciFetch(`${FORWARD_BASE}/orders/${id}/status`, {
        headers: API_KEY ? { Authorization: `Bearer ${API_KEY}` } : undefined,
      });
      const text = await r.text();
      return res.status(r.status).send(text); // type: ignore
    }
    const entry = localOrders.get(id);
    if (!entry) return res.status(404).json({ status: 'unknown', id }); // type: ignore
    return res.json({ status: entry.status, id, created: entry.created }); // type: ignore
  } catch (error) {
    console.error('[swift-mm] Status error:', error);
    return res.status(400).json({ status: 'error', id, error: error instanceof Error ? error.message : 'Unknown error' }); // type: ignore
  }
});

const server = app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`[swift-mm] listening on :${PORT} (${FORWARD_BASE ? 'forward' : 'local'} mode)`);
});

// WS relay: forward upstream stream if configured; else stub echo
const wss = new WebSocketServer({ server, path: '/ws' });
wssRef = wss;
let upstream: typeof WSWebSocket | null = null;
let upstreamConnected = false;

async function connectUpstream() {
  if (!FORWARD_WS || upstreamConnected) return;
  try {
    upstream = new WebSocket(FORWARD_WS, { headers: API_KEY ? { Authorization: `Bearer ${API_KEY}` } : undefined });
    upstream.on('open', () => {
      upstreamConnected = true;
      // eslint-disable-next-line no-console
      console.log('[swift-mm] upstream WS connected');
    });
    upstream.on('message', (buf: Buffer) => {
      const raw = buf.toString();
      try { broadcast({ type: 'upstream', ts: Date.now(), raw }); } catch {}
    });
    upstream.on('close', () => {
      upstreamConnected = false;
      // eslint-disable-next-line no-console
      console.log('[swift-mm] upstream WS closed');
    });
    upstream.on('error', (err: any) => {
      upstreamConnected = false;
      // eslint-disable-next-line no-console
      console.error('[swift-mm] upstream WS error:', err);
    });
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error('[swift-mm] failed to connect upstream WS:', e);
  }
}

wss.on('connection', (ws: any) => {
  ws.send(JSON.stringify({ type: 'hello', ts: Date.now(), mode: FORWARD_WS ? 'forward' : 'local' }));
  if (!upstreamConnected && FORWARD_WS) connectUpstream();
  ws.on('message', (msg: any) => {
    if (!FORWARD_WS) ws.send(JSON.stringify({ type: 'echo', data: msg.toString() }));
  });
});
