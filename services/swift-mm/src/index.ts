import express from 'express';
import client from 'prom-client';
import { WebSocketServer } from 'ws';
import { subscribe, placeOrder, getBook } from './market';
import { quotesCounter } from './metrics';

const app = express();
const register = new client.Registry();
client.collectDefaultMetrics({ register });
app.use(express.json());

const PORT = parseInt(process.env.PORT || '8787', 10);

// Health
app.get('/health', (_req, res) => res.json({ ok: true, ts: Date.now() }));

// Metrics
app.get('/metrics', async (_req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

// Market data stub
app.get('/markets/:symbol', (req, res) => {
  const symbol = req.params.symbol;
  subscribe(symbol);
  res.json(getBook(symbol));
});

// Order relay stub
app.post('/orders', (req, res) => {
  placeOrder(req.body);
  quotesCounter.inc();
  res.json({ ok: true });
});

const server = app.listen(PORT, () => {
  console.log(`[swift-mm] listening on :${PORT}`);
});

// Stub WS relay
const wss = new WebSocketServer({ server, path: '/ws' });
wss.on('connection', (ws) => {
  ws.send(JSON.stringify({ type: 'hello', ts: Date.now(), stub: true }));
  ws.on('message', (msg) => {
    // Echo for now
    ws.send(JSON.stringify({ type: 'echo', data: msg.toString() }));
  });
});
