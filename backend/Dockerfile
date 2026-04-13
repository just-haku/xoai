FROM python:3.12-slim

WORKDIR /app

# System deps for bcrypt wheel
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && \
    rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["xoai", "start"]
