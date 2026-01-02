# Use official Playwright image which includes Python and all browser deps
# This is much faster and more reliable than installing deps manually
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install browsers (Playwright image has deps, but we ensure the specific browser is there)
RUN playwright install chromium

# Copy the rest of the application
COPY . /app

# Run the bot
CMD ["python", "-m", "src.bot"]
