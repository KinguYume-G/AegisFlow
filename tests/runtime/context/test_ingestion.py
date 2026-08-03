from uuid import uuid4
import pytest

from aegisflow_core.runtime.context.embedder import DeterministicHashEmbedder
from aegisflow_core.runtime.context.ingestion import ingest_file


class Store:
    def __init__(self): self.rows = {}
    async def list_file(self, tenant_id, repository, file_path):
        return [v for (t,r,p,_),v in self.rows.items() if (t,r,p)==(tenant_id,repository,file_path)]
    async def add(self, chunk): self.rows[(chunk.tenant_id,chunk.repository,chunk.file_path,chunk.chunk_index)] = chunk
    async def remove_indexes(self, tenant_id, repository, file_path, indexes):
        for index in indexes: self.rows.pop((tenant_id,repository,file_path,index), None)
        return len(indexes)


@pytest.mark.asyncio
async def test_ingestion_is_idempotent_and_quarantines_secrets() -> None:
    store, tenant = Store(), uuid4()
    kwargs = dict(store=store, tenant_id=tenant, repository="o/r", file_path="a.py", embedder=DeterministicHashEmbedder())
    first = await ingest_file(raw_text="safe content\n", **kwargs)
    second = await ingest_file(raw_text="safe content\n", **kwargs)
    secret = await ingest_file(raw_text="API_KEY=sk-secretsecretsecret\n", **kwargs)
    assert (first.changed, second.skipped) == (1, 1)
    assert secret.security_skipped == 1
    assert not store.rows
