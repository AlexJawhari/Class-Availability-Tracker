# Use official Playwright image which includes Python and all browser deps
FROM mcr.microsoft.com/playwright/python:v1.57.0-noble

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install Xvfb (missing in base image but required for pyvirtualdisplay)
# Also install xauth which is sometimes needed
RUN apt-get update && apt-get install -y \
    xvfb \
    xauth \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

# Run python directly. Xvfb is now managed by src/bot.py via pyvirtualdisplay
CMD ["python", "-u", "-m", "src.bot"]
