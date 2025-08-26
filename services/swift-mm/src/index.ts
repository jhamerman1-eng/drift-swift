import express from 'express';
import client from 'prom-client';
import { WebSocketServer } from 'ws';

const app = express();
const register = new client.Registry();
client.collectDefaultMetrics({ register });

const PORT = parseInt(process.env.PORT || '8787', 10);

// Health
app.get('/health', (_req, res) => res.json({ ok: true, ts: Date.now() }));

// Metrics
app.get('/metrics', async (_req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
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
