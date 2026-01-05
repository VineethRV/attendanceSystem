"""Configuration for backend service."""
import os

# Backend URL used by frontend (default to http for local development)
BACKEND_URL = os.environ.get("BACKEND_URL", "https://localhost:8000")

# CORS allowed origins (list). Default includes common local dev origins.
ALLOWED_ORIGINS = os.environ.get(
	"ALLOWED_ORIGINS",
	"http://localhost:8080,https://localhost:8000,https://localhost:8000,http://127.0.0.1:8080,https://localhost:8001,http://localhost:8001",
	).split(",")

# Admin credentials for simple Basic Auth (change in production)
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "secret")
