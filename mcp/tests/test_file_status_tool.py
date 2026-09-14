"""get_file_status resolves one file number at one office, and says when there is none."""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api import CadastralAPIError, ErrorType  # noqa: E402
from cadastral_api.models.entities import FileStatus  # noqa: E402

from cadastral_mcp.tools import CadastralTools  # noqa: E402

FIXTURE = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures" / "file_status_pending.json"


def _tools(status):
    client = MagicMock()
    if isinstance(status, Exception):
        client.get_file_status.side_effect = status
    else:
        client.get_file_status.return_value = status
    return CadastralTools(client), client


def test_found_file_carries_its_record() -> None:
    status = FileStatus.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))
    tools, client = _tools(status)
    result = asyncio.run(tools.get_file_status("Z-12564/2026", "284"))
    assert result["found"] is True
    assert result["institution_id"] == 284
    assert result["status"]["application_content"] == status.application_content
    assert result["status"]["status_description"] == status.status_description
    client.get_file_status.assert_called_once_with("Z-12564/2026", 284)


def test_unknown_file_is_not_an_error() -> None:
    tools, _ = _tools(None)
    result = asyncio.run(tools.get_file_status("Z-1/2026", 284))
    assert result["found"] is False
    assert "Z-1/2026" in result["message"]
    assert "status" not in result


def test_transport_error_is_reported() -> None:
    tools, _ = _tools(CadastralAPIError(ErrorType.SERVER_ERROR, details={}))
    with pytest.raises(ValueError) as excinfo:
        asyncio.run(tools.get_file_status("Z-12564/2026", 284))
    assert "Z-12564/2026" in str(excinfo.value)
