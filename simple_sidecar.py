#!/usr/bin/env python3
"""
Simple Swift sidecar service for testing
"""

from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "forward": True, "version": "0.1.0"})

@app.route('/orders', methods=['POST'])
def place_order():
    try:
        order_data = request.get_json()
        
        # Log the received order
        print(f"[SIDECAR] Received order: {json.dumps(order_data, indent=2)}")
        
        # Validate required fields
        required_fields = ['symbol', 'side', 'price', 'size']
        for field in required_fields:
            if field not in order_data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate side
        if order_data['side'] not in ['buy', 'sell']:
            return jsonify({"error": "Invalid side: must be 'buy' or 'sell'"}), 400
        
        # Validate price and size
        if order_data['price'] <= 0 or order_data['size'] <= 0:
            return jsonify({"error": "Price and size must be positive"}), 400
        
        # Simulate successful order placement
        order_id = f"ORDER-{int(time.time() * 1000) % 1000000:06d}"
        
        print(f"[SIDECAR] Order placed successfully: {order_id}")
        print(f"  Symbol: {order_data['symbol']}")
        print(f"  Side: {order_data['side']}")
        print(f"  Price: {order_data['price']}")
        print(f"  Size: {order_data['size']}")
        
        return jsonify({
            "ok": True,
            "status": "accepted",
            "id": order_id,
            "message": f"Order {order_data['side']} {order_data['size']} {order_data['symbol']} @ {order_data['price']} placed successfully"
        })
        
    except Exception as e:
        print(f"[SIDECAR] Error processing order: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import time
    print("Starting simple Swift sidecar on port 8787...")
    app.run(host='0.0.0.0', port=8787, debug=True)
















