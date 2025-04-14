#!/bin/bash

# Create src directory if it doesn't exist
#mkdir -p src

# Install dependencies
#echo "Installing dependencies..."
#pip install -r requirements.txt

# Check if Ollama is running
echo "Checking Ollama service..."
if ! curl -s http://localhost:11434/api/version > /dev/null; then
  echo "⚠️ Warning: Ollama service doesn't seem to be running on http://localhost:11434"
  echo "Please ensure Ollama is running with the required embedding model (e.g., nomic-embed-text)"
fi

# Check if vLLM is running
echo "Checking vLLM service..."
if ! curl -s http://localhost:8000/v1/models > /dev/null; then
  echo "⚠️ Warning: vLLM service doesn't seem to be running on http://localhost:8000"
  echo "Please ensure vLLM is running with the required LLM model"
fi

# Run the Dash application
echo "Starting the RAG application..."
python app.py