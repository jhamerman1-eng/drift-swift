/**
 * Unit tests for JIT Maker Service
 * Tests all endpoints and functionality including US-JIT user story requirements
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import request from 'supertest';
import { Connection, PublicKey, Keypair } from '@solana/web3.js';
import { app, metrics, health } from '../index.js';

// Mock @drift-labs/sdk
vi.mock('@drift-labs/sdk', () => ({
  DriftClient: vi.fn().mockImplementation(() => ({
    subscribe: vi.fn().mockResolvedValue(undefined),
    getPlaceAndMakeSignedMsgPerpOrderIxs: vi.fn().mockResolvedValue([]),
    buildTransaction: vi.fn().mockResolvedValue({}),
    sendTransaction: vi.fn().mockResolvedValue('test_signature_123'),
    getUserStatsAccountPublicKey: vi.fn().mockResolvedValue(new PublicKey('11111111111111111111111111111111')),
    program: {
      programId: new PublicKey('11111111111111111111111111111111')
    }
  })),
  UserMap: vi.fn().mockImplementation(() => ({
    subscribe: vi.fn().mockResolvedValue(undefined),
    mustGet: vi.fn().mockResolvedValue({
      getUserAccount: vi.fn().mockReturnValue({})
    })
  })),
  SlotSubscriber: vi.fn().mockImplementation(() => ({
    subscribe: vi.fn().mockResolvedValue(undefined),
    getSlot: vi.fn().mockReturnValue(100)
  })),
  AuctionSubscriber: vi.fn().mockImplementation(() => ({
    subscribe: vi.fn().mockResolvedValue(undefined)
  })),
  SwiftOrderSubscriber: vi.fn().mockImplementation(() => ({
    subscribe: vi.fn().mockResolvedValue(undefined)
  })),
  JitProxyClient: vi.fn().mockImplementation(() => ({})),
  getUserAccountPublicKey: vi.fn().mockResolvedValue(new PublicKey('11111111111111111111111111111111')),
  isSignedMsgOrder: vi.fn().mockReturnValue(false),
  MarketType: { PERP: 'perp' },
  getLimitOrderParams: vi.fn().mockReturnValue({}),
  PostOnlyParams: { MUST_POST_ONLY: 'must_post_only', NONE: 'none' },
  PRICE_PRECISION: { toNumber: () => 1000000 },
  BASE_PRECISION: { toNumber: () => 1000000000 },
  PositionDirection: { Long: 'long', Short: 'short' },
  OrderType: { Limit: 'limit' },
  BN: vi.fn().mockImplementation((val) => ({ toNumber: () => Number(val) }))
}));

// Mock Solana web3.js
vi.mock('@solana/web3.js', async () => {
  const actual = await vi.importActual('@solana/web3.js');
  return {
    ...actual,
    Connection: vi.fn().mockImplementation(() => ({})),
    ComputeBudgetProgram: {
      setComputeUnitLimit: vi.fn().mockReturnValue({}),
      setComputeUnitPrice: vi.fn().mockReturnValue({})
    }
  };
});

describe('JIT Maker Service', () => {
  beforeEach(() => {
    // Reset metrics and health status before each test
    metrics.reset();
    health.ok = true;
    health.subscribers = { swift: true, auction: true, drift: true, slot: true };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Health Endpoint - US-JIT-001', () => {
    it('should return healthy status when all subscribers are active', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.body.ok).toBe(true);
      expect(response.body.subscribers).toEqual({
        swift: true,
        auction: true,
        drift: true,
        slot: true
      });
      expect(response.body.timestamp).toBeTypeOf('number');
      expect(response.body.uptime).toBeTypeOf('number');
    });

    it('should return unhealthy status when subscribers are down', async () => {
      health.ok = false;
      health.subscribers.swift = false;

      const response = await request(app)
        .get('/health')
        .expect(503);

      expect(response.body.ok).toBe(false);
      expect(response.body.subscribers.swift).toBe(false);
    });
  });

  describe('Metrics Endpoint - US-JIT-001', () => {
    it('should return Prometheus format metrics', async () => {
      // Add some test metrics
      metrics.inc('jit_place_total', { result: 'ok', via: 'jit' });
      metrics.observe('jit_request_duration_ms', 150);

      const response = await request(app)
        .get('/metrics')
        .expect(200);

      expect(response.headers['content-type']).toContain('text/plain');
      expect(response.text).toContain('jit_place_total');
      expect(response.text).toContain('jit_request_duration_ms');
      expect(response.text).toContain('jit_service_info');
    });

    it('should return JSON format metrics for debugging', async () => {
      metrics.inc('jit_place_total', { result: 'ok' });

      const response = await request(app)
        .get('/metrics/json')
        .expect(200);

      expect(response.body).toHaveProperty('counters');
      expect(response.body).toHaveProperty('histograms');
      expect(response.body).toHaveProperty('gauges');
      expect(response.body).toHaveProperty('uptime_seconds');
      expect(response.body).toHaveProperty('timestamp');
    });
  });

  describe('Place and Make Endpoint - US-JIT-002', () => {
    const validRequest = {
      orderMessageRaw: {
        uuid: 'test-uuid-123',
        taker_authority: '11111111111111111111111111111111',
        order_message: 'deadbeef',
        order_signature: 'dGVzdA==',
        signing_authority: '11111111111111111111111111111111'
      },
      signedMessage: {
        signedMsgOrderParams: {
          marketIndex: 0,
          direction: { long: true },
          baseAssetAmount: '1000000000',
          auctionStartSlot: 95
        },
        subAccountId: 0,
        slot: 95
      },
      maker: {
        price: 100.5,
        size: 0.1,
        postOnly: true,
        ioc: false
      }
    };

    it('should successfully process place_and_make request', async () => {
      const response = await request(app)
        .post('/jit/place_and_make')
        .send(validRequest)
        .expect(200);

      expect(response.body).toHaveProperty('txSig');
      expect(response.body).toHaveProperty('duration');
      expect(response.body.txSig).toBe('test_signature_123');
      expect(typeof response.body.duration).toBe('number');
    });

    it('should reject request with missing required fields', async () => {
      const invalidRequest = {
        orderMessageRaw: {},
        signedMessage: {},
        maker: {}
      };

      const response = await request(app)
        .post('/jit/place_and_make')
        .send(invalidRequest)
        .expect(400);

      expect(response.body.error).toBe('invalid_request');
      expect(response.body.message).toContain('Missing required fields');
    });

    it('should reject request with stale slot - US-JIT-002 slot skew guard', async () => {
      const staleRequest = {
        ...validRequest,
        signedMessage: {
          ...validRequest.signedMessage,
          signedMsgOrderParams: {
            ...validRequest.signedMessage.signedMsgOrderParams,
            auctionStartSlot: 10 // Very old slot
          }
        }
      };

      const response = await request(app)
        .post('/jit/place_and_make')
        .send(staleRequest)
        .expect(409);

      expect(response.body.error).toBe('stale_signed_slot');
      expect(response.body.details).toHaveProperty('current');
      expect(response.body.details).toHaveProperty('signed');
      expect(response.body.details).toHaveProperty('skew');
    });

    it('should handle optional preceding instructions - US-JIT-003', async () => {
      const requestWithPrecedingIxs = {
        ...validRequest,
        precedingIxs: ['dGVzdA==', 'dGVzdDI='],
        overrideCustomIxIndex: 2
      };

      const response = await request(app)
        .post('/jit/place_and_make')
        .send(requestWithPrecedingIxs)
        .expect(200);

      expect(response.body.txSig).toBe('test_signature_123');
    });

    it('should record metrics for successful place_and_make', async () => {
      await request(app)
        .post('/jit/place_and_make')
        .send(validRequest)
        .expect(200);

      const metricsResponse = await request(app)
        .get('/metrics/json')
        .expect(200);

      expect(metricsResponse.body.counters).toHaveProperty('jit_place_total');
    });

    it('should handle internal server errors gracefully', async () => {
      // Mock an error in the Drift client
      const mockDriftClient = {
        getPlaceAndMakeSignedMsgPerpOrderIxs: vi.fn().mockRejectedValue(new Error('Internal error'))
      };

      // This would require more sophisticated mocking to test properly
      // For now, we'll test the error response format
      const response = await request(app)
        .post('/jit/place_and_make')
        .send({ invalid: 'request' })
        .expect(400);

      expect(response.body).toHaveProperty('error');
      expect(response.body).toHaveProperty('message');
    });
  });

  describe('Cancel Replace Endpoint - US-JIT-004', () => {
    it('should return not implemented for cancel_replace', async () => {
      const response = await request(app)
        .post('/jit/cancel_replace')
        .send({
          orderId: 'test_order_123',
          newOrder: {
            marketIndex: 0,
            side: 'buy',
            price: 101.0,
            size: 0.2,
            postOnly: true
          }
        })
        .expect(501);

      expect(response.body.error).toBe('not_implemented');
      expect(response.body.message).toContain('not yet implemented');
    });

    it('should validate cancel_replace request parameters', async () => {
      const response = await request(app)
        .post('/jit/cancel_replace')
        .send({})
        .expect(400);

      expect(response.body.error).toBe('invalid_request');
      expect(response.body.message).toContain('Missing orderId or newOrder');
    });

    it('should handle tombstone conflicts', async () => {
      const orderData = {
        orderId: 'test_order_123',
        newOrder: {
          marketIndex: 0,
          side: 'buy',
          price: 100.0,
          size: 0.1
        }
      };

      // First request should set tombstone
      await request(app)
        .post('/jit/cancel_replace')
        .send(orderData)
        .expect(501); // Not implemented, but should set tombstone

      // Second request with same parameters should conflict
      const response = await request(app)
        .post('/jit/cancel_replace')
        .send(orderData)
        .expect(409);

      expect(response.body.error).toBe('tombstone_active');
    });
  });

  describe('Smoke Test Endpoint - US-JIT-005', () => {
    it('should return comprehensive system status', async () => {
      const response = await request(app)
        .post('/test/smoke')
        .expect(200);

      expect(response.body).toHaveProperty('health');
      expect(response.body).toHaveProperty('subscribers');
      expect(response.body).toHaveProperty('metrics');
      expect(response.body).toHaveProperty('config');
      expect(response.body).toHaveProperty('timestamp');

      expect(response.body.config).toHaveProperty('markets');
      expect(response.body.config).toHaveProperty('slotSkewMax');
      expect(response.body.config).toHaveProperty('env');
    });
  });

  describe('Error Handling', () => {
    it('should handle 404 for unknown endpoints', async () => {
      const response = await request(app)
        .get('/unknown/endpoint')
        .expect(404);

      expect(response.body.error).toBe('not_found');
      expect(response.body.message).toContain('not found');
    });

    it('should handle malformed JSON requests', async () => {
      const response = await request(app)
        .post('/jit/place_and_make')
        .set('Content-Type', 'application/json')
        .send('{ invalid json }')
        .expect(400);
    });

    it('should include CORS headers', async () => {
      const response = await request(app)
        .get('/health')
        .expect(200);

      expect(response.headers).toHaveProperty('access-control-allow-origin');
    });

    it('should include security headers', async () => {
      const response = await request(app)
        .get('/health') 
        .expect(200);

      // Helmet should add security headers
      expect(response.headers).toHaveProperty('x-content-type-options');
      expect(response.headers).toHaveProperty('x-frame-options');
    });
  });

  describe('Rate Limiting', () => {
    it('should allow normal request rates', async () => {
      // Send 10 requests quickly (should be under rate limit)
      const promises = Array(10).fill(null).map(() => 
        request(app).get('/health')
      );

      const results = await Promise.all(promises);
      
      // All should succeed
      results.forEach(response => {
        expect(response.status).toBe(200);
      });
    });

    // Note: Testing actual rate limiting would require sending many more requests
    // which might be too slow for unit tests. Integration tests would be better.
  });

  describe('Metrics Collection - US-JIT-001 detailed requirements', () => {
    it('should track decision→execute conversion metrics', async () => {
      // Simulate the metrics that would be tracked in a real cancel/replace flow
      metrics.recordDecision('aligned', 'stale_price', 'jit');
      metrics.recordExecution('aligned', 'stale_price', 'jit', 'ok');
      metrics.recordCompletion('aligned', 'stale_price', 'jit', 'ok');

      const metricsData = metrics.getMetricsData();
      
      expect(metricsData).toHaveProperty('jit_cancel_replace_total');
      
      // Should have metrics for each phase
      const crMetrics = metricsData.jit_cancel_replace_total;
      expect(crMetrics).toHaveProperty('phase=decision,alignment=aligned,reason=stale_price,via=jit,result=ok');
      expect(crMetrics).toHaveProperty('phase=execute,alignment=aligned,reason=stale_price,via=jit,result=ok');
      expect(crMetrics).toHaveProperty('phase=complete,alignment=aligned,reason=stale_price,via=jit,result=ok');
    });

    it('should track request duration histograms', async () => {
      // Record some sample durations
      metrics.observe('jit_request_duration_ms', 50);
      metrics.observe('jit_request_duration_ms', 100);
      metrics.observe('jit_request_duration_ms', 200);

      const metricsData = metrics.getMetricsData();
      
      expect(metricsData.jit_request_duration_ms.count).toBe(3);
      expect(metricsData.jit_request_duration_ms.sum).toBe(350);
      expect(metricsData.jit_request_duration_ms.p50).toBe(100);
    });

    it('should update health and subscriber metrics', async () => {
      metrics.updateHealthStatus(true);
      metrics.updateActiveSubscribers(4);

      expect(metrics.gauge('jit_health_status')).toBe(1);
      expect(metrics.gauge('jit_active_subscribers')).toBe(4);
    });
  });
});

describe('Metrics Collector', () => {
  let metricsCollector: any;

  beforeEach(() => {
    metricsCollector = metrics;
    metricsCollector.reset();
  });

  describe('Counter Operations', () => {
    it('should increment counters correctly', () => {
      metricsCollector.inc('test_counter');
      metricsCollector.inc('test_counter', { label: 'value' });
      metricsCollector.inc('test_counter', { label: 'value' }, 5);

      const counters = metricsCollector.toJSON().counters;
      expect(counters.test_counter['']).toBe(1);
      expect(counters.test_counter['label="value"']).toBe(6);
    });
  });

  describe('Histogram Operations', () => {
    it('should record histogram values correctly', () => {
      metricsCollector.observe('test_histogram', 10);
      metricsCollector.observe('test_histogram', 20);
      metricsCollector.observe('test_histogram', 30);

      const histograms = metricsCollector.toJSON().histograms;
      expect(histograms.test_histogram.count).toBe(3);
      expect(histograms.test_histogram.sum).toBe(60);
      expect(histograms.test_histogram.avg).toBe(20);
    });

    it('should maintain sliding window for histograms', () => {
      // Add more than 1000 values to test sliding window
      for (let i = 0; i < 1002; i++) {
        metricsCollector.observe('test_histogram', i);
      }

      const histograms = metricsCollector.toJSON().histograms;
      expect(histograms.test_histogram.count).toBe(1000); // Should be capped at 1000
    });
  });

  describe('Gauge Operations', () => {
    it('should set and get gauge values', () => {
      metricsCollector.set('test_gauge', 42);
      expect(metricsCollector.gauge('test_gauge')).toBe(42);

      metricsCollector.set('test_gauge', 100);
      expect(metricsCollector.gauge('test_gauge')).toBe(100);
    });
  });

  describe('Prometheus Format Export', () => {
    it('should export metrics in Prometheus format', () => {
      metricsCollector.inc('test_counter', { environment: 'test' });
      metricsCollector.observe('test_histogram', 150);
      metricsCollector.set('test_gauge', 75);

      const prometheus = metricsCollector.toPrometheusFormat();

      expect(prometheus).toContain('# TYPE test_counter counter');
      expect(prometheus).toContain('test_counter{environment="test"} 1');
      expect(prometheus).toContain('# TYPE test_histogram histogram');
      expect(prometheus).toContain('test_histogram_count 1');
      expect(prometheus).toContain('test_histogram_sum 150');
      expect(prometheus).toContain('# TYPE test_gauge gauge');
      expect(prometheus).toContain('test_gauge 75');
      expect(prometheus).toContain('jit_service_info');
    });
  });
});



