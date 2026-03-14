"""Tests for World Bank configuration loader."""

from pipelines.config import (
    get_country_config,
    get_enabled_countries,
    get_enabled_indicators,
    get_indicator_config,
    get_setting,
    load_world_bank_config,
)


class TestLoadWorldBankConfig:
    """Test loading the YAML configuration file."""

    def test_load_config_returns_dict(self):
        """Config should load successfully and return a dict."""
        config = load_world_bank_config()
        assert isinstance(config, dict)

    def test_config_has_required_keys(self):
        """Config should have all required top-level keys."""
        config = load_world_bank_config()
        assert "countries" in config
        assert "indicators" in config
        assert "settings" in config

    def test_countries_is_list(self):
        """Countries should be a list."""
        config = load_world_bank_config()
        assert isinstance(config["countries"], list)
        assert len(config["countries"]) > 0

    def test_indicators_is_dict(self):
        """Indicators should be a dict with category keys."""
        config = load_world_bank_config()
        assert isinstance(config["indicators"], dict)
        assert "economic" in config["indicators"]
        assert "unemployment" in config["indicators"]
        assert "inflation" in config["indicators"]
        assert "climate" in config["indicators"]

    def test_settings_is_dict(self):
        """Settings should be a dict."""
        config = load_world_bank_config()
        assert isinstance(config["settings"], dict)
        assert "date_range_start" in config["settings"]
        assert "date_range_end" in config["settings"]


class TestGetEnabledCountries:
    """Test getting enabled countries."""

    def test_returns_list_of_tuples(self):
        """Should return list of (code, name) tuples."""
        countries = get_enabled_countries()
        assert isinstance(countries, list)
        assert len(countries) > 0

        # Check first country structure
        assert isinstance(countries[0], tuple)
        assert len(countries[0]) == 2
        assert isinstance(countries[0][0], str)  # code
        assert isinstance(countries[0][1], str)  # name

    def test_only_enabled_countries(self):
        """Should only return countries with enabled=true."""
        countries = get_enabled_countries()
        config = load_world_bank_config()

        enabled_codes = [c[0] for c in countries]

        # Verify all enabled countries are present
        for country in config["countries"]:
            if country.get("enabled", False):
                assert country["code"] in enabled_codes

    def test_expected_countries_present(self):
        """Should include expected countries from config."""
        countries = get_enabled_countries()
        country_codes = [c[0] for c in countries]

        # Check some known countries that should be enabled
        expected = ["US", "CN", "JP", "DE", "GB"]
        for code in expected:
            assert code in country_codes


class TestGetEnabledIndicators:
    """Test getting enabled indicators."""

    def test_returns_dict(self):
        """Should return dict mapping name -> code."""
        indicators = get_enabled_indicators()
        assert isinstance(indicators, dict)
        assert len(indicators) > 0

    def test_only_enabled_indicators(self):
        """Should only return indicators with enabled=true."""
        indicators = get_enabled_indicators()
        config = load_world_bank_config()

        # Collect all enabled indicator names from config
        enabled_names = []
        for _category, indicator_list in config["indicators"].items():
            for ind in indicator_list:
                if ind.get("enabled", False):
                    enabled_names.append(ind["name"])

        # Verify they match
        assert set(indicators.keys()) == set(enabled_names)

    def test_expected_indicators_present(self):
        """Should include expected enabled indicators."""
        indicators = get_enabled_indicators()

        # Based on our config, these should be enabled
        expected = [
            "gdp",
            "gdp_per_capita",
            "unemployment_rate",
            "inflation_cpi",
            "co2_per_capita",
        ]
        for name in expected:
            assert name in indicators

    def test_indicator_codes_are_strings(self):
        """Indicator codes should be World Bank API codes."""
        indicators = get_enabled_indicators()

        for _name, code in indicators.items():
            assert isinstance(code, str)
            assert len(code) > 0


