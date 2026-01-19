"""Tests for batch input parsers."""

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from cadastral_cli.input_parsers import (
    ParcelInput,
    parse_cli_list,
    parse_csv_file,
    parse_input_file,
    parse_json_file,
)


class TestParcelInput:
    """Tests for ParcelInput class."""

    def test_parcel_number_input(self):
        """Test creating ParcelInput with parcel number."""
        parcel = ParcelInput(parcel_number="103/2", municipality="334979")
        assert parcel.parcel_number == "103/2"
        assert parcel.municipality == "334979"
        assert not parcel.is_direct_id

    def test_parcel_id_input(self):
        """Test creating ParcelInput with parcel ID."""
        parcel = ParcelInput(parcel_id="12345678")
        assert parcel.parcel_id == "12345678"
        assert parcel.is_direct_id

    def test_both_raises_error(self):
        """Test that providing both parcel_number and parcel_id raises error."""
        with pytest.raises(ValueError, match="Cannot specify both"):
            ParcelInput(parcel_number="103/2", parcel_id="12345678", municipality="334979")

    def test_neither_raises_error(self):
        """Test that providing neither raises error."""
        with pytest.raises(ValueError, match="Must specify either"):
            ParcelInput()

    def test_parcel_number_without_municipality_raises_error(self):
        """Test that parcel_number without municipality raises error."""
        with pytest.raises(ValueError, match="Municipality required"):
            ParcelInput(parcel_number="103/2")


