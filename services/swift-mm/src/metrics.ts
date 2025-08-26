import client from 'prom-client';
export const quotesCounter = new client.Counter({
  name: 'swift_quotes_total',
  help: 'Quotes relayed (stub)',
});
