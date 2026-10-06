# gunicorn.conf.py - Production configuration for Render deployment
import os

# Bind to Render's dynamic port (defaults to 5000 locally if not set)
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# 1 worker process prevents memory multiplication and stays within 512MB RAM on Render Free Tier
workers = int(os.getenv("WEB_CONCURRENCY", "1"))

# 4 threads handle concurrent web requests efficiently with minimal memory overhead
threads = int(os.getenv("GUNICORN_THREADS", "4"))

# 60s timeout prevents premature worker termination (internal AI REST timeout is strictly 22s)
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))

# Keepalive for persistent HTTP connections
keepalive = 5

# Stream logs to stdout/stderr for Render log aggregation
accesslog = "-"
errorlog = "-"
loglevel = "info"
