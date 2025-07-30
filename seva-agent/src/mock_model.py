"""Mock model for testing without API keys."""
from typing import Dict, List, Optional, Any, Iterator

class MockModel:
    """A simple mock model that returns predefined responses for testing."""
    
    def __init__(self, **kwargs):
        """Initialize the mock model."""
        self.kwargs = kwargs
        print("MockModel initialized with:", kwargs)
    
    def complete(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Return a mock completion response."""
        last_message = messages[-1]["content"] if messages else ""
        
        response = {
            "id": "mock-response-id",
            "object": "chat.completion",
            "created": 1625097600,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"This is a mock response to: {last_message[:50]}...\n\nI'm a data analyst assistant running in test mode. How can I help you today?"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(last_message) // 4,
                "completion_tokens": 50,
                "total_tokens": (len(last_message) // 4) + 50
            }
        }
        
        return response
    
    def complete_stream(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[Dict[str, Any]]:
        """Return a mock streaming completion response."""
        last_message = messages[-1]["content"] if messages else ""
        
        # First chunk with role
        yield {
            "id": "mock-stream-id",
            "object": "chat.completion.chunk",
            "created": 1625097600,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                        "content": ""
                    },
                    "finish_reason": None
                }
            ]
        }
        
        # Content chunks
        response_text = f"This is a mock response to: {last_message[:50]}...\n\nI'm a data analyst assistant running in test mode. How can I help you today?"
        chunk_size = 10
        
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i+chunk_size]
            yield {
                "id": "mock-stream-id",
                "object": "chat.completion.chunk",
                "created": 1625097600,
                "model": "mock-model",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "content": chunk
                        },
                        "finish_reason": None
                    }
                ]
            }
            
        # Final chunk
        yield {
            "id": "mock-stream-id",
            "object": "chat.completion.chunk",
            "created": 1625097600,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }