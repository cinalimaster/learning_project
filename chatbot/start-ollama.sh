#!/bin/sh
# Start Ollama server in the background
echo "Starting Ollama server..."
ollama serve &

# Wait until Ollama server is responsive
echo "Waiting for Ollama server to be ready..."
until ollama list > /dev/null 2>&1; do
  sleep 2
done

echo "Ollama server is ready."

# Define the model
MODEL="hf.co/unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:Q4_K_M"

# Check if model exists in the list
if ollama list | grep -q "$MODEL"; then
  echo "Model '$MODEL' is already present."
else
  echo "Model not found. Pulling '$MODEL'..."
  if ollama pull "$MODEL"; then
    echo "Model '$MODEL' pulled successfully."
  else
    echo "Error: Failed to pull model '$MODEL'."
    exit 1
  fi
fi

# Keep the script running (to keep Ollama server alive)
echo "Ollama server is running. Press Ctrl+C to stop."
wait