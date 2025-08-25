import client from 'prom-client';

export const register = new client.Registry();

// Default metrics
client.collectDefaultMetrics({ register });

// Custom metrics
export const httpLatency = new client.Histogram({
  name: 'swift_http_request_seconds',
  help: 'HTTP handler latency in seconds',
  labelNames: ['route', 'method', 'status'],
  buckets: [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5]
});
register.registerMetric(httpLatency);

export const orderRequests = new client.Counter({
  name: 'swift_order_requests_total',
  help: 'Total order requests',
  labelNames: ['action'] // place | cancelReplace
});
register.registerMetric(orderRequests);
