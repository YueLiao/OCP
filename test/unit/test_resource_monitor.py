import pytest

import tools.resource_monitor as resource_monitor


def test_platform_info_suppresses_psutil_runtime_errors(monkeypatch):
    monkeypatch.setattr(resource_monitor, "HAS_PSUTIL", True)
    monkeypatch.setattr(resource_monitor.psutil, "cpu_count", lambda logical=False: 4)

    class BrokenVirtualMemory:
        @property
        def total(self):
            raise RuntimeError("psutil failed")

    monkeypatch.setattr(resource_monitor.psutil, "virtual_memory", lambda: BrokenVirtualMemory())

    info = resource_monitor.get_platform_info()

    assert info["cpu_count_physical"] == 4
    assert info["ram_total_gb"] is None


def test_platform_info_does_not_suppress_unexpected_errors(monkeypatch):
    monkeypatch.setattr(resource_monitor, "HAS_PSUTIL", True)

    def broken_cpu_count(logical=False):
        raise TypeError("programming error")

    monkeypatch.setattr(resource_monitor.psutil, "cpu_count", broken_cpu_count)

    with pytest.raises(TypeError, match="programming error"):
        resource_monitor.get_platform_info()
