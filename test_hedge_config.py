#!/usr/bin/env python3
import yaml

print('Checking hedge configuration...')
try:
    with open('configs/hedge/routing.yaml', 'r') as f:
        config = yaml.safe_load(f)
    print('✅ Configuration loaded successfully')
    hedge_config = config.get('hedge', {})
    print(f'Hedge enabled: {hedge_config.get("enabled", False)}')
    sub_account = hedge_config.get('sub_account', {})
    print(f'Sub-account: {sub_account.get("name", "N/A")}')
    routes = hedge_config.get('route', [])
    print(f'Routes: {len(routes)}')
    for i, route in enumerate(routes, 1):
        print(f'  {i}. {route.get("venue", "N/A")} - {route.get("mode", "N/A")}')
except Exception as e:
    print(f'❌ Configuration error: {e}')


