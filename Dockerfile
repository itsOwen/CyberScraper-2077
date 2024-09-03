# Use the specified Python image
FROM python:3.8.19-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Install system dependencies including Git
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Cyberscraper repo :)
RUN git clone https://github.com/itsOwen/CyberScraper-2077.git .

# Create and activate a virtual environment
RUN python -m venv venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright and its browser
RUN pip install playwright requests
RUN playwright install chromium
RUN playwright install-deps

# Expose port 8501 for Streamlit
EXPOSE 8501

# Create a shell script to run the application
RUN echo '#!/bin/bash\n\
if [ ! -z "$OPENAI_API_KEY" ]; then\n\
    export OPENAI_API_KEY=$OPENAI_API_KEY\n\
fi\n\
if [ ! -z "$GOOGLE_API_KEY" ]; then\n\
    export GOOGLE_API_KEY=$GOOGLE_API_KEY\n\
fi\n\
streamlit run main.py\n\
' > /app/run.sh

RUN chmod +x /app/run.sh

# Set the entrypoint to the shell script
ENTRYPOINT ["/app/run.sh"]