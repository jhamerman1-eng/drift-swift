import express from "express";
import fetch, { RequestInit } from "node-fetch";
import { v4 as uuid } from "uuid";

const app = express();
app.use(express.json());

const PORT = Number(process.env.PORT || 8787);
const FORWARD_BASE = (process.env.SWIFT_FORWARD_BASE || "").replace(/\/+$/,"");
const API_KEY = process.env.SWIFT_API_KEY || "";

// ⚠️  FAIL FAST: Require SWIFT_FORWARD_BASE to be configured for production
if (!FORWARD_BASE) {
  console.error("❌ SWIFT_FORWARD_BASE is required but not configured!");
  console.error("Please set SWIFT_FORWARD_BASE in your environment variables.");
  console.error("Example: SWIFT_FORWARD_BASE=https://swift.drift.trade");
  console.error("This will run in LOCAL_ACK mode which is for testing only.");
  console.error("For production, you MUST configure SWIFT_FORWARD_BASE.");
  // Don't exit immediately - allow LOCAL_ACK mode for testing
  // process.exit(1);
}

const LOCAL_ACK = !FORWARD_BASE; // only if no forward base configured

// Circuit breaker (optional but nice)
// Flip to 503 degraded after N consecutive 5xx/timeouts to force bot fallback.
let fails = 0; const WINDOW = 30_000, MAX_FAILS = 3; let t0 = Date.now();
function record(ok: boolean) {
  if (Date.now() - t0 > WINDOW) { fails = 0; t0 = Date.now(); }
  fails = ok ? 0 : fails + 1;
}
function degraded() { return fails >= MAX_FAILS; }

app.get("/health", async (_req, res) => {
  // Enhanced upstream probe to confirm Swift is reachable (not just that sidecar booted)
  let upstream: { ok: boolean; status?: number; response_time_ms?: number; error?: string } = { ok: false };
  
  if (!LOCAL_ACK) {
    const startTime = Date.now();
    try {
      console.log(`[upstream] Testing connection to: ${FORWARD_BASE}/health`);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1000);
      
      const r = await fetch(`${FORWARD_BASE}/health`, { 
        method: "GET",
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      const responseTime = Date.now() - startTime;
      upstream = { 
        ok: r.ok, 
        status: r.status,
        response_time_ms: responseTime
      };
      
      // Log upstream health for observability
      if (r.ok) {
        console.log(`[upstream] Swift reachable: ${r.status} (${responseTime}ms)`);
      } else {
        console.warn(`[upstream] Swift unhealthy: ${r.status} (${responseTime}ms)`);
      }
      
    } catch (e: any) {
      const responseTime = Date.now() - startTime;
      upstream = { 
        ok: false, 
        response_time_ms: responseTime,
        error: e.name === 'AbortError' ? 'timeout' : 'network_error'
      };
      console.warn(`[upstream] Swift unreachable: ${e.message} (${responseTime}ms)`);
    }
  }

  // Determine overall health status
  const overallOk = LOCAL_ACK || upstream.ok;
  const statusCode = overallOk ? 200 : 503;

  res.status(statusCode).json({
    ok: overallOk,
    service: "swift-mm-sidecar",
    version: process.env.SIDECAR_VERSION || "dev",
    mode: LOCAL_ACK ? "local-ack" : "forward",
    forward: FORWARD_BASE || null,
    upstream,
    circuit_breaker: {
      fails: fails,
      degraded: degraded(),
      window_ms: WINDOW,
      max_fails: MAX_FAILS
    }
  });
});

app.post("/orders", async (req, res) => {
  if (LOCAL_ACK || degraded()) {
    return res.status(503).json({
      status: "degraded",
      forwarded: false,
      reason: LOCAL_ACK ? "LOCAL_ACK" : "circuit_open"
    });
  }

  try {
    // Idempotency keys (no dup submits on retries)
    const reqIdem = (req.headers["idempotency-key"] ?? uuid()).toString();

    // Short timeouts + error bubbling
    const r = await fetch(`${FORWARD_BASE}/orders`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "Idempotency-Key": reqIdem,
        ...(API_KEY ? { "x-api-key": API_KEY } : {})
      },
      body: JSON.stringify(req.body),
      // node-fetch v3 uses AbortController; undici has 'dispatcher' opts — keep it short
      // @ts-ignore
      signal: AbortSignal.timeout(2500)
    });

    const text = await r.text();
    record(r.ok);
    return res.status(r.status).type("application/json").send(text);
  } catch (e: any) {
    record(false);
    return res.status(502).json({ error: "Sidecar forward failed", detail: String(e) });
  }
});

app.listen(PORT, () => {
  console.log(`[sidecar] :${PORT} mode=${LOCAL_ACK ? "local-ack" : "forward"} forward=${FORWARD_BASE || "-"}`);
});