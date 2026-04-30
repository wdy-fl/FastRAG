from __future__ import annotations
import asyncio
from backend.core.models.ingestion import ParserSettings


class UnstructuredParser:
    async def parse(
        self, content: bytes, filename: str, config: ParserSettings
    ) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, _parse_sync, content, filename
        )


def _parse_sync(content: bytes, filename: str) -> str:
    from unstructured.partition.auto import partition
    import tempfile, os
    suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".bin"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        elements = partition(filename=tmp_path)
        return "\n\n".join(str(el) for el in elements)
    finally:
        os.unlink(tmp_path)
