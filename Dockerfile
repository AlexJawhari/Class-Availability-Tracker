# Use official Playwright image which includes Python and all browser deps
# If BROWSERLESS_TOKEN is set, the browser runs in the cloud (no local browser needed)
# Otherwise, uses local Chromium with Xvfb virtual display
FROM mcr.microsoft.com/playwright/python:v1.54.0-noble

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

# Run with xvfb-run for headful browser support (if not using Browserless.io)
# xvfb-run creates a virtual display for the browser
CMD ["xvfb-run", "--auto-servernum", "--server-args=-screen 0 1920x1080x24", "python", "-m", "src.bot"]
