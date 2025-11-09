FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends gcc curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a non-root user to run the application
RUN useradd -m -u 1000 frostel && chown -R frostel:frostel /app

USER frostel

EXPOSE 5555

CMD ["python", "app.py"]
