"""HTTP client for Croatian Cadastral API with rate limiting and error handling.

⚠️ DEMO/EDUCATIONAL PROJECT ONLY ⚠️

This client demonstrates how a cadastral API integration could work.
It is configured to use a MOCK SERVER by default for safe testing and learning.

CRITICAL RESTRICTIONS:
- DO NOT configure this client to use Croatian government production systems
- Production use is NOT AUTHORIZED due to terms of service and sensitive data
- This is a theoretical demonstration of API design patterns only
- Use only with the included mock server for educational purposes

The author is available to advise the Croatian government on official AI and API
implementation if requested.

See README.md and CLAUDE.md for complete disclaimer.
"""

import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

from ..exceptions import CadastralAPIError, ErrorType
from ..gis import GISCache, GMLParser
from ..models import CadastralOffice, MunicipalitySearchResult, ParcelInfo, ParcelSearchResult
from ..models.gis_entities import ParcelGeometry

# Load environment variables from .env file
load_dotenv()


class CadastralAPIClient:
    """
    Client for Croatian Cadastral System API (Uređena zemlja).

    Provides methods to search for parcels and retrieve detailed information
    with automatic rate limiting and retry logic.
    """

    # Default to localhost test server (production API requires authorization)
    BASE_URL = os.getenv("CADASTRAL_API_BASE_URL", "http://localhost:8000")
    DEFAULT_TIMEOUT = float(os.getenv("CADASTRAL_API_TIMEOUT", "10.0"))
    DEFAULT_RATE_LIMIT = float(os.getenv("CADASTRAL_API_RATE_LIMIT", "0.75"))
    MAX_RETRIES = 3

    def __init__(
        self,
        base_url: str | None = None,
        rate_limit: float | None = None,
        timeout: float | None = None,
        cache_dir: Path | str | None = None,
    ) -> None:
        """
        Initialize the API client.

        Args:
            base_url: API base URL (default: from CADASTRAL_API_BASE_URL env or http://localhost:8000)
            rate_limit: Minimum seconds between requests (default: from CADASTRAL_API_RATE_LIMIT env or 0.75)
            timeout: Request timeout in seconds (default: from CADASTRAL_API_TIMEOUT env or 10.0)
            cache_dir: Directory for GIS data cache (default: ~/.cadastral_api_cache)

        Environment Variables:
            CADASTRAL_API_BASE_URL: API base URL (default: http://localhost:8000)
            CADASTRAL_API_RATE_LIMIT: Rate limit in seconds (default: 0.75)
            CADASTRAL_API_TIMEOUT: Request timeout in seconds (default: 10.0)

        Note:
            The production API (https://oss.uredjenazemlja.hr/oss/public) is protected
            and may require authorization. Use a local test server for development.
        """
        self.base_url = base_url or self.BASE_URL
        self.rate_limit = rate_limit if rate_limit is not None else self.DEFAULT_RATE_LIMIT
        self.timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
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
        self.gis_cache = GISCache(cache_dir)

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

        try:
            return [CadastralOffice.model_validate(item) for item in response_data]
        except ValidationError as e:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint, "reason": "validation_failed"},
                cause=e,
            ) from e

    def search_municipality(
        self,
        search_term: str | None = None,
        office_id: str | None = None,
        department_id: str | None = None,
    ) -> list[MunicipalitySearchResult]:
        """
        Search for municipalities by name, code, or filter by cadastral office/department.

        Args:
            search_term: Municipality name (e.g., "SAVAR") or code (e.g., "334979")
            office_id: Filter by cadastral office ID (e.g., "114" for Zadar)
            department_id: Filter by department ID (e.g., "116")

        Returns:
            List of MunicipalitySearchResult objects

        Raises:
            CadastralAPIError: Any API error occurred

        Examples:
            # Search by name
            municipalities = client.search_municipality("SAVAR")

            # Filter by office (162 municipalities in Zadar office)
            municipalities = client.search_municipality(office_id="114")

            # Filter by office and department (66 municipalities)
            municipalities = client.search_municipality(office_id="114", department_id="116")

            # Combine search with filters
            municipalities = client.search_municipality("SAVAR", office_id="114")

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

        try:
            return [MunicipalitySearchResult.model_validate(item) for item in response_data]
        except ValidationError as e:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint, "reason": "validation_failed"},
                cause=e,
            ) from e

    def search_parcel(
        self, parcel_number: str, municipality_reg_num: str
    ) -> list[ParcelSearchResult]:
        """
        Search for parcel IDs by parcel number and municipality.

        Args:
            parcel_number: Parcel number (e.g., "103/2", "114")
            municipality_reg_num: Municipality registration number (e.g., "334979")

        Returns:
            List of ParcelSearchResult objects

        Raises:
            CadastralAPIError: Any API error occurred

        Note:
            Partial searches return multiple results (e.g., "114" returns 114, 1140/1, etc.)
        """
        endpoint = "/search-cad-parcels/parcel-numbers"
        params = {
            "search": str(parcel_number),
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

        try:
            return [ParcelSearchResult.model_validate(item) for item in response_data]
        except ValidationError as e:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint, "reason": "validation_failed"},
                cause=e,
            ) from e

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
                details={"endpoint": endpoint, "parcel_id": str(parcel_id), "reason": "empty_response"},
            )

        try:
            return ParcelInfo.model_validate(response_data)
        except ValidationError as e:
            raise CadastralAPIError(
                error_type=ErrorType.INVALID_RESPONSE,
                details={"endpoint": endpoint, "parcel_id": str(parcel_id), "reason": "validation_failed"},
                cause=e,
            ) from e

    def get_parcel_by_number(
        self, parcel_number: str, municipality_reg_num: str, exact_match: bool = True
    ) -> ParcelInfo | None:
        """
        Convenience method to search and retrieve parcel info in one call.

        Args:
            parcel_number: Parcel number (e.g., "103/2")
            municipality_reg_num: Municipality registration number
            exact_match: If True, only return exact parcel number match

        Returns:
            ParcelInfo object if found, None otherwise

        Raises:
            CadastralAPIError: Any API error occurred
        """
        search_results = self.search_parcel(parcel_number, municipality_reg_num)

        if not search_results:
            return None

        # Find exact match if requested
        if exact_match:
            for result in search_results:
                if result.parcel_number == parcel_number:
                    return self.get_parcel_info(result.parcel_id)
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
