import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Comparable(Base):
    """Market comparable property (migrated from market_feed.json)."""

    __tablename__ = "comparables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)

    # Property details
    property_type       = Column(String(50),  nullable=False)
    area_sqm            = Column(Numeric(10, 2), nullable=False)
    age_years           = Column(Integer)
    finishing_level     = Column(String(50))
    quality_tier        = Column(String(50))

    # Location
    latitude            = Column(Numeric(10, 8))
    longitude           = Column(Numeric(11, 8))
    governorate         = Column(String(100))
    location_description = Column(Text)

    # Financial
    price_egp           = Column(Numeric(15, 2), nullable=False)
    price_per_sqm       = Column(Numeric(10, 2))

    # Metadata
    source              = Column(String(100))
    listed_date         = Column(Date)
    data_quality_score  = Column(Numeric(3, 2))

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationship: one comparable can be the primary ref for many valuations
    valuations = relationship("Valuation", back_populates="comparable")

    def __repr__(self) -> str:
        return (
            f"<Comparable {self.id}: {self.property_type} "
            f"{self.area_sqm}sqm {self.price_egp}EGP>"
        )


class Valuation(Base):
    """Full valuation result produced by the Phase 4–7 pipeline."""

    __tablename__ = "valuations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)

    # Property + purpose
    asset_type      = Column(String(50), nullable=False)
    primary_purpose = Column(String(50), nullable=False)

    # Optional link to a primary comparable
    comparable_id = Column(
        UUID(as_uuid=True), ForeignKey("comparables.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Results
    primary_value = Column(Numeric(15, 2))
    confidence    = Column(String(20))

    # Three-approach weights
    weight_comparable = Column(Numeric(4, 3))
    weight_cost       = Column(Numeric(4, 3))
    weight_income     = Column(Numeric(4, 3))

    # Phase 4 engine values
    comparable_value = Column(Numeric(15, 2))
    cost_value       = Column(Numeric(15, 2))
    income_value     = Column(Numeric(15, 2))

    # Comparable search metadata
    comparable_count     = Column(Integer)
    top_similarity_score = Column(Numeric(5, 2))

    # Full pipeline result (flexible JSONB)
    result_json = Column(JSONB)

    # Report metadata
    appraiser_name   = Column(String(100))
    property_address = Column(Text)
    valuation_date   = Column(Date)
    report_file_path = Column(String(255))

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    comparable = relationship("Comparable", back_populates="valuations")
    audit      = relationship("QualityAudit", back_populates="valuation",
                              uselist=False)

    def __repr__(self) -> str:
        return (
            f"<Valuation {self.id}: {self.asset_type} "
            f"{self.primary_value}EGP ({self.confidence})>"
        )


class QualityAudit(Base):
    """Quality audit result produced by ReportQualityAuditor."""

    __tablename__ = "quality_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)

    # FK — cascade delete keeps the table clean
    valuation_id = Column(
        UUID(as_uuid=True), ForeignKey("valuations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Overall result
    quality_score = Column(Numeric(5, 2))
    quality_grade = Column(String(1))
    passed        = Column(Boolean)

    # Per-category scores (reserved for future granular auditing)
    completeness_score = Column(Numeric(5, 2))
    methodology_score  = Column(Numeric(5, 2))
    compliance_score   = Column(Numeric(5, 2))
    data_quality_score = Column(Numeric(5, 2))

    # Full findings list (JSONB for flexibility)
    findings_json = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    valuation = relationship("Valuation", back_populates="audit")

    def __repr__(self) -> str:
        return (
            f"<QualityAudit {self.id}: "
            f"{self.quality_grade} ({self.quality_score}/100)>"
        )


class ActivityLog(Base):
    """Request / activity log for debugging and compliance."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)

    # What happened
    action      = Column(String(50), nullable=False)
    entity_type = Column(String(50))
    entity_id   = Column(UUID(as_uuid=True))

    # Who did it
    actor = Column(String(100))

    # Outcome
    success       = Column(Boolean)
    error_message = Column(Text)
    duration_ms   = Column(Integer)

    # Request / response detail
    details_json = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ActivityLog {self.id}: {self.action} {self.success}>"
