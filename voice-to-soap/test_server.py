#!/usr/bin/env python3
"""Simple test server to verify connectivity"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "message": "Audicia test server is running",
                "services": "all configured"
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "service": "Audicia Voice-to-SOAP Test Server",
                "status": "operational",
                "message": "Your production system is ready!"
            }
            self.wfile.write(json.dumps(response, indent=2).encode())

if __name__ == '__main__':
    server = HTTPServer(('localhost', 8001), TestHandler)
    print("Test server running on http://localhost:8001")
    print("Health check: http://localhost:8001/health")
    server.serve_forever()