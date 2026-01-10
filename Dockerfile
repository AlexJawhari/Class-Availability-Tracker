# Lightweight Python Image for Discord Bot
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
# - build-essential: needed for compiling Python packages
# - ca-certificates: for HTTPS connections
# - curl: might be needed by curl_cffi
RUN apt-get update && apt-get install -y \
    build-essential \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Primary dependencies (required)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    py-cord \
    python-dotenv \
    requests \
    supabase \
    beautifulsoup4 \
    lxml

# Try to install curl_cffi (optional fallback scraper)
# If it fails, continue - token extraction method will still work
RUN pip install --no-cache-dir curl_cffi || \
    (echo "WARNING: curl_cffi installation failed, continuing without it (token extraction method will still work)" && \
     pip install --no-cache-dir)

# Copy the rest of the application
COPY . /app

# Expose port for health checks (Render/Railway will set PORT env var)
EXPOSE 8080

# Run the bot directly
CMD ["python", "-u", "-m", "src.bot"]
