"""Tests for batch processor."""

from unittest.mock import MagicMock, Mock

import pytest

from cadastral_cli.batch_processor import (
    BatchResult,
    BatchSummary,
    process_batch,
)
from cadastral_cli.input_parsers import ParcelInput
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.models.entities import ParcelInfo


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    return MagicMock()


@pytest.fixture
def mock_parcel_info():
    """Create a mock ParcelInfo object."""
    parcel = Mock(spec=ParcelInfo)
    parcel.parcel_id = "12345678"
    parcel.parcel_number = "103/2"
    parcel.municipality_reg_num = "334979"
    parcel.municipality_name = "SAVAR"
    parcel.area_numeric = 5000
    parcel.has_building_right = True
    parcel.total_owners = 2
    parcel.possession_sheets = []
    parcel.land_use_summary = {}
    parcel.address = "Test Address"
    # LR unit reference (may be None if not available)
    parcel.lr_unit = None
    return parcel


class TestBatchResult:
    """Tests for BatchResult class."""

    def test_success_result_to_dict(self, mock_parcel_info):
        """Test converting successful result to dict."""
        input_spec = ParcelInput(parcel_number="103/2", municipality="SAVAR")
        result = BatchResult(
            status="success",
            input=input_spec,
            parcel_data=mock_parcel_info,
        )

        data = result.to_dict()
        assert data["status"] == "success"
        assert data["parcel_number"] == "103/2"
        assert data["municipality"] == "SAVAR"
        assert data["parcel_id"] == "12345678"
        assert data["area_m2"] == 5000
        assert data["building_permitted"] is True
        assert data["total_owners"] == 2

    def test_error_result_to_dict(self):
        """Test converting error result to dict."""
        input_spec = ParcelInput(parcel_number="103/2", municipality="SAVAR")
        result = BatchResult(
            status="error",
            input=input_spec,
            error_type=ErrorType.PARCEL_NOT_FOUND.value,
            error_message="Parcel not found",
        )

        data = result.to_dict()
        assert data["status"] == "error"
        assert data["parcel_number"] == "103/2"
        assert data["municipality"] == "SAVAR"
        assert data["error_type"] == ErrorType.PARCEL_NOT_FOUND.value
        assert data["error_message"] == "Parcel not found"

    def test_parcel_id_input_to_dict(self):
        """Test converting result with parcel ID input to dict."""
        input_spec = ParcelInput(parcel_id="12345678")
        result = BatchResult(
            status="error",
            input=input_spec,
            error_type="test_error",
            error_message="Test message",
        )

        data = result.to_dict()
        assert data["parcel_id"] == "12345678"
        assert "parcel_number" not in data


class TestBatchSummary:
    """Tests for BatchSummary class."""

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        summary = BatchSummary(total=10, successful=7, failed=3, results=[])
        assert summary.success_rate == 70.0

    def test_success_rate_zero_total(self):
        """Test success rate with zero total."""
        summary = BatchSummary(total=0, successful=0, failed=0, results=[])
        assert summary.success_rate == 0.0

    def test_to_dict(self, mock_parcel_info):
        """Test converting summary to dict."""
        input_spec = ParcelInput(parcel_number="103/2", municipality="SAVAR")
        result = BatchResult(
            status="success",
            input=input_spec,
            parcel_data=mock_parcel_info,
        )
        summary = BatchSummary(total=1, successful=1, failed=0, results=[result])

        data = summary.to_dict()
        assert data["summary"]["total"] == 1
        assert data["summary"]["successful"] == 1
        assert data["summary"]["failed"] == 0
        assert data["summary"]["success_rate"] == "100.0%"
        assert len(data["results"]) == 1


