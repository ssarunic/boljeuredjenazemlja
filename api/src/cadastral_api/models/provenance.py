"""Retrieval provenance: which register answered, from where, and when."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

#: The two registers a record can come from. The cadastre (katastar) records
#: possession and land use; the land registry (zemljišne knjige) records title.
Register = Literal["cadastre", "land_registry"]


def now_utc_iso() -> str:
    """The current time as ISO 8601 in UTC, to the second (``2026-09-15T12:00:00+00:00``)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Provenance:
    """Where a record came from and when it was fetched.

    Not part of any server response: the client stamps it on the record it
    parsed (the way ``lr_unit_derived_from_links`` is set after the fetch),
    so that a record forwarded to someone else names its register, the URL
    that answered and the time of retrieval, and is never mistaken for an
    official extract. A record built from a file or a fixture has none.

    A dataclass rather than a model because pydantic 2.12's ``BaseModel``
    owns an attribute called ``register``; nested in a model it is validated
    and serialised like one (``{"register", "source_url", "retrieved_at"}``).
    """

    #: Register the record was read from.
    register: Register
    #: URL of the request that returned the record.
    source_url: str
    #: When the record was retrieved (ISO 8601, UTC).
    retrieved_at: str

    def as_dict(self) -> dict[str, str]:
        """The three fields as a plain dict (what ``model_dump`` emits for it)."""
        return {
            "register": self.register,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
        }
