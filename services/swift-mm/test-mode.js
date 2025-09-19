#!/usr/bin/env node
/**
 * Sidecar Mode Validation Test
 * Tests that sidecar mode matches SWIFT_FORWARD_BASE configuration
 */

async function testSidecarMode() {
    try {
        console.log('🔍 Testing sidecar mode...');
        
        // Wait a bit for sidecar to start
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Check health endpoint
        const response = await fetch('http://localhost:8787/health');
        const health = await response.json();
        
        console.log('Health response:', JSON.stringify(health, null, 2));
        
        // Report on upstream health
        if (health.upstream) {
            const upstream = health.upstream;
            if (upstream.ok) {
                console.log(`✅ Upstream Swift healthy: ${upstream.status} (${upstream.response_time_ms}ms)`);
            } else {
                console.log(`⚠️  Upstream Swift unhealthy: ${upstream.error || upstream.status} (${upstream.response_time_ms}ms)`);
            }
        }
        
        // Report on circuit breaker status
        if (health.circuit_breaker) {
            const cb = health.circuit_breaker;
            if (cb.degraded) {
                console.log(`⚠️  Circuit breaker OPEN: ${cb.fails}/${cb.max_fails} failures`);
            } else {
                console.log(`✅ Circuit breaker healthy: ${cb.fails}/${cb.max_fails} failures`);
            }
        }
        
        // Check mode based on SWIFT_FORWARD_BASE
        if (!process.env.SWIFT_FORWARD_BASE) {
            if (health.mode === 'local-ack') {
                console.log('✅ LOCAL_ACK mode confirmed (no SWIFT_FORWARD_BASE)');
                process.exit(0);
            } else {
                console.error('❌ Expected local-ack mode when SWIFT_FORWARD_BASE not set');
                process.exit(1);
            }
        } else {
            if (health.mode === 'forward') {
                console.log('✅ FORWARD mode confirmed with SWIFT_FORWARD_BASE');
                console.log(`   Forward base: ${health.forward || 'unknown'}`);
                process.exit(0);
            } else {
                console.error('❌ Expected forward mode when SWIFT_FORWARD_BASE is set');
                console.error(`   Got mode: ${health.mode}`);
                console.error(`   Expected forward base: ${process.env.SWIFT_FORWARD_BASE}`);
                process.exit(1);
            }
        }
    } catch (e) {
        console.error('❌ Health check failed:', e.message);
        process.exit(1);
    }
}

testSidecarMode().catch(e => {
    console.error('❌ Test failed:', e.message);
    process.exit(1);
});
