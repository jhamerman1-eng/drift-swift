const books: { [key: string]: { bids: any[], asks: any[] } } = {};

function subscribe(symbol: string) {
  if (!books[symbol]) {
    books[symbol] = { bids: [], asks: [] };
  }
  console.log(`[swift-mm] subscribe(${symbol}) stub`);
}

async function placeOrder(order: any) {
  // Handle both simple Order format and complex envelope format
  let orderData;

  if (order.symbol && order.side && order.price && order.size) {
    // Simple format
    orderData = order;
  } else if (order.message && order.signature) {
    // Envelope format with signature - try to place on-chain
    console.log(`[swift-mm] Attempting to place envelope order on-chain...`);

    // TODO: Implement actual on-chain order placement
    // This would require connecting to DriftPy and placing the order
    console.log(`[swift-mm] Envelope order: message=${order.message.substring(0, 50)}..., signature=${order.signature.substring(0, 50)}...`);

    // For now, fall back to stub mode but log the intent
    orderData = {
      symbol: 'SOL-PERP',
      side: order.side || 'buy',
      price: order.price || 200,
      size: order.size || 0.01
    };
    console.log(`[swift-mm] FALLBACK: Using stub mode - order NOT placed on-chain`);
  } else {
    throw new Error('Invalid order format: missing required fields');
  }

  subscribe(orderData.symbol);
  const book = books[orderData.symbol];
  if (orderData.side === 'buy') {
    book.bids.push(orderData.price);
  } else {
    book.asks.push(orderData.price);
  }
  console.log(
    `[swift-mm] placeOrder(${orderData.symbol} ${orderData.side} @ ${orderData.price} x ${orderData.size}) STUB - NOT ON-CHAIN`
  );
}

function getBook(symbol: string) {
  return books[symbol] || { bids: [], asks: [] };
}

module.exports = { subscribe, placeOrder, getBook };
