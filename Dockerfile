# This dockerfile will build a container by cloning the repository and installing the dependencies.
# We will use ollama container as the base image, so if user doesn't have OPENAI_API_KEY, they can still use the container with ollama for local LLMs.
FROM ollama/ollama:latest

# Install git and other dependencies
RUN apt-get update && apt-get install -y git python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Clone the repository (using HTTPS instead of SSH)
RUN git clone https://github.com/shreyaskulkarni-1/mcp-client-m1.git

# Set the working directory
WORKDIR /mcp-client-m1

# Install Python dependencies
RUN pip3 install --break-system-packages -r requirements.txt

# Make start.sh executable
RUN chmod +x start.sh

# Expose ports (adjust as needed for your application)
EXPOSE 7860 8000

# Create an entrypoint script that starts ollama and pulls the model
RUN echo '#!/bin/bash\n\
ollama serve &\n\
OLLAMA_PID=$!\n\
sleep 5\n\
ollama pull llama3.2:3b\n\
exec "$@"' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["./start.sh"]
