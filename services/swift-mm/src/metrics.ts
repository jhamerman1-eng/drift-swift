import client from "prom-client";

// Extend the global interface to include our custom property
declare global {
  var __swift_metrics_register__: client.Registry | undefined;
}

const METRICS_PREFIX = process.env.METRICS_PREFIX || "swift_";
let register: client.Registry;
if (!global.__swift_metrics_register__) {
  register = new client.Registry();
  client.collectDefaultMetrics({ register, prefix: METRICS_PREFIX });
  global.__swift_metrics_register__ = register;
} else {
  register = global.__swift_metrics_register__;
}

const metrics = {
  submit_seconds: new client.Histogram({
    name: `${METRICS_PREFIX}submit_seconds`,
    help: "Swift submit latency seconds",
    labelNames: ["mode"],
    buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
    registers: [register],
  }),
  submit_total: new client.Counter({
    name: `${METRICS_PREFIX}submit_total`,
    help: "Swift submit count",
    labelNames: ["mode", "status"],
    registers: [register],
  }),
  cancel_seconds: new client.Histogram({
    name: `${METRICS_PREFIX}cancel_seconds`,
    help: "Swift cancel latency seconds",
    labelNames: ["mode"],
    buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
    registers: [register],
  }),
  cancel_total: new client.Counter({
    name: `${METRICS_PREFIX}cancel_total`,
    help: "Swift cancel count",
    labelNames: ["mode", "status"],
    registers: [register],
  }),
};

function timeSubmit() {
  const end = metrics.submit_seconds.startTimer({ mode: process.env.SWIFT_FORWARD_BASE ? "forward" : "local" });
  return end;
}

function timeCancel() {
  const end = metrics.cancel_seconds.startTimer({ mode: process.env.SWIFT_FORWARD_BASE ? "forward" : "local" });
  return end;
}

module.exports = { register, metrics, timeSubmit, timeCancel };
