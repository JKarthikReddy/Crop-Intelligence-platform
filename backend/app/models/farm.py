"""Farm model with PostGIS spatial boundary."""

from geoalchemy2 import Geometry
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # PostGIS Polygon — WGS84
    boundary = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=False,
    )
