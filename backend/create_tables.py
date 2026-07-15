from app.core.database import Base, engine
from app.models import *  # noqa

Base.metadata.create_all(engine)
print("Database tables created.")
