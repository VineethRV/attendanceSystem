"""
Database models and connection management for the attendance system.
Uses SQLAlchemy ORM with PostgreSQL.
"""

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    DateTime,
    Date,
    Boolean,
    ARRAY,
    Float,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import config

print("USING DATABASE_URL =", config.DATABASE_URL)

# Create database engine
engine = create_engine(config.DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class Student(Base):
    """
    Students table - stores basic student information
    """
    __tablename__ = "students"
    
    student_id = Column(String(20), primary_key=True)
    registered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    name = Column(String(255), nullable=True)  # Optional: can be added later
    
    # Relationships
    embeddings = relationship("FaceEmbedding", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Student(student_id='{self.student_id}', registered_at='{self.registered_at}')>"


class FaceEmbedding(Base):
    """
    Face embeddings table - stores the 5 embeddings per student
    Each student has exactly 5 embeddings (embedding_index: 1-5)
    """
    __tablename__ = "face_embeddings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
    embedding_index = Column(Integer, nullable=False)  # 1, 2, 3, 4, or 5
    embedding_vector = Column(ARRAY(Float), nullable=False)  # 512-dimensional vector
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    student = relationship("Student", back_populates="embeddings")
    
    # Ensure unique (student_id, embedding_index) combination
    __table_args__ = (
        UniqueConstraint("student_id", "embedding_index", name="uq_student_embedding_index"),
    )
    
    def __repr__(self):
        return f"<FaceEmbedding(student_id='{self.student_id}', index={self.embedding_index})>"


class Attendance(Base):
    """
    Attendance table - records attendance marks
    Matrix-style representation: each row is a (student_id, date) pair
    Unique constraint ensures one attendance record per student per day
    """
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    marked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    present = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    student = relationship("Student", back_populates="attendance_records")
    
    # Ensure unique (student_id, date) - one attendance per student per day
    __table_args__ = (
        UniqueConstraint("student_id", "date", name="uq_student_date"),
    )
    
    def __repr__(self):
        return f"<Attendance(student_id='{self.student_id}', date='{self.date}', present={self.present})>"


def get_db():
    """
    Dependency function to get database session.
    Use in FastAPI route dependencies.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """
    Initialize database - create all tables.
    Run this during application startup or via separate script.
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def drop_all_tables():
    """
    Drop all tables - USE WITH CAUTION!
    Only for development/testing.
    """
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All database tables dropped")


if __name__ == "__main__":
    # When run directly, initialize the database
    print("Initializing database...")
    init_database()
