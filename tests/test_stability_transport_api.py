"""Exercise legacy client imports and guard against incidental API expansion."""
import importlib
import types

import pytest
import ncmemsim
import ncmemsim.transport as transport


@pytest.mark.parametrize("name", ["NodeKind", "TransportNode", "TunnelLink", "TunnelNetwork",
    "LinkTransportResult", "TransportStepResult", "TransportConfig", "TransportEngine"])
def test_legacy_type_import_identity(name):
    namespace = {}
    exec("from ncmemsim.transport import " + name, namespace)
    assert namespace[name] is getattr(ncmemsim, name)


def test_legacy_wildcard_and_submodule_imports():
    namespace = {}
    exec("from ncmemsim.transport import *", namespace)
    for name in ("base", "link", "network", "rates", "engine"):
        assert isinstance(namespace[name], types.ModuleType)
        assert namespace[name] is importlib.import_module("ncmemsim.transport." + name)
    assert namespace["TransportEngine"] is ncmemsim.TransportEngine


def test_future_helper_does_not_extend_wildcard_surface(monkeypatch):
    monkeypatch.setattr(transport, "future_helper", object(), raising=False)
    importlib.reload(transport)
    namespace = {}
    exec("from ncmemsim.transport import *", namespace)
    assert "future_helper" not in namespace
