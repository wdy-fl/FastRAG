def test_deps_importable():
    from backend.api import deps  # noqa: F401
    assert True


def test_get_settings_returns_settings():
    from backend.api.deps import get_settings
    from backend.config.settings import Settings
    s = get_settings()
    assert isinstance(s, Settings)
