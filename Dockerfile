# Use official Python slim image for a smaller footprint
# removing the playwright image which includes heavy browser binaries
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5001 \
    HOST=0.0.0.0 \
    PYTHONPATH=/app/backend

# Set the working directory in the container
WORKDIR /app

# Install minimal system dependencies if needed
# (e.g., for Pillow/ReportLab if wheels aren't sufficient, though usually they are on modern pip)
# We keep it clean for now. 

# Copy the backend requirements file first to leverage Docker cache
COPY backend/requirements.txt backend/requirements.txt

# Install Python dependencies
# This will install 'playwright' python package but NOT the browser binaries
RUN pip install --no-cache-dir -r backend/requirements.txt

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