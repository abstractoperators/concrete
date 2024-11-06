import asyncio
import sys

import pytest

from concrete.orchestrator import SoftwareOrchestrator


class TestDependencies:
    def test_concrete_db_not_installed(self, monkeypatch):
        async def wrapper(so: SoftwareOrchestrator):
            async for _ in so.process_new_project("Create a hello world program"):
                continue
            return True

        monkeypatch.setitem(sys.modules, "concrete_db", None)

        assert asyncio.run(wrapper(SoftwareOrchestrator()))
        with pytest.raises(ImportError):
            asyncio.run(wrapper(SoftwareOrchestrator(store_messages=True)))
