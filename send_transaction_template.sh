#!/bin/bash

# Solana Transaction Sender Template
# Replace ENTER_ENCODED_TRANSACTION_ID with your actual base64-encoded transaction

curl https://thrumming-omniscient-moon.solana-devnet.quiknode.pro/ea7a129663c942e13ce1c9b414c3a8da9ab7d1d9/ \
  -X POST \
  -H "Content-Type: application/json" \
  --data '{
    "method": "sendTransaction",
    "params": ["ENTER_ENCODED_TRANSACTION_ID"],
    "id": 1,
    "jsonrpc": "2.0"
  }'

