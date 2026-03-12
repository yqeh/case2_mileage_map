# Use official Python slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5001 \
    HOST=0.0.0.0 \
    PYTHONPATH=/app/backend \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Set the working directory in the container
WORKDIR /app

# Copy the backend requirements file first to leverage Docker cache
COPY backend/requirements.txt backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Install Playwright browser and its Linux dependencies for screenshot export
RUN python -m playwright install --with-deps chromium

# Copy the backend code
COPY backend/ backend/

# Copy the frontend and other root files
COPY index.html .
COPY css/ css/
COPY js/ js/
COPY template.xlsx .

# Copy assets
COPY assets/ assets/

# Create necessary directories for runtime
RUN mkdir -p logs temp/maps output

# Expose the port
EXPOSE 5001

# Command to run the application
CMD ["python", "backend/main.py"]
