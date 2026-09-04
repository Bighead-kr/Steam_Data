from tracker import config


def test_get_settings_reads_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/d")
    config.get_settings.cache_clear()
    settings = config.get_settings()
    assert settings.database_url == "postgresql+psycopg://u:p@h:5432/d"
