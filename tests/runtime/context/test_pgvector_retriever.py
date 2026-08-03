from datetime import datetime, timezone
from uuid import uuid4

from aegisflow_core.control_plane.domain.knowledge import RepositoryChunk
from aegisflow_core.packs.delivery.contracts.normalized_request import NormalizedRequest
from aegisflow_core.runtime.context.pgvector_retriever import PgVectorContextRetriever, RepositoryTarget


def test_retriever_injects_trusted_scope_and_maps_exact_citations() -> None:
    tenant = uuid4(); calls = []
    row = RepositoryChunk(tenant_id=tenant,repository="o/r",file_path="src/a.py",chunk_index=0,
                          content_hash="a"*64,content="line\n",start_line=4,end_line=4,embedding=[0.0]*32)
    def query(tenant_id, repository, text, limit):
        calls.append((tenant_id, repository, limit)); return [row]
    request = NormalizedRequest(source_type="github_issue",source_ref="untrusted/other",title="find",body="details",idempotency_key="a"*64,received_at=datetime.now(timezone.utc))
    package = PgVectorContextRetriever(tenant_id=tenant,target=RepositoryTarget("o","r"),query=query).retrieve(request)
    assert calls == [(tenant,"o/r",5)]
    assert package.snippets[0].relative_path == "src/a.py" and package.snippets[0].start_line == 4


def test_retriever_reports_missing_evidence() -> None:
    tenant = uuid4()
    request = NormalizedRequest(source_type="prd",source_ref=None,title="find",body="details",idempotency_key="b"*64,received_at=datetime.now(timezone.utc))
    package = PgVectorContextRetriever(tenant_id=tenant,target=RepositoryTarget("o","r"),query=lambda *args: []).retrieve(request)
    assert package.unsupported_notes