class TestParseCliList:
    """Tests for CLI list parser."""

    def test_parse_parcel_numbers(self):
        """Test parsing comma-separated parcel numbers."""
        parcels = parse_cli_list("103/2,45,396/1", "SAVAR")
        assert len(parcels) == 3
        assert parcels[0].parcel_number == "103/2"
        assert parcels[1].parcel_number == "45"
        assert parcels[2].parcel_number == "396/1"
        assert all(p.municipality == "SAVAR" for p in parcels)

    def test_parse_parcel_ids(self):
        """Test parsing comma-separated parcel IDs (all numeric)."""
        parcels = parse_cli_list("12345678,87654321", "ignored")
        assert len(parcels) == 2
        assert parcels[0].parcel_id == "12345678"
        assert parcels[1].parcel_id == "87654321"
        assert all(p.is_direct_id for p in parcels)

    def test_parse_with_spaces(self):
        """Test parsing with spaces around items."""
        parcels = parse_cli_list("103/2 , 45 , 396/1", "SAVAR")
        assert len(parcels) == 3
        assert parcels[0].parcel_number == "103/2"

    def test_empty_list_raises_error(self):
        """Test that empty list raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_cli_list("", "SAVAR")

    def test_no_municipality_raises_error(self):
        """Test that missing municipality raises error."""
        with pytest.raises(ValueError, match="Municipality required"):
            parse_cli_list("103/2,45", "")

    def test_mixed_input_raises_error(self):
        """Test that mixing parcel numbers and IDs raises error."""
        with pytest.raises(ValueError, match="Cannot mix"):
            parse_cli_list("103/2,12345678", "SAVAR")


class TestParseCsvFile:
    """Tests for CSV file parser."""

    def test_parse_parcel_numbers(self):
        """Test parsing CSV with parcel numbers and municipalities."""
        csv_content = "parcel_number,municipality\n103/2,334979\n45,SAVAR\n396/1,334979\n"

        with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                parcels = parse_csv_file(f.name)
                assert len(parcels) == 3
                assert parcels[0].parcel_number == "103/2"
                assert parcels[0].municipality == "334979"
                assert parcels[1].parcel_number == "45"
                assert parcels[1].municipality == "SAVAR"
            finally:
                Path(f.name).unlink()

    def test_parse_with_municipality_inheritance(self):
        """Test municipality inheritance in CSV."""
        csv_content = "parcel_number,municipality\n103/2,334979\n45,\n396/1,\n52,334731\n10,\n"

        with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                parcels = parse_csv_file(f.name)
                assert len(parcels) == 5
                assert parcels[0].municipality == "334979"
                assert parcels[1].municipality == "334979"  # Inherited
                assert parcels[2].municipality == "334979"  # Inherited
                assert parcels[3].municipality == "334731"
                assert parcels[4].municipality == "334731"  # Inherited
            finally:
                Path(f.name).unlink()

    def test_parse_parcel_ids(self):
        """Test parsing CSV with parcel IDs."""
        csv_content = "parcel_id\n12345678\n87654321\n"

        with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                parcels = parse_csv_file(f.name)
                assert len(parcels) == 2
                assert parcels[0].parcel_id == "12345678"
                assert parcels[1].parcel_id == "87654321"
            finally:
                Path(f.name).unlink()

    def test_empty_municipality_without_previous_raises_error(self):
        """Test that empty municipality without previous value raises error."""
        csv_content = "parcel_number,municipality\n103/2,\n"

        with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                with pytest.raises(ValueError, match="municipality required"):
                    parse_csv_file(f.name)
            finally:
                Path(f.name).unlink()

    def test_mixed_columns_raises_error(self):
        """Test that having both parcel_number and parcel_id columns raises error."""
        csv_content = "parcel_number,parcel_id,municipality\n103/2,12345678,334979\n"

        with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                with pytest.raises(ValueError, match="Cannot have both"):
                    parse_csv_file(f.name)
            finally:
                Path(f.name).unlink()

    def test_missing_required_column_raises_error(self):
        """Test that missing required columns raises error."""
        csv_content = "other_column\n103/2\n"

        with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                with pytest.raises(ValueError, match="must have either"):
                    parse_csv_file(f.name)
            finally:
                Path(f.name).unlink()

    def test_file_not_found(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_csv_file("/nonexistent/file.csv")


class TestParseJsonFile:
    """Tests for JSON file parser."""

    def test_parse_parcel_numbers(self):
        """Test parsing JSON with parcel numbers."""
        json_content = [
            {"parcel_number": "103/2", "municipality": "334979"},
            {"parcel_number": "45", "municipality": "SAVAR"},
        ]

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_content, f)
            f.flush()

            try:
                parcels = parse_json_file(f.name)
                assert len(parcels) == 2
                assert parcels[0].parcel_number == "103/2"
                assert parcels[0].municipality == "334979"
                assert parcels[1].parcel_number == "45"
                assert parcels[1].municipality == "SAVAR"
            finally:
                Path(f.name).unlink()

    def test_parse_parcel_ids(self):
        """Test parsing JSON with parcel IDs."""
        json_content = [{"parcel_id": "12345678"}, {"parcel_id": "87654321"}]

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_content, f)
            f.flush()

            try:
                parcels = parse_json_file(f.name)
                assert len(parcels) == 2
                assert parcels[0].parcel_id == "12345678"
                assert parcels[1].parcel_id == "87654321"
            finally:
                Path(f.name).unlink()

    def test_mixed_input_raises_error(self):
        """Test that mixing parcel numbers and IDs raises error."""
        json_content = [
            {"parcel_number": "103/2", "municipality": "334979"},
            {"parcel_id": "12345678"},
        ]

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_content, f)
            f.flush()

            try:
                with pytest.raises(ValueError, match="Cannot mix"):
                    parse_json_file(f.name)
            finally:
                Path(f.name).unlink()

    def test_not_array_raises_error(self):
        """Test that non-array JSON raises error."""
        json_content = {"parcel_number": "103/2", "municipality": "334979"}

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_content, f)
            f.flush()

            try:
                with pytest.raises(ValueError, match="must be an array"):
                    parse_json_file(f.name)
            finally:
                Path(f.name).unlink()

    def test_empty_array_raises_error(self):
        """Test that empty array raises error."""
        json_content = []

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_content, f)
            f.flush()

            try:
                with pytest.raises(ValueError, match="array is empty"):
                    parse_json_file(f.name)
            finally:
                Path(f.name).unlink()

    def test_missing_municipality_raises_error(self):
        """Test that parcel_number without municipality raises error."""
        json_content = [{"parcel_number": "103/2"}]

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_content, f)
            f.flush()

            try:
                with pytest.raises(ValueError, match="municipality required"):
                    parse_json_file(f.name)
            finally:
                Path(f.name).unlink()


class TestParseInputFile:
    """Tests for auto-detect file parser."""

    def test_parse_csv(self):
        """Test auto-detecting CSV files."""
        csv_content = "parcel_id\n12345678\n"

        with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            try:
                parcels = parse_input_file(f.name)
                assert len(parcels) == 1
                assert parcels[0].parcel_id == "12345678"
            finally:
                Path(f.name).unlink()

    def test_parse_json(self):
        """Test auto-detecting JSON files."""
        json_content = [{"parcel_id": "12345678"}]

        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_content, f)
            f.flush()

            try:
                parcels = parse_input_file(f.name)
                assert len(parcels) == 1
                assert parcels[0].parcel_id == "12345678"
            finally:
                Path(f.name).unlink()

    def test_unsupported_format_raises_error(self):
        """Test that unsupported file format raises error."""
        with NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("some content")
            f.flush()

            try:
                with pytest.raises(ValueError, match="Unsupported file format"):
                    parse_input_file(f.name)
            finally:
                Path(f.name).unlink()
