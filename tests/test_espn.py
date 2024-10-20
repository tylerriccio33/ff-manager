import tempfile
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from ff_manager.league import ESPNLeague


@pytest.mark.real
def test_espn_data_load():
    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)
        profile = {
            "espn_s2": "AEBb24SVMtY7mZpzKKdGRq8Yuf0KAYAliYvA8wCTRfeXQx1opGjlVNFJ3%2BlvuGL5LOyj%2BDGc%2FDZYhEuqkdzdEuXH6vsPO6bgMTNwSX5anuwQrKujopxHeep7pGfYgwbmYXj0gPpIRyrnMaxnLYx0CgmZyyivD5nDPDpX73p8R%2BpqZ9ty%2Bbd2X2KuBVG2CzUcCvOxujl2ujpsM8Jg8jdh67e5Wh1N3ofMNVveqyDN4nB%2Bv3hI0ADZcDeoyhCC6nEv%2B4p43Y7x2Gp%2F0txVn5uC7hioxOSO19aBRhtKMeCUoazrOA%3D%3D",
            "swid": "29AD20CC-EE06-4148-9C56-ED6C11F067CD",
            "year": 2024,
            "id": 56618929,
            "lineup": {},
        }
        ESPNLeague(profile=profile, data_loc=tmp / "out.parquet", refresh_data=True)

        assert (tmp / "out.parquet").exists()
        data = pq.read_table(tmp / "out.parquet")
        assert data


if __name__ == "__main__":
    test_espn_data_load()
