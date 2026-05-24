from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON, ForeignKey
from database import Base

class Series(Base):
    """
    Represents an Anime or Manga series tracked by the harness.
    """
    __tablename__ = "series"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    series_type = Column(String, default="animeSeries")
    metadata_payload = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectMemory(Base):
    """
    Persists editorial preference memory parameters.
    """
    __tablename__ = "project_memories"

    key = Column(String, primary_key=True, index=True)
    value = Column(JSON, default=[])


class Job(Base):
    """
    Represents a dynamic multi-agent execution pipeline job.
    """
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    target_type = Column(String, nullable=False)  # youtube_short, editorial_blog
    series_id = Column(String, ForeignKey("series.id"), nullable=True, index=True)
    series_title = Column(String, nullable=False)
    status = Column(String, default="queued", index=True)

    # Intelligence Harness specific fields
    structured_task = Column(JSON, default={})
    execution_plan = Column(JSON, default=[])
    evaluations = Column(JSON, default={})
    memory_logs = Column(JSON, default=[])

    # Legacy & intermediate worker data for backward compatibility
    collector_data = Column(JSON, default={})
    theme_data = Column(JSON, default={})
    writer_data = Column(JSON, default={})
    seo_data = Column(JSON, default={})
    formatter_data = Column(JSON, default={})
    publisher_data = Column(JSON, default={})

    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
