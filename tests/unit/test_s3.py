import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.infra.storage.s3 import S3Storage


@pytest.mark.asyncio
async def test_upload_returns_s3_uri():
    storage = S3Storage(
        endpoint="http://localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket="fastrag",
    )
    with patch.object(storage, "_put_object", new_callable=AsyncMock) as mock_put:
        mock_put.return_value = None
        uri = await storage.upload("docs/file.pdf", b"content")
    assert uri == "s3://fastrag/docs/file.pdf"


@pytest.mark.asyncio
async def test_download_returns_bytes():
    storage = S3Storage(
        endpoint="http://localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket="fastrag",
    )
    with patch.object(storage, "_get_object", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = b"file content"
        data = await storage.download("docs/file.pdf")
    assert data == b"file content"
