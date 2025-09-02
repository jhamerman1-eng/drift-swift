import express from "express";
import pino from "pino";
import { fetch } from "undici";
import { register, metrics, timeSubmit, timeCancel } from "./metrics.js";
import { ulid } from "ulid";

const PORT = Number(process.env.PORT ?? 8787);
const LOG_LEVEL = process.env.LOG_LEVEL ?? "info";
const SWIFT_FORWARD_BASE = process.env.SWIFT_FORWARD_BASE?.replace(/\/+$/, "");
const SWIFT_API_KEY = process.env.SWIFT_API_KEY;

const logger = pino({ level: LOG_LEVEL });
const app = express();
app.use(express.json({ limit: "1mb" }));

app.get("/health", (_req, res) => {
  res.json({
    status: "ok",
    forward: Boolean(SWIFT_FORWARD_BASE),
    version: "0.1.0",
  });
});

app.get("/metrics", async (_req, res) => {
  res.setHeader("Content-Type", register.contentType);
  res.end(await register.metrics());
});

// Submit a Swift order envelope
app.post("/orders", async (req, res) => {
  const stopTimer = timeSubmit();
  try {
    const envelope = req.body ?? {};
    if (!envelope?.message || !envelope?.signature) {
      res.status(400).json({ error: "missing message/signature" });
      return;
    }

    if (SWIFT_FORWARD_BASE) {
      const r = await fetch(`${SWIFT_FORWARD_BASE}/orders`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(SWIFT_API_KEY ? { Authorization: `Bearer ${SWIFT_API_KEY}` } : {}),
        },
        body: JSON.stringify(envelope),
      });
      const text = await r.text();
      if (!r.ok) {
        logger.warn({ status: r.status, text }, "Swift forward error");
        res.status(r.status).send(text);
        return;
      }
      try {
        const json = JSON.parse(text);
        metrics.submit_total.inc({ mode: "forward", status: "ok" });
        res.json(json);
      } catch {
        metrics.submit_total.inc({ mode: "forward", status: "text" });
        res.send(text);
      }
      return;
    }

    // Local ACK mode (no forward)
    const id = ulid();
    metrics.submit_total.inc({ mode: "local", status: "ok" });
    res.json({ status: "accepted", id });
  } catch (e: any) {
    metrics.submit_total.inc({ mode: SWIFT_FORWARD_BASE ? "forward" : "local", status: "err" });
    logger.error({ err: e?.message }, "order submit error");
    res.status(500).json({ error: "submit_failed" });
  } finally {
    stopTimer();
  }
});

// Cancel order by id
app.post("/orders/:id/cancel", async (req, res) => {
  const stopTimer = timeCancel();
  try {
    const { id } = req.params;
    if (!id) {
      res.status(400).json({ error: "missing id" });
      return;
    }
    if (SWIFT_FORWARD_BASE) {
      const r = await fetch(`${SWIFT_FORWARD_BASE}/orders/${id}/cancel`, {
        method: "POST",
        headers: {
          ...(SWIFT_API_KEY ? { Authorization: `Bearer ${SWIFT_API_KEY}` } : {}),
        },
      });
      const text = await r.text();
      if (!r.ok) {
        logger.warn({ status: r.status, text }, "Swift forward cancel error");
        res.status(r.status).send(text);
        return;
      }
      try {
        const json = JSON.parse(text);
        metrics.cancel_total.inc({ mode: "forward", status: "ok" });
        res.json(json);
      } catch {
        metrics.cancel_total.inc({ mode: "forward", status: "text" });
        res.send(text);
      }
      return;
    }
    metrics.cancel_total.inc({ mode: "local", status: "ok" });
    res.json({ status: "cancelled", id });
  } catch (e: any) {
    metrics.cancel_total.inc({ mode: SWIFT_FORWARD_BASE ? "forward" : "local", status: "err" });
    logger.error({ err: e?.message }, "order cancel error");
    res.status(500).json({ error: "cancel_failed" });
  } finally {
    stopTimer();
  }
});

app.listen(PORT, () => {
  logger.info({ port: PORT, forward: Boolean(SWIFT_FORWARD_BASE) }, "swift-mm sidecar up");
});
