"""
Configuration module for the attendance system backend.
All configurable parameters are loaded from environment variables.
"""

import os
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class"""
    
    # Database Configuration
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/attendance_system"
    )
    
    # Admin Authentication
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change_this_password_123")
    
    # Face Recognition Parameters
    # Cosine similarity threshold for face matching (0.0 to 1.0)
    # Higher values mean stricter matching
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.8"))
    
    # Minimum number of stored embeddings that must match the live embedding
    # Out of 5 stored embeddings, how many must exceed the threshold
    MIN_MATCHES_REQUIRED = int(os.getenv("MIN_MATCHES_REQUIRED", "2"))
    
    # Student ID Validation
    # Format: 1RV23CSXXX where XXX is 001-420
    STUDENT_ID_PATTERN = r"^1RV23CS(0[0-9]{2}|[1-3][0-9]{2}|4[0-1][0-9]|420)$"
    STUDENT_ID_REGEX = re.compile(STUDENT_ID_PATTERN)
    
    # Expected number of embeddings per registration
    NUM_EMBEDDINGS = 5
    
    # Expected embedding dimension (ArcFace/FaceNet typically 512 or 128)
    EMBEDDING_DIMENSION = 512
    
    # Server Configuration
    HOST = os.getenv("HOST", "localhost")
    PORT = int(os.getenv("PORT", "8000"))
    
    # CORS Configuration (for local development)
    ALLOWED_ORIGINS = [
        "https://localhost:8001",
        "https://127.0.0.1:8001",
        "https://10.81.169.155:8001",
    ]
    
    @classmethod
    def validate_student_id(cls, student_id: str) -> bool:
        """Validate student ID format"""
        return cls.STUDENT_ID_REGEX.match(student_id) is not None
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """Return a summary of current configuration (for debugging)"""
        return {
            "similarity_threshold": cls.SIMILARITY_THRESHOLD,
            "min_matches_required": cls.MIN_MATCHES_REQUIRED,
            "num_embeddings": cls.NUM_EMBEDDINGS,
            "embedding_dimension": cls.EMBEDDING_DIMENSION,
            "student_id_pattern": cls.STUDENT_ID_PATTERN,
        }


# Global config instance
config = Config()
