# !/bin/sh

# Start Ollama server in the background
ollama serve &

# Wait until Ollama server is responsive
echo "Waiting for Ollama server to be ready..."
until ollama list > /dev/null 2>&1; do
  sleep 2
done

# Pull the model if it's not already pulled
if ! ollama list | grep -q 'qwen3:4b'; then
  echo "Model not found, pulling..."
  ollama pull qwen3:4b
else
  echo "Model already present."
fi

# Keep script running
wait
