#!/bin/bash

# 🚀 Quick Start Script for Drift Bots v3.0 - Beta.Drift.Trade
# Usage: ./start_beta_bots.sh [--dry-run] [--mock]

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default settings
DRY_RUN=false
USE_MOCK=true
CONFIG_FILE="beta_environment_config.yaml"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --real)
      USE_MOCK=false
      shift
      ;;
    --mock)
      USE_MOCK=true
      shift
      ;;
    --config)
      CONFIG_FILE="$2"
      shift 2
      ;;
    --help|-h)
      echo "🚀 Drift Bots v3.0 - Beta.Drift.Trade Quick Start"
      echo ""
      echo "Usage:"
      echo "  $0                    # Launch in mock mode (safe)"
      echo "  $0 --real            # Launch in live mode (uses real wallet!)"
      echo "  $0 --dry-run         # Preview configuration without launching"
      echo "  $0 --config FILE     # Use custom configuration file"
      echo ""
      echo "Examples:"
      echo "  $0 --dry-run         # Safe preview"
      echo "  $0 --mock           # Test with mock client"
      echo "  $0 --real           # LIVE TRADING - USE WITH CAUTION!"
      exit 0
      ;;
    *)
      echo -e "${RED}❌ Unknown option: $1${NC}"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}🚀 Drift Bots v3.0 - Beta.Drift.Trade Launcher${NC}"
echo -e "${BLUE}=$(printf '%.0s=' {1..50})${NC}"

# Check if configuration exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Configuration file not found: $CONFIG_FILE${NC}"
    echo -e "${YELLOW}💡 Create it by copying and modifying beta_environment_config.yaml${NC}"
    exit 1
fi

# Check if wallet exists
WALLET_PATH=$(grep "maker_keypair_path:" "$CONFIG_FILE" | cut -d'"' -f2)
if [ ! -f "$WALLET_PATH" ]; then
    echo -e "${RED}❌ Wallet keypair not found: $WALLET_PATH${NC}"
    echo -e "${YELLOW}💡 Create wallet: solana-keygen new --outfile $WALLET_PATH${NC}"
    exit 1
fi

# Safety checks for live trading
if [ "$USE_MOCK" = false ]; then
    echo -e "${RED}🔥 LIVE TRADING MODE DETECTED!${NC}"
    echo -e "${YELLOW}⚠️  This will place REAL trades on beta.drift.trade${NC}"
    echo -e "${YELLOW}⚠️  Ensure your wallet has sufficient SOL for fees${NC}"
    echo -e "${YELLOW}⚠️  Risk management settings will be active${NC}"
    echo ""

    # Show wallet balance
    if command -v solana &> /dev/null; then
        WALLET_ADDRESS=$(solana-keygen pubkey "$WALLET_PATH" 2>/dev/null || echo "unknown")
        echo -e "${BLUE}👛 Wallet: $WALLET_ADDRESS${NC}"

        # Check SOL balance (if solana CLI is available)
        BALANCE=$(solana balance "$WALLET_ADDRESS" 2>/dev/null | grep -o '[0-9.]* SOL' | head -1 || echo "unknown")
        echo -e "${BLUE}💰 Balance: $BALANCE${NC}"
    fi

    echo ""
    read -p "Are you sure you want to proceed with LIVE trading? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo -e "${GREEN}✅ Launch cancelled. Switching to mock mode for safety.${NC}"
        USE_MOCK=true
    fi
fi

# Show configuration summary
echo -e "${GREEN}✅ Configuration validated${NC}"
echo -e "${BLUE}📁 Config: $CONFIG_FILE${NC}"
echo -e "${BLUE}👛 Wallet: $WALLET_PATH${NC}"
echo -e "${BLUE}🌐 Network: beta.drift.trade${NC}"
echo -e "${BLUE}🔧 Mode: $([ "$USE_MOCK" = true ] && echo 'MOCK (safe)' || echo 'LIVE (real trades!)')${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 DRY RUN MODE - Configuration preview only${NC}"
    python launch_beta_bots.py --dry-run --config "$CONFIG_FILE"
    exit 0
fi

echo ""
echo -e "${GREEN}🚀 Launching bots...${NC}"

# Launch the bots
if [ "$USE_MOCK" = true ]; then
    python launch_beta_bots.py --config "$CONFIG_FILE"
else
    # Temporarily modify config for live mode
    sed -i.bak 's/use_mock: true/use_mock: false/' "$CONFIG_FILE"
    python launch_beta_bots.py --config "$CONFIG_FILE"
    # Restore mock mode
    mv "$CONFIG_FILE.bak" "$CONFIG_FILE"
fi

echo -e "${GREEN}✅ Launch process completed!${NC}"