class TestProcessBatch:
    """Tests for process_batch function."""

    def test_process_parcel_numbers_success(self, mock_client, mock_parcel_info):
        """Test processing parcel numbers successfully."""
        # Setup mock
        mock_client.find_municipality.return_value = [
            Mock(name="SAVAR", municipality_reg_num="334979")
        ]
        mock_client.get_parcel_by_number.return_value = mock_parcel_info

        # Create input
        parcels = [
            ParcelInput(parcel_number="103/2", municipality="SAVAR"),
            ParcelInput(parcel_number="45", municipality="SAVAR"),
        ]

        # Process
        summary = process_batch(mock_client, parcels, show_progress=False)

        # Verify
        assert summary.total == 2
        assert summary.successful == 2
        assert summary.failed == 0
        assert len(summary.results) == 2
        assert all(r.status == "success" for r in summary.results)

    def test_process_parcel_ids_success(self, mock_client, mock_parcel_info):
        """Test processing parcel IDs successfully."""
        # Setup mock
        mock_client.get_parcel_info.return_value = mock_parcel_info

        # Create input
        parcels = [
            ParcelInput(parcel_id="12345678"),
            ParcelInput(parcel_id="87654321"),
        ]

        # Process
        summary = process_batch(mock_client, parcels, show_progress=False)

        # Verify
        assert summary.total == 2
        assert summary.successful == 2
        assert summary.failed == 0
        assert mock_client.get_parcel_info.call_count == 2

    def test_process_with_parcel_not_found(self, mock_client):
        """Test processing when parcel is not found."""
        # Setup mock to return None
        mock_client.find_municipality.return_value = [
            Mock(name="SAVAR", municipality_reg_num="334979")
        ]
        mock_client.get_parcel_by_number.return_value = None

        # Create input
        parcels = [ParcelInput(parcel_number="103/2", municipality="SAVAR")]

        # Process
        summary = process_batch(mock_client, parcels, show_progress=False)

        # Verify
        assert summary.total == 1
        assert summary.successful == 0
        assert summary.failed == 1
        assert summary.results[0].status == "error"
        assert summary.results[0].error_type == ErrorType.PARCEL_NOT_FOUND.value

    def test_process_with_api_error_continue(self, mock_client, mock_parcel_info):
        """Test processing with API error and continue_on_error=True."""
        # Setup mock to raise error on first call, succeed on second
        mock_client.find_municipality.return_value = [
            Mock(name="SAVAR", municipality_reg_num="334979")
        ]
        mock_client.get_parcel_by_number.side_effect = [
            CadastralAPIError(ErrorType.PARCEL_NOT_FOUND),
            mock_parcel_info,
        ]

        # Create input
        parcels = [
            ParcelInput(parcel_number="103/2", municipality="SAVAR"),
            ParcelInput(parcel_number="45", municipality="SAVAR"),
        ]

        # Process
        summary = process_batch(mock_client, parcels, continue_on_error=True, show_progress=False)

        # Verify
        assert summary.total == 2
        assert summary.successful == 1
        assert summary.failed == 1
        assert summary.results[0].status == "error"
        assert summary.results[1].status == "success"

    def test_process_with_api_error_stop(self, mock_client):
        """Test processing with API error and continue_on_error=False."""
        # Setup mock to raise error
        mock_client.find_municipality.return_value = [
            Mock(name="SAVAR", municipality_reg_num="334979")
        ]
        mock_client.get_parcel_by_number.side_effect = CadastralAPIError(
            ErrorType.PARCEL_NOT_FOUND
        )

        # Create input
        parcels = [
            ParcelInput(parcel_number="103/2", municipality="SAVAR"),
            ParcelInput(parcel_number="45", municipality="SAVAR"),
        ]

        # Process - should raise
        with pytest.raises(CadastralAPIError):
            process_batch(mock_client, parcels, continue_on_error=False, show_progress=False)

    def test_process_with_unexpected_error_continue(self, mock_client, mock_parcel_info):
        """Test processing with unexpected error and continue_on_error=True."""
        # Setup mock to raise unexpected error on first call
        mock_client.find_municipality.return_value = [
            Mock(name="SAVAR", municipality_reg_num="334979")
        ]
        mock_client.get_parcel_by_number.side_effect = [
            RuntimeError("Unexpected error"),
            mock_parcel_info,
        ]

        # Create input
        parcels = [
            ParcelInput(parcel_number="103/2", municipality="SAVAR"),
            ParcelInput(parcel_number="45", municipality="SAVAR"),
        ]

        # Process
        summary = process_batch(mock_client, parcels, continue_on_error=True, show_progress=False)

        # Verify
        assert summary.total == 2
        assert summary.successful == 1
        assert summary.failed == 1
        assert summary.results[0].status == "error"
        assert summary.results[0].error_type == "unexpected_error"
        assert summary.results[1].status == "success"

    def test_process_municipality_resolution(self, mock_client, mock_parcel_info):
        """Test that municipality names are resolved to codes."""
        # Setup mock
        municipality_result = Mock()
        municipality_result.municipality_name = "SAVAR"
        municipality_result.municipality_reg_num = "334979"
        mock_client.find_municipality.return_value = [municipality_result]
        mock_client.get_parcel_by_number.return_value = mock_parcel_info

        # Create input with municipality name
        parcels = [ParcelInput(parcel_number="103/2", municipality="SAVAR")]

        # Process
        summary = process_batch(mock_client, parcels, show_progress=False)

        # Verify municipality was resolved
        mock_client.find_municipality.assert_called_once_with(search_term="SAVAR")
        mock_client.get_parcel_by_number.assert_called_once_with("103/2", "334979", exact_match=True)
        assert summary.successful == 1

    def test_process_municipality_not_found(self, mock_client):
        """Test handling when municipality is not found."""
        # Setup mock to return no results
        mock_client.find_municipality.return_value = []

        # Create input
        parcels = [ParcelInput(parcel_number="103/2", municipality="UNKNOWN")]

        # Process
        summary = process_batch(mock_client, parcels, continue_on_error=True, show_progress=False)

        # Verify
        assert summary.failed == 1
        assert summary.results[0].error_type == ErrorType.MUNICIPALITY_NOT_FOUND.value

    def test_process_empty_batch(self, mock_client):
        """Test processing empty batch."""
        summary = process_batch(mock_client, [], show_progress=False)

        assert summary.total == 0
        assert summary.successful == 0
        assert summary.failed == 0
        assert len(summary.results) == 0
