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


# ------------------------------ RuntimeResourceMonitor.get_runtime_usage ------------------------------
def test_runtime_usage_disabled_record_when_no_samples(monkeypatch):
    monkeypatch.setattr(resource_monitor, "HAS_PSUTIL", True)
    usage = resource_monitor.RuntimeResourceMonitor().get_runtime_usage()  # sample_count == 0
    assert usage["monitoring_enabled"] is False
    assert usage["avg_cpu_percent"] is None
    assert usage["max_num_threads"] is None
    assert usage["max_added_threads"] is None


def test_runtime_usage_aggregates_samples_and_reports_added_threads(monkeypatch):
    monkeypatch.setattr(resource_monitor, "HAS_PSUTIL", True)
    mon = resource_monitor.RuntimeResourceMonitor()
    mon.sample_count = 2
    mon.cpu_percent_sum = 150.0
    mon.max_cpu_percent = 90.0
    mon.max_num_threads = 10
    mon.baseline_num_threads = 6

    usage = mon.get_runtime_usage()

    assert usage["monitoring_enabled"] is True
    assert usage["avg_cpu_percent"] == 75.0             # 150 / 2
    assert usage["max_cpu_percent"] == 90.0
    assert usage["avg_used_cores_estimated"] == 0.75    # 75 / 100
    assert usage["max_used_cores_estimated"] == 0.9     # 90 / 100
    assert usage["max_num_threads"] == 10
    assert usage["baseline_num_threads"] == 6
    assert usage["max_added_threads"] == 4              # max(0, 10 - 6): workload-added threads


def test_runtime_usage_added_threads_clamped_to_zero(monkeypatch):
    monkeypatch.setattr(resource_monitor, "HAS_PSUTIL", True)
    mon = resource_monitor.RuntimeResourceMonitor()
    mon.sample_count = 1
    mon.cpu_percent_sum = 50.0
    mon.max_cpu_percent = 50.0
    mon.max_num_threads = 5
    mon.baseline_num_threads = 8  # baseline higher than the observed peak

    assert mon.get_runtime_usage()["max_added_threads"] == 0  # max(0, 5 - 8)


def test_get_stats_bundles_platform_info_and_runtime_usage(monkeypatch):
    monkeypatch.setattr(resource_monitor, "HAS_PSUTIL", True)
    stats = resource_monitor.RuntimeResourceMonitor().get_stats()
    assert set(stats) == {"platform_info", "runtime_usage"}
    assert stats["runtime_usage"]["monitoring_enabled"] is False  # nothing sampled
    assert "platform_system" in stats["platform_info"]


def test_platform_info_degrades_without_psutil(monkeypatch):
    monkeypatch.setattr(resource_monitor, "HAS_PSUTIL", False)
    info = resource_monitor.get_platform_info()
    assert info["cpu_count_physical"] is None
    assert info["ram_total_gb"] is None
    assert info["platform_system"]  # static platform fields are still populated


def test_runtime_usage_disabled_without_psutil(monkeypatch):
    monkeypatch.setattr(resource_monitor, "HAS_PSUTIL", False)
    mon = resource_monitor.RuntimeResourceMonitor()
    mon.sample_count = 5  # even with samples recorded, missing psutil forces the disabled record
    usage = mon.get_runtime_usage()
    assert usage["monitoring_enabled"] is False
    assert usage["max_added_threads"] is None
