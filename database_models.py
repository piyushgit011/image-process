"""
Database Models for Image Processing Pipeline
Handles storage of processed image metadata and flags
"""

from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Text, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy import String
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

class ProcessedImage(Base):
    """Model for storing processed image metadata"""
    __tablename__ = "processed_images"
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(255), unique=True, nullable=False, index=True)
    original_filename = Column(String(500), nullable=False)
    s3_original_path = Column(String(1000), nullable=True)
    s3_processed_path = Column(String(1000), nullable=True)
    
    # Processing flags
    is_vehicle_detected = Column(Boolean, default=False, nullable=False)
    is_face_detected = Column(Boolean, default=False, nullable=False)
    is_face_blurred = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    content_type = Column(String(100), nullable=True)
    file_size_original = Column(Integer, nullable=True)
    file_size_processed = Column(Integer, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    
    # Detection details (JSON)
    vehicle_detection_data = Column(Text, nullable=True)  # JSON string
    face_detection_data = Column(Text, nullable=True)     # JSON string
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            'id': str(self.id),
            'job_id': self.job_id,
            'original_filename': self.original_filename,
            's3_original_path': self.s3_original_path,
            's3_processed_path': self.s3_processed_path,
            'is_vehicle_detected': self.is_vehicle_detected,
            'is_face_detected': self.is_face_detected,
            'is_face_blurred': self.is_face_blurred,
            'content_type': self.content_type,
            'file_size_original': self.file_size_original,
            'file_size_processed': self.file_size_processed,
            'processing_time_seconds': self.processing_time_seconds,
            'vehicle_detection_data': json.loads(self.vehicle_detection_data) if self.vehicle_detection_data else None,
            'face_detection_data': json.loads(self.face_detection_data) if self.face_detection_data else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }

class DatabaseManager:
    """Database manager for image processing pipeline"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        
    async def initialize(self):
        """Initialize database connection"""
        try:
            self.engine = create_engine(self.database_url)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    async def save_processed_image(
        self,
        job_id: str,
        original_filename: str,
        s3_original_path: Optional[str] = None,
        s3_processed_path: Optional[str] = None,
        is_vehicle_detected: bool = False,
        is_face_detected: bool = False,
        is_face_blurred: bool = False,
        content_type: Optional[str] = None,
        file_size_original: Optional[int] = None,
        file_size_processed: Optional[int] = None,
        processing_time_seconds: Optional[float] = None,
        vehicle_detection_data: Optional[Dict] = None,
        face_detection_data: Optional[Dict] = None
    ) -> ProcessedImage:
        """Save processed image record to database"""
        
        session = self.get_session()
        try:
            processed_image = ProcessedImage(
                job_id=job_id,
                original_filename=original_filename,
                s3_original_path=s3_original_path,
                s3_processed_path=s3_processed_path,
                is_vehicle_detected=is_vehicle_detected,
                is_face_detected=is_face_detected,
                is_face_blurred=is_face_blurred,
                content_type=content_type,
                file_size_original=file_size_original,
                file_size_processed=file_size_processed,
                processing_time_seconds=processing_time_seconds,
                vehicle_detection_data=json.dumps(vehicle_detection_data) if vehicle_detection_data else None,
                face_detection_data=json.dumps(face_detection_data) if face_detection_data else None,
                processed_at=datetime.utcnow()
            )
            
            session.add(processed_image)
            session.commit()
            session.refresh(processed_image)
            
            logger.info(f"Saved processed image record for job_id: {job_id}")
            return processed_image
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving processed image: {str(e)}")
            raise
        finally:
            session.close()
    
    async def get_processed_image_by_job_id(self, job_id: str) -> Optional[ProcessedImage]:
        """Get processed image record by job ID"""
        session = self.get_session()
        try:
            return session.query(ProcessedImage).filter(ProcessedImage.job_id == job_id).first()
        finally:
            session.close()
    
    async def get_processed_images_by_flags(
        self,
        is_vehicle_detected: Optional[bool] = None,
        is_face_detected: Optional[bool] = None,
        is_face_blurred: Optional[bool] = None,
        limit: int = 100
    ) -> list[ProcessedImage]:
        """Get processed images filtered by flags"""
        session = self.get_session()
        try:
            query = session.query(ProcessedImage)
            
            if is_vehicle_detected is not None:
                query = query.filter(ProcessedImage.is_vehicle_detected == is_vehicle_detected)
            if is_face_detected is not None:
                query = query.filter(ProcessedImage.is_face_detected == is_face_detected)
            if is_face_blurred is not None:
                query = query.filter(ProcessedImage.is_face_blurred == is_face_blurred)
            
            return query.limit(limit).all()
        finally:
            session.close()
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        session = self.get_session()
        try:
            total_images = session.query(ProcessedImage).count()
            vehicle_detected = session.query(ProcessedImage).filter(ProcessedImage.is_vehicle_detected == True).count()
            face_detected = session.query(ProcessedImage).filter(ProcessedImage.is_face_detected == True).count()
            face_blurred = session.query(ProcessedImage).filter(ProcessedImage.is_face_blurred == True).count()
            
            return {
                'total_images_processed': total_images,
                'vehicle_detection_count': vehicle_detected,
                'face_detection_count': face_detected,
                'face_blur_count': face_blurred,
                'vehicle_detection_rate': (vehicle_detected / total_images * 100) if total_images > 0 else 0,
                'face_detection_rate': (face_detected / total_images * 100) if total_images > 0 else 0,
                'face_blur_rate': (face_blurred / total_images * 100) if total_images > 0 else 0
            }
        finally:
            session.close()