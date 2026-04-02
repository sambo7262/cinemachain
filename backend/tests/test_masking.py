"""
Tests for backend/app/utils/masking.py
All behavior cases from 18-01-PLAN.md Task 1.
"""
import pytest


# ---------------------------------------------------------------------------
# mask_key
# ---------------------------------------------------------------------------

def test_mask_key_none():
    from app.utils.masking import mask_key
    assert mask_key(None) is None


def test_mask_key_empty():
    from app.utils.masking import mask_key
    assert mask_key("") == "***"


def test_mask_key_short_less_than_4():
    from app.utils.masking import mask_key
    assert mask_key("abc") == "***"


def test_mask_key_exactly_4_chars():
    from app.utils.masking import mask_key
    assert mask_key("abcd") == "***bcd"


def test_mask_key_long_value():
    from app.utils.masking import mask_key
    assert mask_key("my_secret_key_xyz") == "***xyz"


# ---------------------------------------------------------------------------
# is_masked_sentinel
# ---------------------------------------------------------------------------

def test_is_masked_sentinel_none():
    from app.utils.masking import is_masked_sentinel
    assert is_masked_sentinel(None) is False


def test_is_masked_sentinel_empty():
    from app.utils.masking import is_masked_sentinel
    assert is_masked_sentinel("") is False


def test_is_masked_sentinel_valid_6_chars():
    from app.utils.masking import is_masked_sentinel
    assert is_masked_sentinel("***abc") is True


def test_is_masked_sentinel_valid_3_chars():
    from app.utils.masking import is_masked_sentinel
    assert is_masked_sentinel("***") is True


def test_is_masked_sentinel_real_key():
    from app.utils.masking import is_masked_sentinel
    assert is_masked_sentinel("real_api_key_value_32chars") is False


def test_is_masked_sentinel_too_long_11_chars():
    from app.utils.masking import is_masked_sentinel
    assert is_masked_sentinel("***abcdefgh") is False  # 11 chars > 10


def test_is_masked_sentinel_exactly_10_chars():
    from app.utils.masking import is_masked_sentinel
    assert is_masked_sentinel("***1234567") is True  # exactly 10 chars


# ---------------------------------------------------------------------------
# scrub_text
# ---------------------------------------------------------------------------

def test_scrub_text_replaces_secret():
    from app.utils.masking import scrub_text
    result = scrub_text("url?api_key=abc123", ["abc123"])
    assert result == "url?api_key=[REDACTED]"


def test_scrub_text_skips_short_secrets():
    from app.utils.masking import scrub_text
    # Secrets shorter than 4 chars should not be substituted
    result = scrub_text("url?api_key=ab", ["ab"])
    assert result == "url?api_key=ab"


def test_scrub_text_skips_exactly_3_chars():
    from app.utils.masking import scrub_text
    result = scrub_text("test abc text", ["abc"])
    assert result == "test abc text"


def test_scrub_text_multiple_secrets():
    from app.utils.masking import scrub_text
    result = scrub_text("key1=secret1 key2=secret2", ["secret1", "secret2"])
    assert "[REDACTED]" in result
    assert "secret1" not in result
    assert "secret2" not in result


def test_scrub_text_empty_secrets_list():
    from app.utils.masking import scrub_text
    result = scrub_text("some text with secrets", [])
    assert result == "some text with secrets"


# ---------------------------------------------------------------------------
# register_secret and _active_secrets
# ---------------------------------------------------------------------------

def test_register_secret_adds_value():
    from app.utils.masking import register_secret, _active_secrets, clear_secrets
    clear_secrets()
    register_secret("my_api_key_value")
    assert "my_api_key_value" in _active_secrets
    clear_secrets()


def test_register_secret_no_duplicates():
    from app.utils.masking import register_secret, _active_secrets, clear_secrets
    clear_secrets()
    register_secret("same_key")
    register_secret("same_key")
    assert _active_secrets.count("same_key") == 1
    clear_secrets()


def test_register_secret_empty_string_noop():
    from app.utils.masking import register_secret, _active_secrets, clear_secrets
    clear_secrets()
    register_secret("")
    assert "" not in _active_secrets
    clear_secrets()


def test_clear_secrets():
    from app.utils.masking import register_secret, _active_secrets, clear_secrets
    register_secret("key_to_clear")
    clear_secrets()
    assert len(_active_secrets) == 0
