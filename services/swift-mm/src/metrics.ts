import client, { Histogram, Registry, Counter } from "prom-client";

const METRICS_PREFIX = process.env.METRICS_PREFIX ?? "swift_";
export const register = new Registry();
client.collectDefaultMetrics({ register, prefix: METRICS_PREFIX });

export const metrics = {
  submit_seconds: new Histogram({
    name: `${METRICS_PREFIX}submit_seconds`,
    help: "Swift submit latency seconds",
    labelNames: ["mode"],
    buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
    registers: [register],
  }),
  submit_total: new Counter({
    name: `${METRICS_PREFIX}submit_total`,
    help: "Swift submit count",
    labelNames: ["mode", "status"],
    registers: [register],
  }),
  cancel_seconds: new Histogram({
    name: `${METRICS_PREFIX}cancel_seconds`,
    help: "Swift cancel latency seconds",
    labelNames: ["mode"],
    buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
    registers: [register],
  }),
  cancel_total: new Counter({
    name: `${METRICS_PREFIX}cancel_total`,
    help: "Swift cancel count",
    labelNames: ["mode", "status"],
    registers: [register],
  }),
};

export function timeSubmit() {
  const end = metrics.submit_seconds.startTimer({ mode: process.env.SWIFT_FORWARD_BASE ? "forward" : "local" });
  return end;
}

export function timeCancel() {
  const end = metrics.cancel_seconds.startTimer({ mode: process.env.SWIFT_FORWARD_BASE ? "forward" : "local" });
  return end;
}
