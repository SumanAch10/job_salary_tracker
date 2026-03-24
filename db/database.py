import os
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine, 
    Column, 
    Integer, 
    Text, 
    Float, 
    Boolean, 
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Load .env file
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Engine = the actual connection to PostgreSQL
engine = create_engine(DATABASE_URL)

# Base = parent class all our table models inherit from
Base = declarative_base()

# Session = how we interact with the DB (insert, query, update)
SessionLocal = sessionmaker(bind=engine)

# ─────────────────────────────────────────
# TABLE 1: raw_postings
# Stores exactly what we scrape — zero processing
# ─────────────────────────────────────────
class RawPosting(Base):
    __tablename__ = "raw_postings"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    title         = Column(Text)               # "Data Quality Analyst"
    company       = Column(Text)               # "The Black Car Fund"
    location      = Column(Text)               # "Long Island City, NY · Hybrid"
    salary_raw    = Column(Text, nullable=True) # "$110,000 - $120,000 a year" (often missing)
    job_type      = Column(Text, nullable=True) # "Full-time"
    url           = Column(Text, unique=True)   # unique prevents duplicate rows
    indeed_job_id = Column(Text, unique=True)   # Indeed's own ID from the URL
    scraped_at    = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────
# TABLE 2: clean_postings
# Processed, ML-ready version of raw data
# ─────────────────────────────────────────
class CleanPosting(Base):
    __tablename__ = "clean_postings"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    raw_id           = Column(Integer, ForeignKey("raw_postings.id"))  # links back to raw row
    title            = Column(Text)
    company          = Column(Text)
    location         = Column(Text)
    is_remote        = Column(Boolean, default=False)
    is_hybrid        = Column(Boolean, default=False)
    salary_min       = Column(Float, nullable=True)
    salary_max       = Column(Float, nullable=True)
    salary_mid       = Column(Float, nullable=True)   # ML target variable
    salary_type      = Column(Text, nullable=True)    # "annual" or "hourly"
    experience_level = Column(Text, nullable=True)    # "entry", "mid", "senior"
    job_type         = Column(Text, nullable=True)    # "full_time", "part_time"
    cleaned_at       = Column(DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────
# This creates both tables in PostgreSQL
# Safe to run multiple times — won't overwrite existing tables
# ─────────────────────────────────────────
def init_db():
    Base.metadata.create_all(engine)
    print("Tables created successfully")


def test_connection():
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()
        print(f"Connected to: {version[0]}")


if __name__ == "__main__":
    test_connection()
    init_db()