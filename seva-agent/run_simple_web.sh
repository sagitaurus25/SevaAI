#!/bin/bash

# Run the simple web interface
uvicorn simple_web:app --host 0.0.0.0 --port 8085