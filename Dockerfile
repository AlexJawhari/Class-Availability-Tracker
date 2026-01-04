# Use official Playwright image which includes Python and all browser deps
FROM mcr.microsoft.com/playwright/python:v1.54.0-noble

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install Xvfb (missing in base image but required for xvfb-run)
RUN apt-get update && apt-get install -y \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

# Run with xvfb-run for headful browser support
# Added -u to python to force unbuffered output immediately
CMD ["xvfb-run", "--auto-servernum", "--server-args=-screen 0 1920x1080x24", "python", "-u", "-m", "src.bot"]
