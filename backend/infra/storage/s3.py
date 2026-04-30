from __future__ import annotations
import aiobotocore.session


class S3Storage:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
    ) -> None:
        self._endpoint = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket = bucket
        self._session = aiobotocore.session.get_session()

    def _client(self):
        return self._session.create_client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
        )

    async def _put_object(self, key: str, data: bytes) -> None:
        async with self._client() as client:
            await client.put_object(Bucket=self._bucket, Key=key, Body=data)

    async def _get_object(self, key: str) -> bytes:
        async with self._client() as client:
            resp = await client.get_object(Bucket=self._bucket, Key=key)
            return await resp["Body"].read()

    async def upload(self, key: str, data: bytes) -> str:
        await self._put_object(key, data)
        return f"s3://{self._bucket}/{key}"

    async def download(self, key: str) -> bytes:
        return await self._get_object(key)
