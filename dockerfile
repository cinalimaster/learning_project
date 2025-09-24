FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt /tmp/requirements.txt
RUN pip install --requirement /tmp/requirements.txt

# Ensure NLTK is installed and data downloaded
RUN python -c "import nltk; \
                nltk.download('punkt', quiet=True); \
                nltk.download('punkt_tab', quiet=True); \
                nltk.download('stopwords', quiet=True)"

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Copy application code
COPY . /app/

# Make the start-ollama.sh script executable
RUN chmod +x /app/start-ollama.sh

# Expose port for Django
EXPOSE 80
