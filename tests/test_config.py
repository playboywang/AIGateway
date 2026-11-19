from config.settings import load_settings


def test_env_file_values_override_defaults(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "AIGATEWAY_PORT=9123\n"
        "AIGATEWAY_DB_ECHO=true\n"
        "AIGATEWAY_DEFAULT_GROUP_TYPE=api\n",
        encoding="utf-8",
    )

    settings = load_settings(env_file)

    assert settings.app_port == 9123
    assert settings.db_echo is True
    assert settings.default_group_type == "API"
    assert settings.app_host == "0.0.0.0"


def test_present_empty_env_key_overrides_default(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("AIGATEWAY_DATABASE_URL=\n", encoding="utf-8")

    settings = load_settings(env_file)

    assert settings.database_url == ""
