from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# Create the SQLAlchemy engine
engine = create_engine(os.getenv('DATABASE_URL'))

# Create a session factory
Session = sessionmaker(bind=engine)
session = Session()

# Create a base class for declarative models
Base = declarative_base()

# Create all tables
def init_db():
    Base.metadata.create_all(engine)