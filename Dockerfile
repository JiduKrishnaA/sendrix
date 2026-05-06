# Use official lightweight Python images and music
FROM python:3.10-slim

# Set system environment variables to optimize Python performances
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy requirements file first to utilize Docker layer caching
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . /app/

# Ensure the uploads directory exists
RUN mkdir -p /app/uploads

# Expose port (Render overrides this, but good for local/documentative testing)
EXPOSE 5000

# Run using gunicorn with dynamic PORT binding (defaults to 5000 if PORT is not set)
CMD ["sh", "-c", "gunicorn --workers 4 --threads 2 --bind 0.0.0.0:${PORT:-5000} app:app"]
