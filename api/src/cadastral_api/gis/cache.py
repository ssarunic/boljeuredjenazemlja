"""GIS data cache manager for municipality ZIP files."""

import zipfile
from pathlib import Path

import httpx


class GISCache:
    """
    Manages local caching of municipality GIS ZIP files.

    Downloads and caches ZIP files containing GML data for municipalities.
    Automatically extracts files when needed.
    """

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        """
        Initialize GIS cache.

        Args:
            cache_dir: Directory for caching files. Defaults to ~/.cadastral_api_cache
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cadastral_api_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_municipality_dir(self, municipality_reg_num: str) -> Path:
        """
        Get cache directory for a specific municipality.

        Args:
            municipality_reg_num: Municipality registration number

        Returns:
            Path to municipality cache directory
        """
        muni_dir = self.cache_dir / f"ko-{municipality_reg_num}"
        muni_dir.mkdir(exist_ok=True)
        return muni_dir

    def get_zip_path(self, municipality_reg_num: str) -> Path:
        """
        Get path to cached ZIP file.

        Args:
            municipality_reg_num: Municipality registration number

        Returns:
            Path to ZIP file
        """
        muni_dir = self.get_municipality_dir(municipality_reg_num)
        return muni_dir / f"ko-{municipality_reg_num}.zip"

    def get_gml_path(self, municipality_reg_num: str, filename: str) -> Path:
        """
        Get path to extracted GML file.

        Args:
            municipality_reg_num: Municipality registration number
            filename: GML filename (e.g., "katastarske_cestice.gml")

        Returns:
            Path to GML file
        """
        muni_dir = self.get_municipality_dir(municipality_reg_num)
        return muni_dir / filename

    def is_cached(self, municipality_reg_num: str) -> bool:
        """
        Check if municipality data is already cached.

        Args:
            municipality_reg_num: Municipality registration number

        Returns:
            True if ZIP file exists in cache
        """
        zip_path = self.get_zip_path(municipality_reg_num)
        return zip_path.exists()

    def download_municipality(
        self, municipality_reg_num: str, force: bool = False
    ) -> Path:
        """
        Download municipality GIS data ZIP file.

        Args:
            municipality_reg_num: Municipality registration number
            force: Force re-download even if cached

        Returns:
            Path to downloaded ZIP file

        Raises:
            httpx.HTTPError: Download failed
        """
        zip_path = self.get_zip_path(municipality_reg_num)

        if zip_path.exists() and not force:
            return zip_path

        # Download from ATOM feed
        url = f"https://oss.uredjenazemlja.hr/oss/public/atom/ko-{municipality_reg_num}.zip"

        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

            zip_path.write_bytes(response.content)

        return zip_path

    def extract_gml(self, municipality_reg_num: str, filename: str) -> Path:
        """
        Extract specific GML file from ZIP.

        Args:
            municipality_reg_num: Municipality registration number
            filename: GML filename to extract (e.g., "katastarske_cestice.gml")

        Returns:
            Path to extracted GML file

        Raises:
            FileNotFoundError: ZIP file not in cache
            KeyError: GML file not found in ZIP
        """
        zip_path = self.get_zip_path(municipality_reg_num)

        if not zip_path.exists():
            raise FileNotFoundError(
                f"ZIP file not cached for municipality {municipality_reg_num}. "
                "Call download_municipality() first."
            )

        gml_path = self.get_gml_path(municipality_reg_num, filename)

        # Extract if not already extracted
        if not gml_path.exists():
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extract(filename, self.get_municipality_dir(municipality_reg_num))

        return gml_path

    def get_parcel_data(self, municipality_reg_num: str, auto_download: bool = True) -> Path:
        """
        Get path to cadastral parcels GML file.

        Args:
            municipality_reg_num: Municipality registration number
            auto_download: Automatically download if not cached

        Returns:
            Path to katastarske_cestice.gml file

        Raises:
            FileNotFoundError: Not cached and auto_download=False
        """
        if auto_download and not self.is_cached(municipality_reg_num):
            self.download_municipality(municipality_reg_num)

        return self.extract_gml(municipality_reg_num, "katastarske_cestice.gml")

    def clear_municipality(self, municipality_reg_num: str) -> None:
        """
        Clear cached data for a municipality.

        Args:
            municipality_reg_num: Municipality registration number
        """
        import shutil

        muni_dir = self.get_municipality_dir(municipality_reg_num)
        if muni_dir.exists():
            shutil.rmtree(muni_dir)

    def clear_all(self) -> None:
        """Clear entire cache directory."""
        import shutil

        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
