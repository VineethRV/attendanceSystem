"""
Main FastAPI application for the attendance system backend.
Implements registration, verification, and admin APIs.
"""

from fastapi import FastAPI, Depends, HTTPException, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import date, datetime
import uvicorn
import io
import pandas as pd
import csv
import os

from database import get_db, Student, FaceEmbedding, Attendance, init_database
from config import config
from utils import (
    verify_face,
    validate_embedding,
    validate_embeddings_list,
    verify_basic_auth,
    format_similarity_scores,
)

# Path to registration keys CSV
KEYS_CSV_PATH = os.path.join(os.path.dirname(__file__), 'registration_keys.csv')

# Initialize FastAPI app
app = FastAPI(
    title="Classroom Attendance System API",
    description="Face recognition-based attendance system",
    version="1.0.0",
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class RegistrationRequest(BaseModel):
    """Request model for student registration"""
    student_id: str = Field(..., description="Student ID (format: 1RV23CSXXX)")
    registration_key: str = Field(..., description="Unique registration key")
    embeddings: List[List[float]] = Field(..., description="List of 5 face embeddings")
    name: Optional[str] = Field(None, description="Student name")
    semester: Optional[str] = Field(None, description="Semester")
    section: Optional[str] = Field(None, description="Section")
    
    @validator("student_id")
    def validate_student_id(cls, v):
        if not config.validate_student_id(v):
            raise ValueError(f"Invalid student ID format. Expected: {config.STUDENT_ID_PATTERN}")
        return v
    
    @validator("embeddings")
    def validate_embeddings(cls, v):
        is_valid, error_msg = validate_embeddings_list(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class KeyValidationRequest(BaseModel):
    """Request model for key validation"""
    student_id: str = Field(..., description="Student ID (USN)")
    registration_key: str = Field(..., description="Registration key")


class KeyValidationResponse(BaseModel):
    """Response model for key validation"""
    status: str
    message: str
    valid: bool


class RegistrationResponse(BaseModel):
    """Response model for registration"""
    status: str
    message: str
    student_id: str


class VerificationRequest(BaseModel):
    """Request model for attendance verification"""
    student_id: str = Field(..., description="Student ID")
    live_embedding: List[float] = Field(..., description="Live face embedding")
    
    @validator("student_id")
    def validate_student_id(cls, v):
        if not config.validate_student_id(v):
            raise ValueError(f"Invalid student ID format")
        return v
    
    @validator("live_embedding")
    def validate_live_embedding(cls, v):
        is_valid, error_msg = validate_embedding(v)
        if not is_valid:
            raise ValueError(error_msg)
        return v


class VerificationResponse(BaseModel):
    """Response model for attendance verification"""
    status: str
    message: str
    similarity_scores: Optional[List[float]] = None
    matches: Optional[int] = None
    confidence: Optional[float] = None
    matches_found: Optional[int] = None
    best_match: Optional[float] = None
    marked_at: Optional[str] = None


class AttendanceRecord(BaseModel):
    """Model for a single attendance record"""
    student_id: str
    present: bool
    marked_at: Optional[datetime] = None


class AttendanceResponse(BaseModel):
    """Response model for attendance query"""
    date: str
    total_students: int
    present: int
    absent: int
    attendance: List[AttendanceRecord]


# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    init_database()
    
    # Check if registration keys CSV exists
    if not os.path.exists(KEYS_CSV_PATH):
        print("⚠️  Registration keys CSV not found. Generating...")
        from generate_keys import generate_keys_csv
        generate_keys_csv(KEYS_CSV_PATH)
    
    print("✅ Backend started successfully")
    print(f"🔧 Configuration: {config.get_config_summary()}")


# ============================================================================
# Helper Functions for Registration Keys
# ============================================================================

def validate_registration_key(student_id: str, key: str) -> tuple[bool, str]:
    """
    Validate if the registration key matches the USN.
    Returns (is_valid, message)
    """
    if not os.path.exists(KEYS_CSV_PATH):
        return False, "Registration keys file not found. Please contact admin."
    
    try:
        with open(KEYS_CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['usn'].upper() == student_id.upper():
                    if row['registration_key'] == key:
                        if row['used'].upper() == 'YES':
                            return False, "This registration key has already been used."
                        return True, "Key validated successfully."
                    else:
                        return False, "Invalid registration key for this USN."
            return False, "USN not found in the system."
    except Exception as e:
        return False, f"Error validating key: {str(e)}"


def mark_key_as_used(student_id: str) -> bool:
    """Mark a registration key as used after successful registration"""
    if not os.path.exists(KEYS_CSV_PATH):
        return False
    
    try:
        rows = []
        with open(KEYS_CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row['usn'].upper() == student_id.upper():
                    row['used'] = 'YES'
                rows.append(row)
        
        with open(KEYS_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        return True
    except Exception as e:
        print(f"Error marking key as used: {e}")
        return False


# ============================================================================
# Student APIs
# ============================================================================

@app.post("/api/validate-key", response_model=KeyValidationResponse)
async def validate_key(request: KeyValidationRequest):
    """
    Validate registration key before allowing face capture.
    """
    is_valid, message = validate_registration_key(request.student_id, request.registration_key)
    
    return KeyValidationResponse(
        status="success" if is_valid else "error",
        message=message,
        valid=is_valid
    )

@app.post("/api/register", response_model=RegistrationResponse)
async def register_student(
    request: RegistrationRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new student with face embeddings.
    
    - Validates registration key
    - Validates student ID format
    - Checks if student already exists
    - Stores 5 face embeddings in database
    """
    student_id = request.student_id
    
    # Validate registration key first
    is_valid, key_message = validate_registration_key(student_id, request.registration_key)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": key_message
            }
        )
    
    # Check if student already exists
    existing_student = db.query(Student).filter(Student.student_id == student_id).first()
    if existing_student:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "message": "Student already registered. Use overwrite option if you want to re-register."
            }
        )
    
    try:
        # Create student record
        new_student = Student(
            student_id=student_id,
            registered_at=datetime.utcnow()
        )
        db.add(new_student)
        
        # Create face embedding records
        for i, embedding in enumerate(request.embeddings):
            face_embedding = FaceEmbedding(
                student_id=student_id,
                embedding_index=i + 1,  # 1-indexed
                embedding_vector=embedding,
                created_at=datetime.utcnow()
            )
            db.add(face_embedding)
        
        # Commit transaction
        db.commit()
        
        # Mark key as used
        mark_key_as_used(student_id)
        
        return RegistrationResponse(
            status="success",
            message="Student registered successfully",
            student_id=student_id
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Registration failed: {str(e)}"
            }
        )


@app.post("/api/verify", response_model=VerificationResponse)
async def verify_attendance(
    request: VerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify student identity and mark attendance.
    
    - Retrieves stored embeddings
    - Compares with live embedding using cosine similarity
    - Marks attendance if verification succeeds
    - Enforces once-per-day rule
    """
    student_id = request.student_id
    today = date.today()
    
    # Check if student is registered
    student = db.query(Student).filter(Student.student_id == student_id).first()
    if not student:
        return VerificationResponse(
            status="not_registered",
            message="Student not registered. Please register first.",
            similarity_scores=None,
            matches=None
        )
    
    # Check if attendance already marked today
    existing_attendance = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.date == today
    ).first()
    
    if existing_attendance:
        return VerificationResponse(
            status="already_marked",
            message="Attendance already marked for today",
            similarity_scores=None,
            matches=None,
            marked_at=existing_attendance.marked_at.isoformat() if existing_attendance.marked_at else None
        )
    
    # Retrieve stored embeddings
    stored_embeddings_records = db.query(FaceEmbedding).filter(
        FaceEmbedding.student_id == student_id
    ).order_by(FaceEmbedding.embedding_index).all()
    
    if len(stored_embeddings_records) != config.NUM_EMBEDDINGS:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Incomplete registration data. Please re-register."
            }
        )
    
    # Extract embedding vectors
    stored_embeddings = [record.embedding_vector for record in stored_embeddings_records]
    
    # Perform face verification
    is_verified, similarity_scores, num_matches = verify_face(
        request.live_embedding,
        stored_embeddings
    )
    
    if not is_verified:
        best_similarity = max(similarity_scores) if similarity_scores else 0.0
        return VerificationResponse(
            status="verification_failed",
            message="Biometric verification failed",
            similarity_scores=format_similarity_scores(similarity_scores),
            matches=num_matches,
            matches_found=num_matches,
            best_match=float(best_similarity),
            confidence=float(best_similarity)
        )
    
    # Mark attendance
    try:
        attendance_record = Attendance(
            student_id=student_id,
            date=today,
            marked_at=datetime.utcnow(),
            present=True
        )
        db.add(attendance_record)
        db.commit()
        
        best_similarity = max(similarity_scores) if similarity_scores else 0.0
        return VerificationResponse(
            status="ok",
            message="Attendance marked successfully",
            similarity_scores=format_similarity_scores(similarity_scores),
            matches=num_matches,
            matches_found=num_matches,
            confidence=float(best_similarity)
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Failed to mark attendance: {str(e)}"
            }
        )


# ============================================================================
# Admin APIs
# ============================================================================

def require_admin_auth(authorization: Optional[str] = Header(None)):
    """Dependency to require admin authentication"""
    if not verify_basic_auth(authorization):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/api/admin/attendance", response_model=AttendanceResponse)
async def get_attendance(
    date_str: Optional[str] = None,
    student_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _auth: None = Depends(require_admin_auth)
):
    """
    Get attendance records for a specific date or student.
    Requires admin authentication.
    
    Query parameters:
    - date: Date in YYYY-MM-DD format (defaults to today)
    - student_id: Filter by specific student (optional)
    """
    # Parse date
    if date_str:
        try:
            query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    else:
        query_date = date.today()
    
    # Build query
    if student_id:
        # Get attendance for specific student on specific date
        attendance_records = db.query(Attendance).filter(
            Attendance.student_id == student_id,
            Attendance.date == query_date
        ).all()
    else:
        # Get all attendance for specific date
        attendance_records = db.query(Attendance).filter(
            Attendance.date == query_date
        ).all()
    
    # Get total registered students
    total_students = db.query(Student).count()
    
    # Format response
    attendance_list = [
        AttendanceRecord(
            student_id=record.student_id,
            present=record.present,
            marked_at=record.marked_at
        )
        for record in attendance_records
    ]
    
    present_count = sum(1 for record in attendance_records if record.present)
    absent_count = total_students - present_count
    
    return AttendanceResponse(
        date=query_date.strftime("%Y-%m-%d"),
        total_students=total_students,
        present=present_count,
        absent=absent_count,
        attendance=attendance_list
    )


@app.get("/api/admin/export")
async def export_attendance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    _auth: None = Depends(require_admin_auth)
):
    """
    Export attendance data as CSV.
    Requires admin authentication.
    
    Query parameters:
    - start_date: Start date in YYYY-MM-DD format
    - end_date: End date in YYYY-MM-DD format
    """
    # Parse dates
    try:
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            start = date.today()
        
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end = date.today()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    # Query attendance records
    attendance_records = db.query(Attendance).filter(
        Attendance.date >= start,
        Attendance.date <= end
    ).order_by(Attendance.date, Attendance.student_id).all()
    
    # Convert to DataFrame
    data = [
        {
            "student_id": record.student_id,
            "date": record.date.strftime("%Y-%m-%d"),
            "present": record.present,
            "marked_at": record.marked_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for record in attendance_records
    ]
    
    df = pd.DataFrame(data)
    
    # Generate CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    # Return as streaming response
    filename = f"attendance_{start}_{end}.csv"
    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/admin/stats")
async def get_statistics(
    db: Session = Depends(get_db),
    _auth: None = Depends(require_admin_auth)
):
    """
    Get overall system statistics.
    Requires admin authentication.
    """
    total_students = db.query(Student).count()
    total_attendance_records = db.query(Attendance).count()
    today_attendance = db.query(Attendance).filter(Attendance.date == date.today()).count()
    
    return {
        "total_registered_students": total_students,
        "total_attendance_records": total_attendance_records,
        "today_attendance": today_attendance,
        "config": config.get_config_summary()
    }


# ============================================================================
# Health Check
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Attendance System Backend",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "config": config.get_config_summary()
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Run with HTTPS (required for webcam access)
    import os
    
    # Check if SSL certificates exist
    cert_file = os.path.join(os.path.dirname(__file__), "..", "certs", "cert.pem")
    key_file = os.path.join(os.path.dirname(__file__), "..", "certs", "key.pem")
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        # Run with HTTPS
        uvicorn.run(
            "main:app",
            host=config.HOST,
            port=config.PORT,
            reload=True,
            ssl_certfile=cert_file,
            ssl_keyfile=key_file
        )
    else:
        # Fallback to HTTP with warning
        print("⚠️  WARNING: SSL certificates not found!")
        print("⚠️  Webcam access requires HTTPS. Generate certificates with:")
        print("   cd certs && python generate_certs.py")
        uvicorn.run(
            "main:app",
            host=config.HOST,
            port=config.PORT,
            reload=True
        )
