FROM python:3.12-slim

WORKDIR /app

# Copy only requirements first for better layer caching
COPY requirements.txt .

# Combine RUN commands and remove unnecessary packages
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install -U psutil aiohttp==3.9.0rc0

# Copy application code
COPY . .

# Use python to run the app explicitly
CMD ["python", "app.py"]