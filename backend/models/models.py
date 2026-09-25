from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Scheme(Base):
    __tablename__ = "schemes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    degree_level = Column(String(100), nullable=True)
    max_income = Column(Float, nullable=True)
    min_percentage = Column(Float, nullable=True)
    config_json = Column(Text, nullable=False)

    applications = relationship("Application", back_populates="scheme")

class Applicant(Base):
    __tablename__ = "applicants"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    category = Column(String(50), default="ST")
    caste_certificate_no = Column(String(100), nullable=True)
    annual_income = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    applications = relationship("Application", back_populates="applicant")

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    application_no = Column(String(100), unique=True, index=True, nullable=False)
    scheme_id = Column(Integer, ForeignKey("schemes.id"), nullable=False)
    applicant_id = Column(Integer, ForeignKey("applicants.id"), nullable=False)
    declared_data = Column(Text, nullable=False)  # JSON string
    confidence_score = Column(Float, default=90.0)  # 0 to 100
    status = Column(String(50), default="SUBMITTED")  # SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED, DEFICIENT
    ai_evaluation = Column(Text, nullable=True)  # JSON string of rule evaluation & mismatches
    admin_remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scheme = relationship("Scheme", back_populates="applications")
    applicant = relationship("Applicant", back_populates="applications")
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    doc_type = Column(String(100), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    status = Column(String(50), default="UPLOADED")  # UPLOADED, VERIFIED, DEFICIENT
    extracted_text = Column(Text, nullable=True)
    ocr_status = Column(String(50), default="PENDING")
    ocr_confidence = Column(Float, default=0.0)
    parsed_fields = Column(Text, nullable=True)
    failed_reason = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="documents")
