from tracker import config


def test_get_settings_reads_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")
    monkeypatch.setenv("STEAM_API_KEY", "test-key")
    config.get_settings.cache_clear()
    settings = config.get_settings()
    assert settings.database_url == "postgresql+psycopg://u:p@h:5432/d"


def test_get_settings_reads_steam_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")
    monkeypatch.setenv("STEAM_API_KEY", "test-key-123")
    config.get_settings.cache_clear()
    settings = config.get_settings()
    assert settings.steam_api_key == "test-key-123"
    assert settings.bayesian_prior_strength == 50.0
    assert settings.min_cohort_size == 20
