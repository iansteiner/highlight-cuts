import pytest
from highlight_cuts.utils import parse_time


def test_parse_time_hh_mm_ss():
    assert parse_time("01:01:01") == 3661.0
    assert parse_time("1:00:00") == 3600.0


def test_parse_time_mm_ss():
    assert parse_time("01:01") == 61.0
    assert parse_time("10:30") == 630.0


def test_parse_time_invalid():
    with pytest.raises(ValueError):
        parse_time("invalid")
    with pytest.raises(ValueError):
        parse_time("01:01:01:01")


def test_parse_time_floats():
    assert parse_time("00:00:01.5") == 1.5
