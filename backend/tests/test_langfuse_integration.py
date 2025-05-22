import os
import sys
import importlib
from pathlib import Path
from types import ModuleType, SimpleNamespace

# Ensure the backend folder is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def import_langfuse_module(public=None, secret=None, host=None, available=True):
    """Helper to import langfuse_integration with patched config and logger."""
    # Create dummy utils.config module
    config_module = ModuleType("utils.config")
    config_module.config = SimpleNamespace(
        LANGFUSE_PUBLIC_KEY=public,
        LANGFUSE_SECRET_KEY=secret,
        LANGFUSE_HOST=host,
    )

    # Create dummy utils.logger module
    logger_module = ModuleType("utils.logger")

    class DummyLogger:
        def info(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            pass

        def debug(self, *args, **kwargs):
            pass

    logger_module.logger = DummyLogger()

    sys.modules["utils.config"] = config_module
    sys.modules["utils.logger"] = logger_module

    if "services.langfuse_integration" in sys.modules:
        del sys.modules["services.langfuse_integration"]

    module = importlib.import_module("services.langfuse_integration")
    module.LANGFUSE_AVAILABLE = available
    return module, config_module.config


def test_setup_langfuse_success(monkeypatch):
    module, config = import_langfuse_module(
        public="pk_test",
        secret="sk_test",
        host="https://example.com",
    )

    for var in ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"]:
        os.environ.pop(var, None)

    result = module.setup_langfuse()

    assert result is True
    assert os.environ.get("LANGFUSE_PUBLIC_KEY") == "pk_test"
    assert os.environ.get("LANGFUSE_SECRET_KEY") == "sk_test"
    assert os.environ.get("LANGFUSE_HOST") == "https://example.com"


def test_setup_langfuse_missing_keys(monkeypatch):
    module, config = import_langfuse_module(
        public=None,
        secret=None,
        host="https://example.com",
    )

    for var in ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"]:
        os.environ.pop(var, None)

    result = module.setup_langfuse()

    assert result is False
    assert "LANGFUSE_PUBLIC_KEY" not in os.environ
    assert "LANGFUSE_SECRET_KEY" not in os.environ


def test_setup_langfuse_package_missing(monkeypatch):
    module, config = import_langfuse_module(
        public="pk_test",
        secret="sk_test",
        host=None,
        available=False,
    )

    for var in ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"]:
        os.environ.pop(var, None)

    result = module.setup_langfuse()

    assert result is False
    assert "LANGFUSE_PUBLIC_KEY" not in os.environ
    assert "LANGFUSE_SECRET_KEY" not in os.environ
    assert "LANGFUSE_HOST" not in os.environ
