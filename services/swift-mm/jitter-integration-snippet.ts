/**
 * Integration snippet for existing Swift MM sidecar
 * 
 * Add these lines to your existing services/swift-mm/src/index.ts
 * or similar main TypeScript sidecar file to enable jitter control.
 */

// Add this import at the top
import { 
  handleJitterControl, 
  getJitterConfig, 
  shouldProcessShotgun, 
  shouldProcessSniper,
  getClipSize,
  getJitterHealth
} from './jitter-control';

// Add these routes to your Express app
app.post('/control/jitter', handleJitterControl);
app.get('/control/jitter', getJitterConfig);

// Add jitter health to your existing health endpoint
app.get('/health', (req, res) => {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    // ... your existing health checks
    jitter: getJitterHealth()  // Add this line
  };
  
  res.json(health);
});

// Example integration in your order processing logic
// (modify your existing order processing to include these checks)

/*
async function processSwiftOrder(orderData: any) {
  try {
    // Determine which strategies should process this order
    const shouldShotgun = shouldProcessShotgun(orderData);
    const shouldSniper = shouldProcessSniper(orderData);
    
    if (shouldShotgun) {
      const clipSize = getClipSize('shotgun');
      await processShotgunOrder(orderData, clipSize);
    }
    
    if (shouldSniper) {
      const clipSize = getClipSize('sniper');
      await processSniperOrder(orderData, clipSize);
    }
    
    // Continue with your existing logic...
    
  } catch (error) {
    console.error('Order processing error:', error);
  }
}

async function processShotgunOrder(orderData: any, clipSize: number) {
  // Your shotgun-specific order processing
  console.log(`🔫 Shotgun: ${clipSize} SOL clip`);
  // Place smaller, broad orders
}

async function processSniperOrder(orderData: any, clipSize: number) {
  // Your sniper-specific order processing  
  console.log(`🎯 Sniper: ${clipSize} SOL clip`);
  // Place larger, selective orders
}
*/

// That's it! Your TypeScript sidecar now supports jitter control.




