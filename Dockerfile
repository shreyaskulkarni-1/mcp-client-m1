# This dockerfile will build a container by cloning the repository and installing the dependencies.
# We will use python 3.12 image.
FROM python:3.12-slim

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
bash ./start.sh\n\' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["./start.sh"]
