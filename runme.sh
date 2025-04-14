cat << 'EOF' > /home/cshelp/streamlit-vllm-rag/src/request_vllm.sh
#!/bin/bash

# Load environment variables
source .env

# Create a curl command to request the VLLM endpoint
curl -X POST "$VLLM_URL" \
  -H "Content-Type: application/json" \
  -d '{
  "model": "'$MODEL_NAME'",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Tell me about VLLM in 3 sentences."}
  ],
  "temperature": 0.7,
  "max_tokens": 150
}'

EOF

chmod +x /home/cshelp/streamlit-vllm-rag/src/request_vllm.sh
echo "Created executable script request_vllm.sh"