# cadastral_api: Python SDK

Rate-limited HTTP client, Pydantic V2 models, and GIS helpers for the cadastral
and land registry API. The CLI and the MCP server are built on this package.

```bash
pip install -e ./api
```

```python
from cadastral_api import CadastralAPIClient

with CadastralAPIClient() as client:
    unit = client.get_lr_unit_from_parcel("103/2", "SAVAR")
    print(unit.summary())
```

Documentation: [docs/sdk-guide.md](../docs/sdk-guide.md). Examples: [examples/](examples/).

Runs against the included mock server only; see [docs/legal.md](../docs/legal.md).
