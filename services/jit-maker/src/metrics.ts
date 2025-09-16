/**
 * Metrics collection and reporting for JIT Maker Service
 * Implements US-JIT-001 requirement for comprehensive metrics
 */

import { MetricsData } from "./types.js";

interface Counter {
  [key: string]: number;
}

interface Histogram {
  values: number[];
  count: number;
  sum: number;
}

export class MetricsCollector {
  private counters: Map<string, Counter> = new Map();
  private histograms: Map<string, Histogram> = new Map();
  private gauges: Map<string, number> = new Map();
  private startTime: number = Date.now();

  constructor() {
    // Initialize core metrics
    this.initializeMetrics();
  }

  private initializeMetrics(): void {
    // Counters for place_and_make operations
    this.counters.set("jit_place_total", {});
    this.counters.set("jit_cancel_replace_total", {});
    this.counters.set("jit_swift_orders_total", {});
    this.counters.set("jit_dedup_drops_total", {});
    this.counters.set("jit_unified_events_total", {});
    
    // Histograms for timing
    this.histograms.set("jit_request_duration_ms", { values: [], count: 0, sum: 0 });
    
    // Gauges for status
    this.gauges.set("jit_health_status", 0);
    this.gauges.set("jit_active_subscribers", 0);
  }

  // Counter operations
  inc(metric: string, labels: Record<string, string> = {}, value: number = 1): void {
    const counter = this.counters.get(metric) || {};
    const labelKey = this.buildLabelKey(labels);
    counter[labelKey] = (counter[labelKey] || 0) + value;
    this.counters.set(metric, counter);
  }

  // Histogram operations
  observe(metric: string, value: number, labels: Record<string, string> = {}): void {
    const histogram = this.histograms.get(metric) || { values: [], count: 0, sum: 0 };
    histogram.values.push(value);
    histogram.count++;
    histogram.sum += value;
    
    // Keep only recent values (sliding window)
    if (histogram.values.length > 1000) {
      const removed = histogram.values.shift()!;
      histogram.count--;
      histogram.sum -= removed;
    }
    
    this.histograms.set(metric, histogram);
  }

  // Gauge operations
  set(metric: string, value: number): void {
    this.gauges.set(metric, value);
  }

  gauge(metric: string): number {
    return this.gauges.get(metric) || 0;
  }

  // US-JIT-001: Specific metrics for decision→execute conversion
  recordDecision(alignment: string, reason: string, via: string = "jit"): void {
    this.inc("cancel_replace_total", {
      phase: "decision",
      alignment,
      reason,
      via,
      result: "ok"
    });
  }

  recordExecution(alignment: string, reason: string, via: string = "jit", result: string = "ok"): void {
    this.inc("cancel_replace_total", {
      phase: "execute", 
      alignment,
      reason,
      via,
      result
    });
  }

  recordCompletion(alignment: string, reason: string, via: string = "jit", result: string = "ok"): void {
    this.inc("cancel_replace_total", {
      phase: "complete",
      alignment,
      reason, 
      via,
      result
    });
  }

  // Health status metrics
  updateHealthStatus(healthy: boolean): void {
    this.set("jit_health_status", healthy ? 1 : 0);
  }

  updateActiveSubscribers(count: number): void {
    this.set("jit_active_subscribers", count);
  }

  // Get metrics in different formats
  getMetricsData(): MetricsData {
    const duration = this.histograms.get("jit_request_duration_ms")!;
    const sortedValues = [...duration.values].sort((a, b) => a - b);
    
    return {
      jit_place_total: this.counters.get("jit_place_total") || {},
      jit_cancel_replace_total: this.counters.get("jit_cancel_replace_total") || {},
      jit_request_duration_ms: {
        count: duration.count,
        sum: duration.sum,
        p50: this.percentile(sortedValues, 0.5),
        p95: this.percentile(sortedValues, 0.95),
        p99: this.percentile(sortedValues, 0.99),
      },
      jit_health_status: this.gauge("jit_health_status"),
      jit_active_subscribers: {
        total: this.gauge("jit_active_subscribers")
      }
    };
  }

  // Prometheus format export
  toPrometheusFormat(): string {
    const lines: string[] = [];
    const timestamp = Date.now();

    // Counters
    for (const [metricName, counter] of this.counters) {
      lines.push(`# TYPE ${metricName} counter`);
      for (const [labelKey, value] of Object.entries(counter)) {
        const labels = labelKey ? `{${labelKey}}` : "";
        lines.push(`${metricName}${labels} ${value} ${timestamp}`);
      }
    }

    // Histograms
    for (const [metricName, histogram] of this.histograms) {
      lines.push(`# TYPE ${metricName} histogram`);
      lines.push(`${metricName}_count ${histogram.count} ${timestamp}`);
      lines.push(`${metricName}_sum ${histogram.sum} ${timestamp}`);
      
      // Add buckets
      const buckets = [0.1, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000];
      const sortedValues = [...histogram.values].sort((a, b) => a - b);
      
      for (const bucket of buckets) {
        const count = sortedValues.filter(v => v <= bucket).length;
        lines.push(`${metricName}_bucket{le="${bucket}"} ${count} ${timestamp}`);
      }
      lines.push(`${metricName}_bucket{le="+Inf"} ${histogram.count} ${timestamp}`);
    }

    // Gauges
    for (const [metricName, value] of this.gauges) {
      lines.push(`# TYPE ${metricName} gauge`);
      lines.push(`${metricName} ${value} ${timestamp}`);
    }

    // Service info
    lines.push(`# TYPE jit_service_info gauge`);
    lines.push(`jit_service_info{version="1.0.0",env="${process.env.DRIFT_ENV || "unknown"}"} 1 ${timestamp}`);
    
    lines.push(`# TYPE jit_service_uptime_seconds gauge`);
    lines.push(`jit_service_uptime_seconds ${(Date.now() - this.startTime) / 1000} ${timestamp}`);

    return lines.join("\n") + "\n";
  }

  // JSON format export
  toJSON(): Record<string, unknown> {
    return {
      counters: Object.fromEntries(this.counters),
      histograms: Object.fromEntries(
        Array.from(this.histograms.entries()).map(([name, hist]) => [
          name,
          {
            count: hist.count,
            sum: hist.sum,
            avg: hist.count > 0 ? hist.sum / hist.count : 0,
            latest: hist.values[hist.values.length - 1] || 0,
          }
        ])
      ),
      gauges: Object.fromEntries(this.gauges),
      uptime_seconds: (Date.now() - this.startTime) / 1000,
      timestamp: Date.now(),
    };
  }

  private buildLabelKey(labels: Record<string, string>): string {
    const pairs = Object.entries(labels)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, value]) => `${key}="${value}"`);
    return pairs.join(",");
  }

  private percentile(sortedValues: number[], p: number): number {
    if (sortedValues.length === 0) return 0;
    const index = Math.ceil(sortedValues.length * p) - 1;
    return sortedValues[Math.max(0, Math.min(index, sortedValues.length - 1))] || 0;
  }

  // Reset metrics (useful for testing)
  reset(): void {
    this.counters.clear();
    this.histograms.clear();
    this.gauges.clear();
    this.startTime = Date.now();
    this.initializeMetrics();
  }
}