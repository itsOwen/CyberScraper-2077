# Use the specified Python image
FROM python:3.10-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Install system dependencies including Git and Tor
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    git \
    tor \
    tor-geoipdb \
    # Additional dependencies that might be needed
    build-essential \
    python3-dev \
    libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configure Tor
RUN echo "SocksPort 9050" >> /etc/tor/torrc && \
    echo "ControlPort 9051" >> /etc/tor/torrc && \
    echo "CookieAuthentication 1" >> /etc/tor/torrc

# Cyberscraper repo :)
RUN git clone https://github.com/itsOwen/CyberScraper-2077.git .

# Create and activate a virtual environment
RUN python -m venv venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional Tor-related Python packages
RUN pip install --no-cache-dir \
    PySocks \
    requests[socks]

# Install playwright and its browser
RUN pip install playwright requests
RUN playwright install chromium
RUN playwright install-deps

# Expose ports for Streamlit and Tor
EXPOSE 8501
EXPOSE 9050
EXPOSE 9051

# Create a shell script to run the application
RUN echo '#!/bin/bash\n\
# Start Tor service\n\
service tor start\n\
\n\
# Wait for Tor to be ready\n\
echo "Waiting for Tor to be ready..."\n\
timeout 60 bash -c "until nc -z localhost 9050; do sleep 1; done"\n\
\n\
if [ ! -z "$OPENAI_API_KEY" ]; then\n\
    export OPENAI_API_KEY=$OPENAI_API_KEY\n\
fi\n\
if [ ! -z "$GOOGLE_API_KEY" ]; then\n\
    export GOOGLE_API_KEY=$GOOGLE_API_KEY\n\
fi\n\
\n\
# Check Tor connection\n\
echo "Verifying Tor connection..."\n\
curl --socks5 localhost:9050 --socks5-hostname localhost:9050 -s https://check.torproject.org/api/ip\n\
\n\
streamlit run main.py\n\
' > /app/run.sh

RUN chmod +x /app/run.sh

# Set the entrypoint to the shell script
ENTRYPOINT ["/app/run.sh"]