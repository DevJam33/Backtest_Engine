"""
Tests pour la configuration
"""

import pytest
from survivorship_bias_free_data.config import DataConfig, ScraperConfig

class TestConfig:
    """Tests de configuration"""

    def test_data_config_defaults(self):
        """Test valeurs par défaut de DataConfig"""
        config = DataConfig()
        assert config.SP500_START_YEAR == 1957
        assert config.NASDAQ_START_YEAR == 1971
        assert config.STORAGE_FORMAT == "parquet"
        assert config.CHUNK_SIZE == 100
        assert config.REQUEST_DELAY > 0

    def test_scraper_config_defaults(self):
        """Test valeurs par défaut de ScraperConfig"""
        config = ScraperConfig()
        assert "User-Agent" in config.USER_AGENT
        assert config.REQUEST_TIMEOUT > 0
        assert config.MAX_RETRIES >= 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
