#!/usr/bin/env python3
"""
Simple HTTP sidecar service for testing
"""

import http.server
import json
import socketserver
import time
from urllib.parse import urlparse, parse_qs

class SidecarHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "ok", "forward": True, "version": "0.1.0"}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/orders':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                order_data = json.loads(post_data.decode('utf-8'))
                
                # Log the received order
                print(f"[SIDECAR] Received order: {json.dumps(order_data, indent=2)}")
                
                # Validate required fields
                required_fields = ['symbol', 'side', 'price', 'size']
                for field in required_fields:
                    if field not in order_data:
                        self.send_response(400)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        response = {"error": f"Missing required field: {field}"}
                        self.wfile.write(json.dumps(response).encode())
                        return
                
                # Validate side
                if order_data['side'] not in ['buy', 'sell']:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {"error": "Invalid side: must be 'buy' or 'sell'"}
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                # Validate price and size
                if order_data['price'] <= 0 or order_data['size'] <= 0:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {"error": "Price and size must be positive"}
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                # Simulate successful order placement
                order_id = f"ORDER-{int(time.time() * 1000) % 1000000:06d}"
                
                print(f"[SIDECAR] Order placed successfully: {order_id}")
                print(f"  Symbol: {order_data['symbol']}")
                print(f"  Side: {order_data['side']}")
                print(f"  Price: {order_data['price']}")
                print(f"  Size: {order_data['size']}")
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    "ok": True,
                    "status": "accepted",
                    "id": order_id,
                    "message": f"Order {order_data['side']} {order_data['size']} {order_data['symbol']} @ {order_data['price']} placed successfully"
                }
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                print(f"[SIDECAR] Error processing order: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"error": str(e)}
                self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

if __name__ == "__main__":
    PORT = 8787
    print(f"Starting simple Swift sidecar on port {PORT}...")
    
    with socketserver.TCPServer(("", PORT), SidecarHandler) as httpd:
        print(f"Sidecar running on http://localhost:{PORT}")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down sidecar...")
            httpd.shutdown()
















