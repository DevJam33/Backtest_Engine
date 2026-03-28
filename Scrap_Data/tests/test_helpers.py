"""
Tests pour les fonctions utilitaires
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import shutil

from survivorship_bias_free_data.utils.helpers import (
    ensure_dir,
    save_json,
    load_json,
    save_pickle,
    load_pickle,
    save_dataframe,
    load_dataframe,
    normalize_ticker,
    date_to_str
)

class TestHelpers:
    """Tests des fonctions helpers"""

    def test_ensure_dir_creates_directory(self, tmp_path):
        """Test que ensure_dir crée le répertoire"""
        test_dir = tmp_path / "new_dir" / "nested"
        result = ensure_dir(test_dir)
        assert result.exists()
        assert result.is_dir()

    def test_normalize_ticker(self):
        """Test de normalisation des tickers"""
        assert normalize_ticker("aapl") == "AAPL"
        assert normalize_ticker("brk.a") == "BRK-A"  # Yahoo format
        assert normalize_ticker("  msft  ") == "MSFT"
        assert normalize_ticker("RDS-A") == "RDS-A"
        # Ne pas modifier les tickers canadiens avec .TO
        assert normalize_ticker("BNS.TO") == "BNS.TO"

    def test_date_to_str(self):
        """Test de conversion date -> string"""
        from datetime import datetime
        dt = datetime(2023, 1, 15)
        assert date_to_str(dt) == "2023-01-15"
        assert date_to_str(None) is None

    def test_save_load_json(self, tmp_path):
        """Test cycle save/load JSON"""
        data = {"test": "value", "number": 42, "list": [1, 2, 3]}
        filepath = tmp_path / "test.json"
        save_json(data, filepath)
        loaded = load_json(filepath)
        assert loaded == data

    def test_save_load_dataframe(self, tmp_path):
        """Test cycle save/load DataFrame"""
        df = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z'],
            'Date': pd.date_range('2023-01-01', periods=3)
        })
        # Parquet
        filepath = tmp_path / "test.parquet"
        save_dataframe(df, filepath)
        loaded = load_dataframe(filepath)
        pd.testing.assert_frame_equal(df, loaded)

        # CSV
        csv_path = tmp_path / "test.csv"
        save_dataframe(df, csv_path, format='csv')
        loaded_csv = load_dataframe(csv_path, format='csv')
        pd.testing.assert_frame_equal(df, loaded_csv)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
