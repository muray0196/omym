"""Tests for metadata extraction helper utilities.

Where: tests/features/metadata/test_track_metadata_helpers.py
What: Validate helper functions used by the track metadata extractor.
Why: Pin current behaviour ahead of planned refactors that will relocate these helpers.
"""

from omym.features.metadata.usecases.extraction._tag_utils import (
    parse_slash_separated,
    parse_tuple_numbers,
    parse_year,
)


def test_parse_slash_separated_extracts_numbers() -> None:
    """Ensure basic slash-delimited numbers are parsed correctly."""
    assert parse_slash_separated("3/12") == (3, 12)


def test_parse_slash_separated_handles_invalid_values() -> None:
    """Non-numeric segments should yield None values."""
    assert parse_slash_separated("a/b") == (None, None)
    assert parse_slash_separated("") == (None, None)


def test_parse_tuple_numbers_converts_zeros_to_none() -> None:
    """Tuple values of zero should be normalised to None."""
    assert parse_tuple_numbers([(0, 10)]) == (None, 10)
    assert parse_tuple_numbers([(4, 0)]) == (4, None)


def test_parse_tuple_numbers_handles_missing_data() -> None:
    """Absent tuples should return a pair of None values."""
    assert parse_tuple_numbers(None) == (None, None)
    assert parse_tuple_numbers([]) == (None, None)


def test_parse_year_reads_leading_digits() -> None:
    """The helper should extract the leading four-digit year when present."""
    assert parse_year("2023-04-01") == 2023
    assert parse_year("1999") == 1999


def test_parse_year_returns_none_for_invalid_input() -> None:
    """Short or non-numeric prefixes should return None."""
    assert parse_year("abc") is None
    assert parse_year("12") is None