class TestGetIndicatorConfig:
    """Test getting full indicator configuration."""

    def test_get_existing_indicator(self):
        """Should return config for existing indicator."""
        config = get_indicator_config("gdp")
        assert config is not None
        assert config["name"] == "gdp"
        assert config["code"] == "NY.GDP.MKTP.CD"

    def test_get_nonexistent_indicator(self):
        """Should return None for non-existent indicator."""
        config = get_indicator_config("does_not_exist")
        assert config is None

    def test_indicator_has_required_fields(self):
        """Indicator config should have all required fields."""
        config = get_indicator_config("gdp")
        assert "code" in config
        assert "name" in config
        assert "display_name" in config
        assert "description" in config
        assert "unit" in config
        assert "enabled" in config


class TestGetCountryConfig:
    """Test getting full country configuration."""

    def test_get_existing_country(self):
        """Should return config for existing country."""
        config = get_country_config("US")
        assert config is not None
        assert config["code"] == "US"
        assert config["name"] == "United States"

    def test_get_nonexistent_country(self):
        """Should return None for non-existent country."""
        config = get_country_config("ZZ")
        assert config is None

    def test_country_has_required_fields(self):
        """Country config should have all required fields."""
        config = get_country_config("US")
        assert "code" in config
        assert "name" in config
        assert "region" in config
        assert "enabled" in config


class TestGetSetting:
    """Test cascading setting resolution."""

    def test_global_default(self):
        """Should return global default when no overrides."""
        setting = get_setting("date_range_start")
        assert setting == 1960  # Global default

    def test_country_override(self):
        """Should return country override when present."""
        country = get_country_config("EUU")  # EU has date_range_start: 1993
        setting = get_setting("date_range_start", country_config=country)
        assert setting == 1993  # Country override

    def test_indicator_override(self):
        """Should return indicator override when present."""
        indicator = get_indicator_config(
            "unemployment_rate"
        )  # Has date_range_start: 1991
        setting = get_setting("date_range_start", indicator_config=indicator)
        assert setting == 1991  # Indicator override

    def test_indicator_overrides_country(self):
        """Indicator override should take precedence over country."""
        country = get_country_config("EUU")  # date_range_start: 1993
        indicator = get_indicator_config("unemployment_rate")  # date_range_start: 1991
        setting = get_setting("date_range_start", country, indicator)
        assert setting == 1991  # Indicator wins

    def test_allow_negative_values_default(self):
        """Default for allow_negative_values should be False."""
        setting = get_setting("allow_negative_values")
        assert not setting

    def test_allow_negative_values_override(self):
        """Indicators with negative values should override to True."""
        indicator = get_indicator_config("inflation_cpi")  # Can have deflation
        setting = get_setting("allow_negative_values", indicator_config=indicator)
        assert setting  # Indicator override


class TestConfigDataIntegrity:
    """Test data integrity and consistency in configuration."""

    def test_all_enabled_countries_have_required_fields(self):
        """All enabled countries should have required fields."""
        countries = get_enabled_countries()
        for code, name in countries:
            assert code is not None
            assert name is not None
            assert len(code) >= 2
            assert len(name) > 0

    def test_all_enabled_indicators_have_required_fields(self):
        """All enabled indicators should have required fields."""
        indicators = get_enabled_indicators()
        for name, code in indicators.items():
            assert name is not None
            assert code is not None
            assert len(name) > 0
            assert len(code) > 0

            # Get full config and verify
            config = get_indicator_config(name)
            assert config["display_name"]
            assert config["description"]
            assert config["unit"]

    def test_no_duplicate_country_codes(self):
        """Country codes should be unique."""
        config = load_world_bank_config()
        codes = [c["code"] for c in config["countries"]]
        assert len(codes) == len(set(codes))

    def test_no_duplicate_indicator_names(self):
        """Indicator names should be unique across all categories."""
        config = load_world_bank_config()
        names = []
        for _category, indicators in config["indicators"].items():
            for ind in indicators:
                names.append(ind["name"])
        assert len(names) == len(set(names))
