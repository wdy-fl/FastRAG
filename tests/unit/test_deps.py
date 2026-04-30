def test_deps_importable():
    from fastrag.api import deps  # noqa: F401
    assert True


def test_get_settings_returns_settings():
    from fastrag.api.deps import get_settings
    from fastrag.config.settings import Settings
    s = get_settings()
    assert isinstance(s, Settings)
