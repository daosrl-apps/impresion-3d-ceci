FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user and group
RUN groupadd -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup -d /app appuser

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and change ownership
COPY --chown=appuser:appgroup . .

# Ensure upload directory permissions
RUN mkdir -p /app/uploads && chown -R appuser:appgroup /app/uploads

# Run as non-root user
USER appuser

EXPOSE 8085

# Healthcheck to verify the server is active
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8085/api/config || exit 1

CMD ["python", "server.py"]
