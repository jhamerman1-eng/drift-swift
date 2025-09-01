# Example environment for Swift MM Sidecar
# Copy to .env.swift and edit safely (do NOT commit real secrets)

# If set, forward to real Swift (e.g., https://swift.drift.trade)
SWIFT_FORWARD_BASE=

# Optional: API key/header if Swift requires
SWIFT_API_KEY=

# Sidecar server
PORT=8787
LOG_LEVEL=info

# Prometheus
METRICS_ENABLED=true
METRICS_PREFIX=swift_
