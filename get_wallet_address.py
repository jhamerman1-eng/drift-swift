import json
import yaml
from solders.keypair import Keypair

# Load configuration
cfg = yaml.safe_load(open("configs/core/drift_client.yaml", "r", encoding="utf-8"))
secret = json.load(open(cfg["wallets"]["maker_keypair_path"], "r", encoding="utf-8"))
kp = Keypair.from_bytes(bytes(secret))

print(f"Wallet public key: {kp.pubkey()}")
print(f"Wallet address: {str(kp.pubkey())}")

