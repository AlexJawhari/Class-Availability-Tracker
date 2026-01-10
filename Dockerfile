# Python Discord Bot with Playwright and Xvfb
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Set work directory
WORKDIR /app

# Install system dependencies
# - build-essential: needed for compiling Python packages
# - ca-certificates: for HTTPS connections
# - curl: might be needed by curl_cffi
# - xvfb: virtual display for headful browser mode (stealth)
# - fonts: needed for proper rendering
# - libnss3, libatk, etc: dependencies for Chromium
RUN apt-get update && apt-get install -y \
    build-essential \
    ca-certificates \
    curl \
    xvfb \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    py-cord \
    python-dotenv \
    requests \
    supabase \
    beautifulsoup4 \
    lxml \
    playwright \
    playwright-stealth

# Install Playwright browsers (Chromium and Firefox for multiple options)
RUN playwright install chromium firefox && \
    playwright install-deps chromium firefox

# Try to install curl_cffi (optional fallback scraper)
# If it fails, continue - Playwright and token extraction methods will still work
RUN pip install --no-cache-dir curl_cffi || \
    (echo "WARNING: curl_cffi installation failed, continuing without it" && \
     pip install --no-cache-dir)

# Copy the rest of the application
COPY . /app

# Expose port for health checks (Render/Railway will set PORT env var)
EXPOSE 8080

# Start Xvfb in background and run bot
# Xvfb creates a virtual display for headful browser mode
CMD Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & \
    export DISPLAY=:99 && \
    sleep 2 && \
    python -u -m src.bot
