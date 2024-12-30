"""Tests for file and path name sanitization functionality."""

from pathlib import Path
from typing import Optional

import pytest

from omym.core.sanitizer import Sanitizer


class TestSanitizer:
    """Test cases for Sanitizer."""

    def test_empty_string(self) -> None:
        """Test sanitization of empty string."""
        assert Sanitizer.sanitize_string("") == ""
        assert Sanitizer.sanitize_string(None) == ""

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            (None, "Unknown-Title"),  # None
            ("", "Unknown-Title"),  # Empty string
            (" ", "Unknown-Title"),  # Only space
            (".", "Unknown-Title"),  # Only dot
            ("   ", "Unknown-Title"),  # Multiple spaces
            ("---", "Unknown-Title"),  # Multiple hyphens
            ("@#$%^&*()", "Unknown-Title"),  # Only special characters
            ("♪♫♬", "Unknown-Title"),  # Only music symbols
            ("★☆○●", "Unknown-Title"),  # Only geometric shapes
        ],
    )
    def test_track_name_empty(self, input_str: Optional[str], expected: str) -> None:
        """Test handling of empty track names.

        Args:
            input_str: Input string to test
            expected: Expected output string
        """
        assert Sanitizer.sanitize_track_name(input_str) == expected
        assert Sanitizer.sanitize_title(input_str) == expected

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("Don't Stop Believin'", "Dont-Stop-Believin"),
            ("Rock'n'Roll", "RocknRoll"),
            ("'Round Midnight", "Round-Midnight"),
        ],
    )
    def test_apostrophe_removal(self, input_str: str, expected: str) -> None:
        """Test removal of apostrophes.

        Args:
            input_str: Input string to test
            expected: Expected output string
        """
        assert Sanitizer.sanitize_string(input_str) == expected

    @pytest.mark.parametrize(
        "input_str,expected",
        [
            ("Hello, World!", "Hello-World"),  # Punctuation between words
            ("Rock & Roll", "Rock-Roll"),  # Ampersand between words
            ("AC/DC", "AC-DC"),  # Slash between letters
            ("$100%", "100"),  # Currency and percent with number
            ("@#$%^&*()", ""),  # Only special characters
            ("♪♫♬", ""),  # Only music symbols
        ],
    )
    def test_special_character_replacement(self, input_str: str, expected: str) -> None:
        """Test replacement of special characters with hyphens.

        Args:
            input_str: Input string to test
            expected: Expected output string
        """
        assert Sanitizer.sanitize_string(input_str) == expected

    def test_multiple_hyphen_compression(self):
        """Test compression of multiple consecutive hyphens."""
        test_cases = [
            ("Hello---World", "Hello-World"),
            ("Rock----&----Roll", "Rock-Roll"),
            ("--Multiple--Hyphens--", "Multiple-Hyphens"),
        ]
        for input_str, expected in test_cases:
            assert Sanitizer.sanitize_string(input_str) == expected

    def test_start_end_hyphen_removal(self):
        """Test removal of hyphens at start and end."""
        test_cases = [
            ("-Hello-", "Hello"),
            ("--Start-End--", "Start-End"),
            ("-Multiple-Hyphens-", "Multiple-Hyphens"),
        ]
        for input_str, expected in test_cases:
            assert Sanitizer.sanitize_string(input_str) == expected

    def test_length_truncation(self):
        """Test string truncation to maximum length."""
        long_string = "a" * 100
        assert len(Sanitizer.sanitize_string(long_string, max_length=10).encode("utf-8")) <= 10

    def test_artist_name_length(self):
        """Test artist name length limitation."""
        long_artist = "Very" * 20 + " Long Artist Name"
        sanitized = Sanitizer.sanitize_artist_name(long_artist)
        assert len(sanitized.encode("utf-8")) <= Sanitizer.MAX_ARTIST_LENGTH

    def test_album_name_length(self):
        """Test album name length limitation."""
        long_album = "Very" * 30 + " Long Album Name"
        sanitized = Sanitizer.sanitize_album_name(long_album)
        assert len(sanitized.encode("utf-8")) <= Sanitizer.MAX_ALBUM_LENGTH

    def test_track_name_length(self):
        """Test track name length limitation."""
        long_track = "Very" * 30 + " Long Track Name"
        sanitized = Sanitizer.sanitize_track_name(long_track)
        assert len(sanitized.encode("utf-8")) <= Sanitizer.MAX_TRACK_LENGTH

    def test_path_sanitization(self):
        """Test path sanitization."""
        # Test relative path
        path = Path("Artist's Name/Album (2023)/01. Track!.mp3")
        expected = Path("Artists-Name/Album-2023/01-Track.mp3")
        assert Sanitizer.sanitize_path(path) == expected

        # Test absolute path
        if Path.cwd().drive:  # Windows
            path = Path("C:/Music/Artist's Name/Album (2023)/01. Track!.mp3")
            expected = Path("C:/Music/Artists-Name/Album-2023/01-Track.mp3")
        else:  # Unix-like
            path = Path("/music/Artist's Name/Album (2023)/01. Track!.mp3")
            expected = Path("/music/Artists-Name/Album-2023/01-Track.mp3")
        assert Sanitizer.sanitize_path(path) == expected

    def test_unicode_handling(self):
        """Test handling of Unicode characters."""
        test_cases = [
            ("こんにちは", "こんにちは"),  # Japanese
            ("안녕하세요", "안녕하세요"),  # Korean
            ("你好", "你好"),  # Chinese
            ("Café", "Café"),  # Latin-1
            ("über", "über"),  # German
        ]
        for input_str, expected in test_cases:
            assert Sanitizer.sanitize_string(input_str) == expected

    def test_edge_cases(self):
        """Test edge cases."""
        test_cases = [
            (" ", ""),  # Only space
            ("-", ""),  # Only hyphen
            (".", ""),  # Only dot
            ("---", ""),  # Only hyphens
            ("   ", ""),  # Multiple spaces
            ("...", ""),  # Multiple dots
        ]
        for input_str, expected in test_cases:
            assert Sanitizer.sanitize_string(input_str) == expected

    def test_space_handling(self):
        """Test handling of various space characters."""
        test_cases = [
            ("Hello World", "Hello-World"),  # Regular space
            ("Hello　World", "Hello-World"),  # Full-width space
            ("Hello\tWorld", "Hello-World"),  # Tab
            ("Hello\nWorld", "Hello-World"),  # Newline
            ("Hello\rWorld", "Hello-World"),  # Carriage return
            ("Hello\u00a0World", "Hello-World"),  # Non-breaking space
            ("Hello\u2003World", "Hello-World"),  # Em space
        ]
        for input_str, expected in test_cases:
            assert Sanitizer.sanitize_string(input_str) == expected

    def test_symbol_handling(self):
        """Test handling of various symbols."""
        test_cases = [
            # Basic punctuation
            ("Hello,World", "Hello-World"),
            ("Hello.World", "Hello-World"),
            ("Hello:World", "Hello-World"),
            ("Hello;World", "Hello-World"),
            ("Hello!World", "Hello-World"),
            ("Hello?World", "Hello-World"),
            # Brackets and parentheses
            ("(Hello)World", "Hello-World"),
            ("[Hello]World", "Hello-World"),
            ("{Hello}World", "Hello-World"),
            ("「Hello」World", "Hello-World"),
            ("『Hello』World", "Hello-World"),
            # Mathematical symbols
            ("Hello+World", "Hello-World"),
            ("Hello=World", "Hello-World"),
            ("Hello<World", "Hello-World"),
            ("Hello>World", "Hello-World"),
            # Currency and other symbols
            ("Hello$World", "Hello-World"),
            ("Hello¥World", "Hello-World"),
            ("Hello€World", "Hello-World"),
            ("Hello£World", "Hello-World"),
            ("Hello%World", "Hello-World"),
            ("Hello&World", "Hello-World"),
            ("Hello#World", "Hello-World"),
            ("Hello@World", "Hello-World"),
        ]
        for input_str, expected in test_cases:
            assert Sanitizer.sanitize_string(input_str) == expected

    def test_nfkc_normalization(self):
        """Test NFKC normalization."""
        test_cases = [
            ("ｶﾌｪ", "カフェ"),  # Half-width to full-width
            ("①②③", "123"),  # Special numbers to ASCII
            ("㌔", "キロ"),  # Units to normal text
            ("™", "TM"),  # Only trademark symbols
            ("ﾊﾟｽﾜｰﾄﾞ", "パスワード"),  # Half-width kana to full-width
            # Combined characters
            ("é", "é"),  # e + acute = single é
            ("が", "が"),  # か + dakuten = が
        ]
        for input_str, expected in test_cases:
            assert Sanitizer.sanitize_string(input_str) == expected
