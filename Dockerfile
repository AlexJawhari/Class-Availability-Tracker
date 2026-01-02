# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to prevent pyc files and buffer stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install python dependencies from the (hidden) requirements
# Note: In a real deploy you verify requirements.txt is present contextually 
# or copy it from a secret manager, but here we assume it's copied in build context.
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

# Copy the rest of the application
COPY . /app

# Run the bot and the runner scheduler (Note: For simple deployments, 
# running just the bot is often enough if you use an external scheduler for the runner,
# BUT here we actually want to run the bot process continuously).
# To actually run both bot and runner in one container often requires a supervisor, 
# but simply running the bot is the primary "server" task here.
CMD ["python", "-m", "src.bot"]
