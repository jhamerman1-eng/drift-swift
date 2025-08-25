import { DriftClient } from '@drift-labs/sdk';
import { BN } from '@drift-labs/sdk';

export type MarketMeta = {
  tickSize: number; // price tick
  lotSize: number;  // base asset lot
};

// Attempt to infer from market; fallback to env vars
export async function loadMarketMeta(client: DriftClient, marketIndex: number): Promise<MarketMeta> {
  try {
    const m = client.getPerpMarketAccount(marketIndex);
    // Heuristic defaults; replace with real mapping from your market metadata:
    // Developers often derive ticks from 'amm' params + oracle precision.
    // For devnet, use conservative defaults if fields not present.
    const tickSize = Number(process.env.SWIFT_TICK_SIZE || 0.01);
    const lotSize  = Number(process.env.SWIFT_LOT_SIZE || 0.001);
    return { tickSize, lotSize };
  } catch {
    return {
      tickSize: Number(process.env.SWIFT_TICK_SIZE || 0.01),
      lotSize: Number(process.env.SWIFT_LOT_SIZE || 0.001)
    };
  }
}

export function toTicks(p: number, tickSize: number): BN {
  const ticks = Math.round(p / tickSize);
  return new BN(ticks);
}

export function toLots(sz: number, lotSize: number): BN {
  const lots = Math.round(sz / lotSize);
  return new BN(lots);
}
