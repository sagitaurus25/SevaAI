from http.server import HTTPServer, BaseHTTPRequestHandler
import json

print("🚀 Starting test server...")

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"📥 GET: {self.path}")
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = """
        <html>
        <body>
            <h1>✅ Test Server Working!</h1>
            <p>If you see this, the server is running correctly.</p>
            <button onclick="testAPI()">Test API</button>
            <div id="result"></div>
            <script>
                async function testAPI() {
                    try {
                        const response = await fetch('/api/test');
                        const data = await response.json();
                        document.getElementById('result').innerHTML = '<p>API Response: ' + data.message + '</p>';
                    } catch (error) {
                        document.getElementById('result').innerHTML = '<p>API Error: ' + error + '</p>';
                    }
                }
            </script>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def do_POST(self):
        print(f"📤 POST: {self.path}")
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        if self.path == '/api/test':
            response = {"message": "Test API working!"}
            self.wfile.write(json.dumps(response).encode())

def main():
    try:
        print("🌐 Creating server on port 8000...")
        server = HTTPServer(('localhost', 8000), TestHandler)
        print("✅ Server created successfully!")
        print("🔗 Go to: http://localhost:8000")
        print("⏹️  Press Ctrl+C to stop")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Server failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()