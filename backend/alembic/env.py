from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import app.db  # noqa: F401 — registers all models
from app.db.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate support
target_metadata = Base.metadata

# Exclude PostGIS system schemas and tables from autogenerate
EXCLUDE_SCHEMAS = {"tiger", "tiger_data", "topology"}
POSTGIS_TABLES = {
    "spatial_ref_sys", "topology", "layer", "geocode_settings",
    "geocode_settings_default", "loader_lookuptables", "loader_platform",
    "loader_variables", "pagc_gaz", "pagc_lex", "pagc_rules",
    "zip_lookup", "zip_lookup_all", "zip_lookup_base", "zip_state",
    "zip_state_loc", "direction_lookup", "secondary_unit_lookup",
    "street_type_lookup", "state_lookup", "county_lookup",
    "countysub_lookup", "place_lookup", "state", "county", "cousub",
    "place", "tract", "tabblock", "tabblock20", "bg", "zcta5", "faces",
    "featnames", "edges", "addr", "addrfeat",
}


def include_object(obj, name, type_, reflected, compare_to):
    """Filter out PostGIS system tables from autogenerate."""
    if type_ == "table":
        if name in POSTGIS_TABLES:
            return False
        if hasattr(obj, "schema") and obj.schema in EXCLUDE_SCHEMAS:
            return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
