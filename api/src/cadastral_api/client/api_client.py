"""HTTP client for Croatian Cadastral API with rate limiting and error handling.

⚠️ DEMO/EDUCATIONAL PROJECT ONLY ⚠️

This client demonstrates how a cadastral API integration could work.
It is configured to use a MOCK SERVER by default for safe testing and learning.

BEFORE USING ANOTHER SERVER:
- Verify that you have the rights to use that server and its data (terms of
  service, data protection); real cadastral data is personal data
- You do so at your own risk; see docs/legal.md
- Do not bypass authorization, rate limits or access restrictions

The author is available to advise the Croatian government on official AI and API
implementation if requested.

See README.md and CLAUDE.md for complete disclaimer.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Literal, TypeVar

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from ..exceptions import CadastralAPIError, ErrorType
from ..gis import GISCache, GMLParser
from ..models import (
    BookOfDCSearchResult,
    CadastralOffice,
    FileStatus,
    LandRegistryUnitDetailed,
    MainBookSearchResult,
    MunicipalitySearchResult,
    ParcelInfo,
    ParcelSearchResult,
    PossessionSheetSearchResult,
)
from ..models.gis_entities import ParcelGeometry
from ..utils import is_building_parcel_number, normalize_parcel_number, parse_file_number

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

UnknownFieldsPolicy = Literal["warn", "ignore", "error"]
UNKNOWN_FIELDS_POLICIES: tuple[str, ...] = ("warn", "ignore", "error")

# Unknown key paths already reported by this process (logged once each).
_REPORTED_UNKNOWN_FIELDS: set[str] = set()

M = TypeVar("M", bound=BaseModel)


class CadastralAPIClient:
    """
    Client for Croatian Cadastral System API (Uređena zemlja).

    Provides methods to search for parcels and retrieve detailed information
    with automatic rate limiting and retry logic.
    """

    # Default to localhost test server (production API requires authorization)
    BASE_URL = os.getenv("CADASTRAL_API_BASE_URL", "http://localhost:8000")
    DEFAULT_TIMEOUT = float(os.getenv("CADASTRAL_API_TIMEOUT", "10.0"))
    DEFAULT_RATE_LIMIT = float(os.getenv("CADASTRAL_API_RATE_LIMIT", "0.375"))
    DEFAULT_UNKNOWN_FIELDS = os.getenv("CADASTRAL_API_UNKNOWN_FIELDS", "warn")
    MAX_RETRIES = 3

    def __init__(
        self,
        base_url: str | None = None,
        rate_limit: float | None = None,
        timeout: float | None = None,
        cache_dir: Path | str | None = None,
        unknown_fields: UnknownFieldsPolicy | None = None,
    ) -> None:
        """
        Initialize the API client.

        Args:
            base_url: API base URL (default: from CADASTRAL_API_BASE_URL env or http://localhost:8000)
            rate_limit: Minimum seconds between requests
                (default: from CADASTRAL_API_RATE_LIMIT env or 0.375)
            timeout: Request timeout in seconds (default: from CADASTRAL_API_TIMEOUT env or 10.0)
            cache_dir: Directory for GIS data cache (default: ~/.cadastral_api_cache)
            unknown_fields: What to do when a response carries a key no model
                declares (it is kept in ``source_fields`` either way):
                ``"warn"`` logs each new key path once per process (default),
                ``"ignore"`` stays silent, ``"error"`` raises
                ``CadastralAPIError(INVALID_RESPONSE, reason="unknown_fields")``.

        Environment Variables:
            CADASTRAL_API_BASE_URL: API base URL (default: http://localhost:8000)
            CADASTRAL_API_RATE_LIMIT: Rate limit in seconds (default: 0.375)
            CADASTRAL_API_TIMEOUT: Request timeout in seconds (default: 10.0)
            CADASTRAL_API_UNKNOWN_FIELDS: warn | ignore | error (default: warn)

        Note:
            Before pointing the client at any server other than the included
            mock, verify that you have the rights to use that server; see
            docs/legal.md. Use is at your own risk.
        """
        self.base_url = base_url or self.BASE_URL
        self.rate_limit = rate_limit if rate_limit is not None else self.DEFAULT_RATE_LIMIT
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        policy = unknown_fields or self.DEFAULT_UNKNOWN_FIELDS
        if policy not in UNKNOWN_FIELDS_POLICIES:
            raise ValueError(
                f"unknown_fields must be one of {UNKNOWN_FIELDS_POLICIES}, got {policy!r}"
            )
        self.unknown_fields: UnknownFieldsPolicy = policy  # type: ignore[assignment]
        self._last_request_time: float = 0.0

        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
        }

        self.client = httpx.Client(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
        )

        # Initialize GIS cache
        self.gis_cache = GISCache(cache_dir, base_url=self.base_url)

    def __enter__(self) -> "CadastralAPIClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - close HTTP client."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def _wait_for_rate_limit(self) -> None:
        """
        Enforce rate limiting between requests.

        Waits until enough time has passed since the last request.
        """
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time

        if time_since_last_request < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last_request
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def _make_request(
        self, endpoint: str, params: dict[str, str] | None = None, retry_count: int = 0
    ) -> dict:
        """
        Make HTTP request with rate limiting and retry logic.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            retry_count: Current retry attempt number

        Returns:
            JSON response as dictionary

        Raises:
            CadastralAPIError: Any API error occurred
        """
        self._wait_for_rate_limit()

        try:
            response = self.client.get(endpoint, params=params)

            # Handle rate limiting
            if response.status_code == 429:
                if retry_count < self.MAX_RETRIES:
                    time.sleep(2 ** retry_count)  # Exponential backoff
                    return self._make_request(endpoint, params, retry_count + 1)
                raise CadastralAPIError(
                    error_type=ErrorType.RATE_LIMIT,
                    details={"retry_count": retry_count, "max_retries": self.MAX_RETRIES},
                )

            # Handle server errors with retry
            if 500 <= response.status_code < 600:
                if retry_count < self.MAX_RETRIES:
                    time.sleep(1.5 ** retry_count)
                    return self._make_request(endpoint, params, retry_count + 1)
                raise CadastralAPIError(
                    error_type=ErrorType.SERVER_ERROR,
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "retry_count": retry_count,
                    },
                )

            # Raise for other error codes
            response.raise_for_status()

            return response.json()

        except httpx.TimeoutException as e:
            raise CadastralAPIError(
                error_type=ErrorType.TIMEOUT,
                details={"timeout_seconds": self.timeout, "endpoint": endpoint},
                cause=e,
            ) from e
        except httpx.ConnectError as e:
            raise CadastralAPIError(
                error_type=ErrorType.CONNECTION,
                details={"endpoint": endpoint},
                cause=e,
            ) from e
        except httpx.HTTPError as e:
            raise CadastralAPIError(
                error_type=ErrorType.CONNECTION,
                details={"endpoint": endpoint},
                cause=e,
            ) from e
        except ValueError as e:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint},
                cause=e,
            ) from e

    def _make_post_request(
        self, endpoint: str, json_body: dict, retry_count: int = 0
    ) -> dict:
        """Make a POST request with rate limiting and retry logic.

        Mirrors :meth:`_make_request` (GET) for the few endpoints that require a
        JSON body, e.g. ``/lr/file-status``.

        Args:
            endpoint: API endpoint path
            json_body: JSON request body
            retry_count: Current retry attempt number

        Returns:
            JSON response as a dictionary

        Raises:
            CadastralAPIError: Any API error occurred
        """
        self._wait_for_rate_limit()

        try:
            response = self.client.post(endpoint, json=json_body)

            if response.status_code == 429:
                if retry_count < self.MAX_RETRIES:
                    time.sleep(2 ** retry_count)
                    return self._make_post_request(endpoint, json_body, retry_count + 1)
                raise CadastralAPIError(
                    error_type=ErrorType.RATE_LIMIT,
                    details={"retry_count": retry_count, "max_retries": self.MAX_RETRIES},
                )

            if 500 <= response.status_code < 600:
                if retry_count < self.MAX_RETRIES:
                    time.sleep(1.5 ** retry_count)
                    return self._make_post_request(endpoint, json_body, retry_count + 1)
                raise CadastralAPIError(
                    error_type=ErrorType.SERVER_ERROR,
                    details={
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "retry_count": retry_count,
                    },
                )

            response.raise_for_status()

            return response.json()

        except httpx.TimeoutException as e:
            raise CadastralAPIError(
                error_type=ErrorType.TIMEOUT,
                details={"timeout_seconds": self.timeout, "endpoint": endpoint},
                cause=e,
            ) from e
        except httpx.ConnectError as e:
            raise CadastralAPIError(
                error_type=ErrorType.CONNECTION,
                details={"endpoint": endpoint},
                cause=e,
            ) from e
        except httpx.HTTPError as e:
            raise CadastralAPIError(
                error_type=ErrorType.CONNECTION,
                details={"endpoint": endpoint},
                cause=e,
            ) from e
        except ValueError as e:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint},
                cause=e,
            ) from e

    # ------------------------------------------------------------------
    # Response validation
    # ------------------------------------------------------------------

    def _parse(
        self, model: type[M], data: Any, endpoint: str, details: dict[str, Any] | None = None
    ) -> M:
        """Validate one server object into ``model`` and apply the unknown-fields policy."""
        try:
            instance = model.model_validate(data)
        except ValidationError as e:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint, **(details or {}), "reason": "validation_failed"},
                cause=e,
            ) from e
        self._check_unknown_fields(instance, endpoint, details)
        return instance

    def _parse_list(
        self, model: type[M], data: Any, endpoint: str, details: dict[str, Any] | None = None
    ) -> list[M]:
        """Validate a list response; the unknown-fields policy applies to every item."""
        if not isinstance(data, list):
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint, **(details or {}), "reason": "not_a_list"},
            )
        return [self._parse(model, item, endpoint, details) for item in data]

    def _check_unknown_fields(
        self, instance: BaseModel, endpoint: str, details: dict[str, Any] | None
    ) -> None:
        if self.unknown_fields == "ignore":
            return
        unknown = sorted(_unknown_field_paths(instance, endpoint))
        if not unknown:
            return
        if self.unknown_fields == "error":
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={
                    "endpoint": endpoint,
                    **(details or {}),
                    "reason": "unknown_fields",
                    "unknown_fields": ", ".join(unknown),
                },
            )
        for path in unknown:
            if path not in _REPORTED_UNKNOWN_FIELDS:
                _REPORTED_UNKNOWN_FIELDS.add(path)
                logger.warning(
                    "Server sent a field no model declares: %s (kept in source_fields)", path
                )

    def list_cadastral_offices(self) -> list[CadastralOffice]:
        """
        List all cadastral offices (Područni uredi za katastar) in Croatia.

        Returns:
            List of CadastralOffice objects (21 offices total)

        Raises:
            CadastralAPIError: Any API error occurred

        Note:
            Returns complete list of all cadastral offices without pagination.
            Office IDs match the institutionId field in parcel information responses.
        """
        endpoint = "/search-cad-parcels/offices"

        response_data = self._make_request(endpoint)

        if not response_data:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint, "reason": "empty_response"},
            )

        return self._parse_list(CadastralOffice, response_data, endpoint)

    def find_municipality(
        self,
        search_term: str | None = None,
        office_id: str | None = None,
        department_id: str | None = None,
    ) -> list[MunicipalitySearchResult]:
        """
        Find municipalities by name, code, or filter by cadastral office/department.

        Args:
            search_term: Municipality name (e.g., "SAVAR") or code (e.g., "334979")
            office_id: Filter by cadastral office ID (e.g., "114" for Zadar)
            department_id: Filter by department ID (e.g., "116")

        Returns:
            List of MunicipalitySearchResult objects

        Raises:
            CadastralAPIError: Any API error occurred

        Examples:
            # Find by name
            municipalities = client.find_municipality("SAVAR")

            # Filter by office (162 municipalities in Zadar office)
            municipalities = client.find_municipality(office_id="114")

            # Filter by office and department (66 municipalities)
            municipalities = client.find_municipality(office_id="114", department_id="116")

            # Combine search with filters
            municipalities = client.find_municipality("SAVAR", office_id="114")

        Note:
            - All parameters are optional but at least one should be provided
            - Partial name searches return multiple results (e.g., "LUKA" returns 16 municipalities)
            - office_id corresponds to institutionId from cadastral offices
        """
        endpoint = "/search-cad-parcels/municipalities"
        params: dict[str, str] = {}

        if search_term:
            params["search"] = str(search_term)
        if office_id:
            params["officeId"] = str(office_id)
        if department_id:
            params["departmentId"] = str(department_id)

        response_data = self._make_request(endpoint, params if params else None)

        if not response_data:
            raise CadastralAPIError(
                error_type=ErrorType.MUNICIPALITY_NOT_FOUND,
                details={
                    "search_term": search_term,
                    "office_id": office_id,
                    "department_id": department_id,
                },
            )

        return self._parse_list(MunicipalitySearchResult, response_data, endpoint)

    def find_parcel(
        self, parcel_number: str, municipality_reg_num: str
    ) -> list[ParcelSearchResult]:
        """
        Find parcel IDs by parcel number and municipality.

        Args:
            parcel_number: Parcel number (e.g., "103/2", "114"). Building parcels
                may be written as "35/1.ZGR", "35/1 ZGR", "zgr. 35/1" or "*35/1";
                every form is sent as the API spelling "*35/1".
            municipality_reg_num: Municipality registration number (e.g., "334979")

        Returns:
            List of ParcelSearchResult objects

        Raises:
            CadastralAPIError: Any API error occurred

        Note:
            The server matches on the prefix: "114" returns 114, 1140/1, etc.;
            "1072/1" returns 1072/1, 1072/10, 1072/11, ... A leading asterisk acts
            as a wildcard ("*35/1" also returns 135/1).
        """
        endpoint = "/search-cad-parcels/parcel-numbers"
        params = {
            "search": normalize_parcel_number(str(parcel_number)),
            "municipalityRegNum": municipality_reg_num,
        }

        response_data = self._make_request(endpoint, params)

        if not response_data:
            raise CadastralAPIError(
                error_type=ErrorType.PARCEL_NOT_FOUND,
                details={
                    "parcel_number": parcel_number,
                    "municipality_reg_num": municipality_reg_num,
                },
            )

        return self._parse_list(ParcelSearchResult, response_data, endpoint)

    def find_possession_sheet(
        self, sheet_number: str, municipality_reg_num: str
    ) -> list[PossessionSheetSearchResult]:
        """
        Find possession sheets (posjedovni listovi) by sheet number.

        ``GET /search-cad-parcels/possession-sheet-numbers``. The records carry
        the ``possessionSheetId`` that parcel-info ``possessionSheets[]`` use and
        the sheet number; no endpoint returns a sheet by id, so this search is
        all the API offers (open question OQ4 of the coverage specification).

        Args:
            sheet_number: Possession sheet number (prefix match, e.g. "363")
            municipality_reg_num: Municipality registration number (e.g., "334979")

        Returns:
            List of PossessionSheetSearchResult objects (empty when nothing matches)
        """
        endpoint = "/search-cad-parcels/possession-sheet-numbers"
        params = {"search": str(sheet_number), "municipalityRegNum": municipality_reg_num}
        response_data = self._make_request(endpoint, params)
        return self._parse_list(PossessionSheetSearchResult, response_data or [], endpoint)

    def find_main_book(
        self,
        search: str | None = None,
        office_id: str | None = None,
        institution_name: str | None = None,
    ) -> list[MainBookSearchResult]:
        """
        Find land-registry main books (glavne knjige) by name, office or institution.

        ``GET /search-lr-parcels/main-books``. This is the link from a
        municipality name to the ``main_book_id`` that ``get_lr_unit_detailed``
        needs: searching "SAVAR" returns main book 21277 of the Zadar court
        (institution 284).

        Args:
            search: Book name to search for (e.g., "SAVAR"); empty returns every book
            office_id: Filter by land-registry office (institution) id, e.g. "284"
            institution_name: Filter by institution name

        Returns:
            List of MainBookSearchResult objects (empty when nothing matches)
        """
        endpoint = "/search-lr-parcels/main-books"
        params = {
            "search": search or "",
            "officeId": office_id or "",
            "institutionName": institution_name or "",
        }
        response_data = self._make_request(endpoint, params)
        return self._parse_list(MainBookSearchResult, response_data or [], endpoint)

    def find_book_of_dc(
        self,
        search: str | None = None,
        office_id: str | None = None,
        institution_name: str | None = None,
    ) -> list[BookOfDCSearchResult]:
        """
        Find books of deposited contracts (knjige položenih ugovora, KPU).

        ``GET /search-lr-parcels/books-of-dc``. Same parameters as
        :meth:`find_main_book`. Whether a book id can be passed to the lr-unit
        endpoint as ``mainBookId`` is unverified (OQ5), so this returns the
        search records only.

        Args:
            search: Book name to search for (e.g., "ZADAR")
            office_id: Filter by land-registry office id
            institution_name: Filter by institution name

        Returns:
            List of BookOfDCSearchResult objects (empty when nothing matches)
        """
        endpoint = "/search-lr-parcels/books-of-dc"
        params = {
            "search": search or "",
            "officeId": office_id or "",
            "institutionName": institution_name or "",
        }
        response_data = self._make_request(endpoint, params)
        return self._parse_list(BookOfDCSearchResult, response_data or [], endpoint)

    def resolve_main_book_id(self, main_book_name: str) -> int:
        """
        Resolve a main book name ("SAVAR") to its id through :meth:`find_main_book`.

        Raises:
            CadastralAPIError: ``LR_UNIT_NOT_FOUND`` with reason
                ``main_book_not_found`` when no book matches the name exactly, or
                ``main_book_ambiguous`` (with the candidates) when several do.
        """
        books = self.find_main_book(main_book_name)
        wanted = main_book_name.strip().casefold()
        exact = [b for b in books if b.main_book_name.strip().casefold() == wanted]
        if len(exact) == 1:
            return exact[0].main_book_id
        if not exact:
            raise CadastralAPIError(
                error_type=ErrorType.LR_UNIT_NOT_FOUND,
                details={
                    "main_book_name": main_book_name,
                    "reason": "main_book_not_found",
                    "candidates": ", ".join(b.main_book_name for b in books) or None,
                },
            )
        raise CadastralAPIError(
            error_type=ErrorType.LR_UNIT_NOT_FOUND,
            details={
                "main_book_name": main_book_name,
                "reason": "main_book_ambiguous",
                "candidates": ", ".join(
                    f"{b.main_book_name} ({b.main_book_id}, {b.court_name})" for b in exact
                ),
            },
        )

    def get_parcel_info(self, parcel_id: str | int) -> ParcelInfo:
        """
        Get complete parcel information including ownership data.

        Args:
            parcel_id: Parcel ID obtained from search_parcel()

        Returns:
            ParcelInfo object with complete parcel details

        Raises:
            CadastralAPIError: Any API error occurred
        """
        endpoint = "/cad/parcel-info"
        params = {"parcelId": str(parcel_id)}

        response_data = self._make_request(endpoint, params)

        if not response_data:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={
                    "endpoint": endpoint,
                    "parcel_id": str(parcel_id),
                    "reason": "empty_response",
                },
            )

        return self._parse(ParcelInfo, response_data, endpoint, {"parcel_id": str(parcel_id)})

    def get_parcel_by_number(
        self, parcel_number: str, municipality_reg_num: str, exact_match: bool = True
    ) -> ParcelInfo | None:
        """
        Convenience method to find and retrieve parcel info in one call.

        Args:
            parcel_number: Parcel number (e.g., "103/2"); building parcels in any
                spelling ("35/1.ZGR", "zgr. 35/1", "*35/1")
            municipality_reg_num: Municipality registration number
            exact_match: If True, only return exact parcel number match

        Returns:
            ParcelInfo object if found, None otherwise

        Raises:
            CadastralAPIError: Any API error occurred; ``PARCEL_NOT_FOUND`` with
                reason ``only_building_parcel_exists`` when the caller asked for
                a land parcel ("35/1") and only the building parcel ("*35/1")
                exists, so the two are never confused.
        """
        wanted = normalize_parcel_number(parcel_number)
        search_results = self.find_parcel(wanted, municipality_reg_num)

        if not search_results:
            return None

        # Find exact match if requested
        if exact_match:
            for result in search_results:
                if result.parcel_number == wanted:
                    return self.get_parcel_info(result.parcel_id)
            candidates = [r.parcel_number for r in search_results]
            if not is_building_parcel_number(wanted) and f"*{wanted}" in candidates:
                raise CadastralAPIError(
                    error_type=ErrorType.PARCEL_NOT_FOUND,
                    details={
                        "parcel_number": parcel_number,
                        "municipality_reg_num": municipality_reg_num,
                        "reason": "only_building_parcel_exists",
                        "candidates": ", ".join(candidates),
                    },
                )
            return None

        # Return first result
        return self.get_parcel_info(search_results[0].parcel_id)

    def get_map_url(self, parcel_id: str | int) -> str:
        """
        Generate interactive map URL for a parcel.

        Args:
            parcel_id: Parcel ID

        Returns:
            URL to view parcel on interactive map
        """
        return f"https://oss.uredjenazemlja.hr/map?cad_parcel_id={parcel_id}"

    def get_municipality_gis_download_url(self, municipality_reg_num: str) -> str:
        """
        Generate GIS data download URL for a municipality (ATOM feed).

        Returns URL for downloading a ZIP file containing parcel boundaries and other
        GIS information in GML format for the specified municipality.

        Args:
            municipality_reg_num: Municipality registration number (e.g., "334979" for SAVAR)

        Returns:
            URL to download municipality GIS data ZIP file

        Example:
            url = client.get_municipality_gis_download_url("334979")
            # Returns: "https://oss.uredjenazemlja.hr/oss/public/atom/ko-334979.zip"

            # Direct download works without authentication
            import httpx
            response = httpx.get(url)
            with open("savar.zip", "wb") as f:
                f.write(response.content)

        ZIP Contents:
            - katastarske_cestice.gml - Cadastral parcels (~1.4 MB for SAVAR)
            - katastarske_opcine.gml - Cadastral municipalities
            - nacini_uporabe_zemljista.gml - Land use types
            - nacini_uporabe_zgrada.gml - Building use types

        Note:
            - No authentication required - direct download works
            - INSPIRE-compliant spatial datasets
            - File sizes range from ~200KB to several MB per municipality
            - Suitable for automated bulk downloads
            - The 'ko-' prefix stands for "katastarska općina" (cadastral municipality)
        """
        return f"https://oss.uredjenazemlja.hr/oss/public/atom/ko-{municipality_reg_num}.zip"

    def get_parcel_geometry(
        self, parcel_number: str, municipality_reg_num: str
    ) -> ParcelGeometry | None:
        """
        Get parcel geometry (boundary coordinates) from GIS data.

        Downloads municipality GIS data (if not cached), extracts GML file,
        and returns parcel geometry with boundary coordinates.

        Args:
            parcel_number: Parcel number (e.g., "103/2", "114")
            municipality_reg_num: Municipality registration number (e.g., "334979")

        Returns:
            ParcelGeometry object with coordinates, or None if not found

        Example:
            geometry = client.get_parcel_geometry("103/2", "334979")
            if geometry:
                print(f"Parcel: {geometry.broj_cestice}")
                print(f"Area: {geometry.povrsina_graficka} m²")
                print(f"Vertices: {geometry.coordinate_count}")
                print(f"Bounds: {geometry.bounds}")

                # Export to WKT
                wkt = geometry.to_wkt()

                # Get coordinates for mapping
                coords = geometry.to_geojson_coords()

        Note:
            - First call downloads and caches municipality GIS data (~200KB-several MB)
            - Subsequent calls use cached data (fast)
            - Coordinates are in EPSG:3765 (HTRS96/TM) projection
            - Use gis_cache.clear_municipality() to clear cache for a municipality
        """
        # Download and cache GIS data
        gml_path = self.gis_cache.get_parcel_data(municipality_reg_num, auto_download=True)

        # Parse GML and find parcel
        parser = GMLParser(gml_path)
        return parser.get_parcel_by_number(parcel_number)

    def get_lr_unit_detailed(
        self,
        lr_unit_number: str,
        main_book_id: int | None = None,
        historical_overview: bool = False,
        *,
        main_book_name: str | None = None,
    ) -> LandRegistryUnitDetailed:
        """
        Get detailed land registry unit information including all sheets (A, B, C).

        This method retrieves complete information about a land registry unit
        (zemljišnoknjižni uložak), including:
        - Sheet A: List of all cadastral parcels in the unit
        - Sheet B: Ownership information with co-owners and shares
        - Sheet C: Encumbrances (mortgages, liens, easements, etc.)

        Args:
            lr_unit_number: Land registry unit number (e.g., "769")
            main_book_id: Main book ID (e.g., 21277 for SAVAR). May be omitted
                when ``main_book_name`` is given.
            historical_overview: Include historical data (default: False)
            main_book_name: Main book name (e.g., "SAVAR"), resolved to its id
                through the main-book search (:meth:`resolve_main_book_id`)
                when ``main_book_id`` is not given.

        Returns:
            LandRegistryUnitDetailed object with complete unit information

        Raises:
            CadastralAPIError: Any API error occurred; ``LR_UNIT_NOT_FOUND`` with
                reason ``main_book_ambiguous`` when the name matches several books.
            ValueError: Neither ``main_book_id`` nor ``main_book_name`` was given.

        Example:
            # Get LR unit details
            lr_unit = client.get_lr_unit_detailed("769", 21277)
            lr_unit = client.get_lr_unit_detailed("769", main_book_name="SAVAR")

            # Access ownership information
            owners = lr_unit.get_all_owners()
            for owner in owners:
                print(f"Owner: {owner.name}, OIB: {owner.tax_number}")

            # Check for encumbrances
            if lr_unit.has_sheet_c_entries():
                print("Unit has encumbrances (mortgages, liens, etc.)")

            # Get summary
            summary = lr_unit.summary()
            print(f"Total parcels: {summary['total_parcels']}")
            print(f"Total area: {summary['total_area_m2']} m²")

        Note:
            ⚠️ Demo project: verify your rights before using any server other than the mock.
            The API response is returned as a list with typically one element.
        """
        if main_book_id is None:
            if not main_book_name:
                raise ValueError("get_lr_unit_detailed needs main_book_id or main_book_name")
            main_book_id = self.resolve_main_book_id(main_book_name)

        endpoint = "/lr/lr-unit"
        params = {
            "lrUnitNumber": str(lr_unit_number),
            "mainBookId": str(main_book_id),
            "historicalOverview": str(historical_overview).lower(),
        }

        response_data = self._make_request(endpoint, params)

        if not response_data:
            raise CadastralAPIError(
                error_type=ErrorType.LR_UNIT_NOT_FOUND,
                details={
                    "lr_unit_number": lr_unit_number,
                    "main_book_id": main_book_id,
                    "reason": "empty_response",
                },
            )

        # API returns a list, typically with one element
        if isinstance(response_data, list):
            if not response_data:
                raise CadastralAPIError(
                    error_type=ErrorType.LR_UNIT_NOT_FOUND,
                    details={
                        "lr_unit_number": lr_unit_number,
                        "main_book_id": main_book_id,
                        "reason": "empty_list_response",
                    },
                )
            response_data = response_data[0]

        return self._parse(
            LandRegistryUnitDetailed,
            response_data,
            endpoint,
            {"lr_unit_number": lr_unit_number, "main_book_id": main_book_id},
        )

    def get_lr_unit_from_parcel(
        self,
        parcel_number: str,
        municipality: str | int,
        historical_overview: bool = False,
    ) -> LandRegistryUnitDetailed:
        """
        Convenience method to get LR unit details by first looking up parcel.

        This method performs a two-step process:
        1. Searches for the parcel to get its lr_unit information
        2. Retrieves detailed LR unit information using the found unit number and main book ID

        Args:
            parcel_number: Parcel number (e.g., "103/2", "279/6")
            municipality: Municipality name (e.g., "SAVAR") or registration number (e.g., "334979")
            historical_overview: Include historical data (default: False)

        Returns:
            LandRegistryUnitDetailed object with complete unit information

        Raises:
            CadastralAPIError: Any API error occurred (parcel not found, LR unit not found, etc.)

        Example:
            # Get LR unit details for a specific parcel
            lr_unit = client.get_lr_unit_from_parcel("279/6", "SAVAR")

            # See all parcels in the same LR unit
            all_parcels = lr_unit.get_all_parcels()
            for parcel in all_parcels:
                print(f"Parcel: {parcel.parcel_number}, Area: {parcel.area_numeric} m²")

            # Get all co-owners
            owners = lr_unit.get_all_owners()
            print(f"Number of co-owners: {len(owners)}")

        Note:
            ⚠️ Demo project: verify your rights before using any server other than the mock.
            This is a convenience wrapper that combines parcel lookup with LR unit retrieval.
        """
        parcel_number = normalize_parcel_number(parcel_number)
        municipality = str(municipality)

        # If municipality is a name, find it
        if not municipality.isdigit():
            municipalities = self.find_municipality(str(municipality))
            if not municipalities:
                raise CadastralAPIError(
                    error_type=ErrorType.MUNICIPALITY_NOT_FOUND,
                    details={"municipality": municipality},
                )
            municipality_reg_num = municipalities[0].municipality_reg_num
        else:
            municipality_reg_num = str(municipality)

        # Get parcel info to extract LR unit details
        parcel_info = self.get_parcel_by_number(parcel_number, municipality_reg_num)

        if not parcel_info:
            raise CadastralAPIError(
                error_type=ErrorType.PARCEL_NOT_FOUND,
                details={
                    "parcel_number": parcel_number,
                    "municipality": municipality,
                },
            )

        # Resolve the LR unit reference, falling back to parcel links when the
        # parcel has no direct lr_unit (a common case - the unit is still
        # reachable via lr_units_from_parcel_links / parcel_links).
        ref = self._resolve_lr_unit_ref(parcel_info)
        if ref is None:
            # Building parcels never carry a land-registry reference: the
            # building is registered on its land parcel.
            raise CadastralAPIError(
                error_type=ErrorType.LR_UNIT_NOT_FOUND,
                details={
                    "parcel_number": parcel_number,
                    "municipality": municipality,
                    "reason": "parcel_not_in_land_registry",
                    "is_building_parcel": parcel_info.is_building_parcel or None,
                },
            )
        lr_unit_number, main_book_id = ref
        derived_from_links = parcel_info.lr_unit is None

        # Get detailed LR unit information
        lr_unit = self.get_lr_unit_detailed(
            lr_unit_number=lr_unit_number,
            main_book_id=main_book_id,
            historical_overview=historical_overview,
        )
        lr_unit.lr_unit_derived_from_links = derived_from_links
        lr_unit.cadastre_harmonized = parcel_info.is_harmonized
        return lr_unit

    @staticmethod
    def _resolve_lr_unit_ref(parcel_info: ParcelInfo) -> tuple[str, int] | None:
        """Resolve an (lr_unit_number, main_book_id) reference from a parcel.

        Prefers the direct ``lr_unit``; otherwise falls back to the units
        carried by parcel links. Returns None when the parcel is not in the
        land registry at all, and raises ``LR_UNIT_NOT_FOUND`` with reason
        ``lr_unit_ambiguous`` when the links name different units.
        """
        unit = parcel_info.resolved_lr_unit()
        if unit is None:
            return None
        if parcel_info.lr_unit is None:
            # Without a direct unit, links that disagree must not be resolved
            # by taking the first one.
            refs = {(c.lr_unit_number, c.main_book_id) for c in parcel_info.lr_unit_candidates()}
            if len(refs) > 1:
                raise CadastralAPIError(
                    error_type=ErrorType.LR_UNIT_NOT_FOUND,
                    details={
                        "parcel_number": parcel_info.parcel_number,
                        "reason": "lr_unit_ambiguous",
                        "candidates": ", ".join(f"{n}/{b}" for n, b in sorted(refs)),
                    },
                )
        return unit.lr_unit_number, unit.main_book_id

    def get_file_status(
        self, file_number: str, institution_id: int
    ) -> FileStatus | None:
        """Get the processing status (detail) of a single land-registry file.

        A unit's ``activePlumbs`` only carry the bare file number (e.g.
        ``"Z-12564/2026"``). This resolves that number to its full status -
        what the request is, its processing stage, and key dates - via
        ``POST /lr/file-status``.

        The endpoint wants the number split into parts plus the owning
        institution; the institution comes from the unit
        (``lr_unit.institution_id``). Without it the endpoint returns an empty
        body, which is treated as "no detail available" (``None``).

        Args:
            file_number: Rendered file number, e.g. ``"Z-12564/2026"``.
            institution_id: Owning land-registry office ID (e.g. 284 for Zadar).

        Returns:
            A :class:`FileStatus`, or ``None`` when the number cannot be parsed
            or the endpoint has no record for it.

        Raises:
            CadastralAPIError: A transport/server error occurred.

        Note:
            ⚠️ Demo project: verify your rights before using any server other than the mock.
        """
        parts = parse_file_number(file_number)
        if parts is None:
            return None
        code, order_number, year = parts

        response_data = self._make_post_request(
            "/lr/file-status",
            {
                "lrFileCode": code,
                "lrFileOrderNumber": order_number,
                "lrFileYear": year,
                "institutionId": institution_id,
            },
        )

        # The endpoint answers an unknown file with an empty object, not a 404.
        if not response_data:
            return None

        return self._parse(
            FileStatus, response_data, "/lr/file-status", {"file_number": file_number}
        )

    def get_plombe_details(
        self, lr_unit: LandRegistryUnitDetailed
    ) -> dict[str, FileStatus]:
        """Resolve detail for each pending plomba on a land-registry unit.

        Iterates the unit's ``active_plumbs`` and fetches each one's status,
        using the unit's own ``institution_id``. Cadastre plombe
        (``cad_plumb=True``) are skipped - ``/lr/file-status`` is a
        land-registry endpoint and does not resolve them. Plombe with no
        retrievable record are likewise omitted.

        Each extra plomba costs one rate-limited request, so this is opt-in at
        the call sites (CLI ``--plombe-detail`` / MCP ``include_plombe_detail``).

        Args:
            lr_unit: The unit whose pending plombe should be detailed.

        Returns:
            Mapping of ``file_number`` -> :class:`FileStatus` for the
            land-registry plombe that resolved. Consumers iterate
            ``lr_unit.active_plumbs`` and look up by ``file_number`` so that
            skipped/unresolved plombe remain visible as "detail unavailable".
        """
        details: dict[str, FileStatus] = {}
        for plumb in lr_unit.active_plumbs:
            if plumb.cad_plumb:
                continue
            status = self.get_file_status(plumb.file_number, lr_unit.institution_id)
            if status is not None:
                details[plumb.file_number] = status
        return details


def _unknown_field_paths(instance: BaseModel, prefix: str) -> set[str]:
    """Key paths (``endpoint.field.subfield[].key``) of every undeclared server key."""
    paths: set[str] = set()
    extra = getattr(instance, "source_fields", None)
    if extra is None:
        extra = dict(instance.model_extra or {})
    for key in extra:
        paths.add(f"{prefix}.{key}")
    for name in type(instance).model_fields:
        value = getattr(instance, name, None)
        if isinstance(value, BaseModel):
            paths |= _unknown_field_paths(value, f"{prefix}.{name}")
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, BaseModel):
                    paths |= _unknown_field_paths(item, f"{prefix}.{name}[]")
    return paths
