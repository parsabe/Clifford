from alembic import context

from clifford.config import Settings
from clifford.persistence import Base, Store

settings = Settings()
# Ensure the SQLite parent directory exists before migration.
store = Store(settings.database_url)
target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(
        url=settings.database_url, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with store.engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
