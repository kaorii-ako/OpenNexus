# Contributing to OpenNexus

## Adding a Connector

1. Create `backend/connectors/<name>.py`
2. Subclass `ConnectorBase`:

```python
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig

class MyConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig): ...
    async def connect(self) -> None: ...
    async def health(self) -> HealthResult: ...
    async def fetch_data(self) -> dict: ...
```

3. Register in `backend/core/config.py` → `ConnectorsConfig`
4. Add to `nexus connect` in `cli/main.py`
5. Add to `backend/agents/digest.py` if it contributes to the morning briefing
6. Add a row to the Connectors table in `README.md`

## Dev Setup

```bash
git clone https://github.com/<you>/opennexus
cd opennexus
uv sync
cp nexus.toml.example nexus.toml
# edit nexus.toml
uv run nexus serve
```

## Tests

```bash
uv run pytest tests/ -v
```

## Frontend

```bash
cd frontend
npm install
npm run dev   # dev server on :5173 (proxies API to :8000)
```
