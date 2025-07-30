from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import os
import urllib.parse
import re
import asyncio
import logging
import shlex
from typing import Dict, Any

print("🚀 Starting AWS Agent...")
print("📍 Current directory:", os.getcwd())
print("🔍 Checking imports...")

try:
    from models.session import SessionData
    print("✅ SessionData imported successfully")
except ImportError as e:
    print("❌ Failed to import SessionData:", e)

try:
    from services.llm_command_generator import LLMCommandGenerator
    print("✅ LLMCommandGenerator imported successfully")
except ImportError as e:
    print("❌ Failed to import LLMCommandGenerator:", e)

print("🎯 Starting main application...")

# Initialize LLM command generator
llm_command_generator = LLMCommandGenerator()

print("📝 Defining AWSAgentHandler class...")

class AWSAgentHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"📥 GET request received: {self.path}")
        
        if self.path == '/' or self.path == '/index.html':
            self.serve_file('../frontend/index.html', 'text/html')
        elif self.path == '/style.css':
            self.serve_file('../frontend/style.css', 'text/css')
        elif self.path == '/script.js':
            self.serve_file('../frontend/script.js', 'application/javascript')
        elif self.path == '/static/style.css':
            self.serve_file('../frontend/style.css', 'text/css')
        elif self.path == '/static/script.js':
            self.serve_file('../frontend/script.js', 'application/javascript')
        elif self.path == '/api/health':
            self.send_json_response({'status': 'healthy'})
        else:
            self.send_404()

    def do_POST(self):
        print(f"📤 POST request received: {self.path}")
        if self.path == '/api/chat':
            self.handle_chat()
        else:
            self.send_404()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def serve_file(self, file_path, content_type):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
            print(f"✅ Served file: {file_path}")
        except FileNotFoundError:
            print(f"❌ File not found: {file_path}")
            self.send_404()
        except Exception as e:
            print(f"❌ Error serving file: {e}")
            self.send_404()
    
    def send_404(self):
        self.send_response(404)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>404 Not Found</h1>')
        print("📤 Sent 404 response")
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
        print(f"📤 Sent JSON response")
    
    def handle_chat(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            message = data.get('message', '').strip()
            
            print(f"💬 Processing message: {message}")
            
            # Run async code in sync context
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            response = loop.run_until_complete(self.process_message_async(message))
            
            self.send_json_response({
                'response': response,
                'session_id': data.get('session_id', 'default'),
                'needs_clarification': False,
                'suggested_actions': []
            })
            
        except Exception as e:
            print(f"❌ Error in handle_chat: {e}")
            import traceback
            traceback.print_exc()
            self.send_json_response({
                'response': f'Error processing your request: {str(e)}',
                'session_id': 'default',
                'needs_clarification': False,
                'suggested_actions': []
            })

    async def process_message_async(self, message):
        """Async message processing with LLM"""
        print(f"🎯 PROCESSING MESSAGE: '{message}'")
        try:
            print("🧠 Calling LLM to generate command...")
        
            # ALL requests should go through LLM - no hardcoded patterns!
            command_result = await llm_command_generator.generate_aws_command(message, {})
        
            if command_result.get("success"):
                command = command_result.get('command')
                print(f"✅ LLM generated command: {command}")
            
                # Execute the command
                execution_result = await self.execute_command(command)
            
                if execution_result.get("success"):
                    data = execution_result.get('data', '')
                    description = command_result.get('description', 'AWS command executed')
                    return f"✅ **{description}**\n\n📊 **Results**:\n```\n{data}\n```\n\n🔧 **Command**: `{command}`"
                else:
                    error = execution_result.get('error', 'Unknown error')
                    return f"❌ **Error**: {error}\n\n🔧 **Command attempted**: `{command}`"
            else:
                error = command_result.get('error', 'Unknown error')
                suggestion = command_result.get('suggestion', '')
                response = f"❌ Could not generate command: {error}"
                if suggestion:
                    response += f"\n\n💡 Suggestion: {suggestion}"
                return response
            
        except Exception as e:
            print(f"❌ LLM processing error: {e}")
            import traceback
            traceback.print_exc()
            return f"Error processing request: {str(e)}"

    async def execute_command(self, command):
        """Execute AWS CLI command"""
        try:
            print(f"⚡ Executing command: {command}")
            
            # Use secure execution with shlex
            result = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if not output:
                    output = "Command executed successfully but returned no results. You might not have any resources of this type."
                return {
                    "success": True,
                    "data": output
                }
            else:
                error_output = result.stderr.strip()
                if not error_output:
                    error_output = f"Command failed with return code {result.returncode}"
                return {
                    "success": False,
                    "error": error_output
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out after 30 seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

print("🔧 Defining run_server function...")

def run_server():
    print("🌐 Creating server...")
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, AWSAgentHandler)
    print("✅ Server created successfully")
    print("🚀 AWS Agent server starting on http://localhost:8000")
    print("📱 Open your browser and go to: http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    
    try:
        print("🔄 Starting server loop...")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")

print("🎬 Checking if __name__ == '__main__'...")

if __name__ == '__main__':
    print("✅ Running as main script")
    print("🚀 Calling run_server()...")
    run_server()