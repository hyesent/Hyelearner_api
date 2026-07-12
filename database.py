from supabase import create_client
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# ============================================================
# SUPABASE CLIENT (For REST API)
# ============================================================
supabase = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY
)

supabase_admin = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)

# ============================================================
# SQLALCHEMY (For ORM Models — Keep for now)
# ============================================================

# Force IPv4 for SQLAlchemy
import socket
import os

def force_ipv4():
    original_getaddrinfo = socket.getaddrinfo
    def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        try:
            return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
        except socket.gaierror:
            return original_getaddrinfo(host, port, socket.AF_INET6, type, proto, flags)
    socket.getaddrinfo = new_getaddrinfo

force_ipv4()
os.environ['PGSSLMODE'] = 'require'

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={
        'connect_timeout': 10,
        'keepalives_idle': 5,
        'keepalives_interval': 2,
        'keepalives_count': 2,
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# This is what models.py needs
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================
# FUNCTION TO GET SUPABASE (For REST API routes)
# ============================================================
def get_supabase():
    return supabase

def get_supabase_admin():
    return supabase_admin