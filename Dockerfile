# Use the specified Python image
FROM python:3.10-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    git \
    curl \
    build-essential \
    python3-dev \
    libffi-dev \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Clone the repository
RUN git clone https://github.com/itsOwen/CyberScraper-2077.git .

# Create and activate a virtual environment
RUN python -m venv venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create run script
RUN echo '#!/bin/bash\n\
\n\
# Export API keys if provided\n\
if [ ! -z "$OPENAI_API_KEY" ]; then\n\
    export OPENAI_API_KEY=$OPENAI_API_KEY\n\
    echo "OpenAI API key configured"\n\
fi\n\
\n\
if [ ! -z "$GOOGLE_API_KEY" ]; then\n\
    export GOOGLE_API_KEY=$GOOGLE_API_KEY\n\
    echo "Google API key configured"\n\
fi\n\
\n\
if [ ! -z "$SCRAPELESS_API_KEY" ]; then\n\
    export SCRAPELESS_API_KEY=$SCRAPELESS_API_KEY\n\
    echo "Scrapeless API key configured"\n\
fi\n\
\n\
# Start the application with explicit host binding\n\
echo "Starting CyberScraper 2077..."\n\
streamlit run --server.address 0.0.0.0 --server.port 8501 main.py\n\
' > /app/run.sh

RUN chmod +x /app/run.sh

# Expose port
EXPOSE 8501

# Set the entrypoint
ENTRYPOINT ["/app/run.sh"]