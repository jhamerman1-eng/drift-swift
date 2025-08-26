# Swift MM Sidecar (Scaffold)

A minimal TypeScript service that would sit between the Python bot and Drift Swift components.
This version exposes `/health` and `/metrics` and stubs a WS endpoint.

## Dev
```bash
cd services/swift-mm
npm install
npm run build
node dist/index.js
```

Or via Docker:
```bash
docker build -t swift-mm:rc2 .
docker run -p 8787:8787 swift-mm:rc2
```
