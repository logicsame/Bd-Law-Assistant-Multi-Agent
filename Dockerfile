# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if needed (e.g., for libraries like OpenCV or specific DB drivers)
# We need build-essential for some dependencies, and potentially others for faiss/spacy
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Download default spacy model
RUN pip install --no-cache-dir spacy && \
    python -m spacy download en_core_web_sm

# First copy the whole project to ensure setup.py is available
COPY . .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir to reduce image size
# Using --default-timeout=100 to prevent timeouts during installation
# The '-e .' line will install the local package from setup.py
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# Make ports available to the world outside this container
# Port 8000 for FastAPI backend
EXPOSE 8000
# Port 8501 for Streamlit frontend
EXPOSE 8501

# Define environment variables if needed
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

