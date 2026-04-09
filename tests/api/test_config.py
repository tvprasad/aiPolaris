"""
tests/api/test_config.py — Unit tests for Settings defaults and get_settings cache.
"""

from api.config import Settings, get_settings


class TestSettingsDefaults:
    def test_model_temperature_default(self) -> None:
        # temperature=0.0 is a hard code constraint (ADR-007) — never env-overridden
        s = Settings()
        assert s.model_temperature == 0.0

    def test_max_tokens_default(self) -> None:
        s = Settings()
        assert s.max_tokens == 1000

    def test_confidence_threshold_default(self) -> None:
        s = Settings()
        assert s.confidence_threshold == 0.60

    def test_settings_fields_are_correct_types(self) -> None:
        s = Settings()
        assert isinstance(s.environment, str)
        assert isinstance(s.openai_endpoint, str)
        assert isinstance(s.auth_enabled, bool)
        assert isinstance(s.max_tokens, int)
        assert isinstance(s.model_temperature, float)

    def test_settings_has_all_required_fields(self) -> None:
        s = Settings()
        # Verify all fields that nodes and middleware depend on are present
        assert hasattr(s, "openai_endpoint")
        assert hasattr(s, "search_endpoint")
        assert hasattr(s, "openai_deployment")
        assert hasattr(s, "confidence_threshold")
        assert hasattr(s, "auth_enabled")
        assert hasattr(s, "tenant_id")


class TestGetSettings:
    def test_returns_settings_instance(self) -> None:
        s = get_settings()
        assert isinstance(s, Settings)

    def test_returns_cached_instance(self) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
