# Docker Build Instructions

This project provides two Dockerfiles for different use cases:

## Option 1: Build from GitHub (Dockerfile)
This Dockerfile clones the repository from GitHub and builds the image.

```bash
docker build -t mcp-client-m1 .
```

## Option 2: Build from Local Files (Dockerfile.local) - RECOMMENDED
This Dockerfile uses your local files and is faster for development.

```bash
docker build -f Dockerfile.local -t mcp-client-m1:local .
```

## Running the Container

After building, run the container with port mapping to expose ports to your host machine:

```bash
docker run -p 7860:7860 -p 8000:8000 mcp-client-m1:local
```

### Understanding Port Mapping

**Important:** The `-p` flag is REQUIRED to access ports from your host machine. Without it, ports are not accessible.

- `docker run -p 7860:7860` - Maps container port 7860 to host port 7860
- `docker run -p 8000:8000` - Maps container port 8000 to host port 8000

**Example with different ports:**
If port 7860 is already in use on your host, you can map to a different port:
```bash
docker run -p 9000:7860 -p 8000:8000 mcp-client-m1:local
```
This maps container port 7860 to host port 9000. Access Gradio at `http://localhost:9000`

### With Environment Variables

If you want to use OpenAI instead of Ollama, pass your API key:

```bash
docker run -p 7860:7860 -p 8000:8000 \
  -e OPENAI_API_KEY=your_api_key_here \
  -e MODEL_NAME=gpt-4 \
  mcp-client-m1:local
```

### Interactive Mode

To run in interactive mode with shell access:

```bash
docker run -it -p 7860:7860 -p 8000:8000 mcp-client-m1:local /bin/bash
```

## Accessing the Application

After running the container with port mapping:

- **Gradio Interface**: http://localhost:7860
- **API Endpoint**: http://localhost:8000

### Testing the API

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "your question here"}'
```

## What Was Fixed

1. **Port Binding**: Updated both applications to bind to `0.0.0.0` instead of `localhost` so they can be accessed from the host machine
   - `client_query.py`: aiohttp server now binds to `0.0.0.0:8000`
   - `gradio_interface.py`: Gradio app now binds to `0.0.0.0:7860`

2. **Pip Install**: Added `--break-system-packages` flag to work with Python 3.12+ in the container

## Notes

- The container will automatically start Ollama and pull the `llama3.2:3b` model on first run (this may take a few minutes)
- The ports must be available on your host machine
- The container uses the ollama/ollama base image with Python 3 installed
- Both services (API and Gradio) run in the same container and communicate via localhost internally

## Notes

- The container will automatically start Ollama and pull the `llama3.2:3b` model on first run (this may take a few minutes)
- Ports 7860 and 8000 must be available on your host machine
- The container uses the ollama/ollama base image with Python 3 installed

