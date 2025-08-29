export type OrderSide = 'buy' | 'sell';
export interface Order {
  symbol: string;
  side: OrderSide;
  price: number;
  size: number;
}

interface Book {
  bids: number[];
  asks: number[];
}

const books: Record<string, Book> = {};

export function subscribe(symbol: string) {
  if (!books[symbol]) {
    books[symbol] = { bids: [], asks: [] };
  }
  console.log(`[swift-mm] subscribe(${symbol}) stub`);
}

export function placeOrder(order: Order) {
  subscribe(order.symbol);
  const book = books[order.symbol];
  if (order.side === 'buy') {
    book.bids.push(order.price);
  } else {
    book.asks.push(order.price);
  }
  console.log(
    `[swift-mm] placeOrder(${order.symbol} ${order.side} @ ${order.price} x ${order.size}) stub`
  );
}

export function getBook(symbol: string): Book {
  return books[symbol] || { bids: [], asks: [] };
}
