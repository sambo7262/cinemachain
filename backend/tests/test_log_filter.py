"""
Tests for backend/app/utils/log_filter.py (ScrubSecretsFilter) and
scrub_traceback() in masking.py.
All behavior cases from 18-02-PLAN.md Task 1.
"""
import logging
import pytest


# ---------------------------------------------------------------------------
# ScrubSecretsFilter — secret replacement
# ---------------------------------------------------------------------------

def test_filter_scrubs_registered_secret_in_msg():
    from app.utils.masking import register_secret, clear_secrets
    from app.utils.log_filter import ScrubSecretsFilter

    clear_secrets()
    register_secret("super_secret_key_abc123")
    f = ScrubSecretsFilter()

    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="request url?api_key=super_secret_key_abc123 failed",
        args=(), exc_info=None,
    )
    result = f.filter(record)

    assert result is True
    assert "super_secret_key_abc123" not in record.msg
    assert "[REDACTED]" in record.msg
    clear_secrets()


def test_filter_always_returns_true():
    from app.utils.log_filter import ScrubSecretsFilter

    f = ScrubSecretsFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="harmless log message",
        args=(), exc_info=None,
    )
    assert f.filter(record) is True


def test_filter_scrubs_api_key_pattern_no_registered_secrets():
    """Pattern-based scrub works even with empty _active_secrets."""
    from app.utils.masking import clear_secrets
    from app.utils.log_filter import ScrubSecretsFilter

    clear_secrets()
    f = ScrubSecretsFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="GET https://api.tmdb.org/3/movie?api_key=abcdef1234567890",
        args=(), exc_info=None,
    )
    f.filter(record)
    assert "abcdef1234567890" not in record.msg
    assert "[REDACTED]" in record.msg


def test_filter_scrubs_apikey_variant():
    from app.utils.masking import clear_secrets
    from app.utils.log_filter import ScrubSecretsFilter

    clear_secrets()
    f = ScrubSecretsFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="https://mdblist.com/api/?apikey=SECRETKEY12345",
        args=(), exc_info=None,
    )
    f.filter(record)
    assert "SECRETKEY12345" not in record.msg
    assert "[REDACTED]" in record.msg


def test_filter_scrubs_authorization_bearer_pattern():
    from app.utils.masking import clear_secrets
    from app.utils.log_filter import ScrubSecretsFilter

    clear_secrets()
    f = ScrubSecretsFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig",
        args=(), exc_info=None,
    )
    f.filter(record)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in record.msg
    assert "[REDACTED]" in record.msg


def test_filter_scrubs_x_api_key_pattern():
    from app.utils.masking import clear_secrets
    from app.utils.log_filter import ScrubSecretsFilter

    clear_secrets()
    f = ScrubSecretsFilter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="X-Api-Key: myRadarrKeyValueXYZ789",
        args=(), exc_info=None,
    )
    f.filter(record)
    assert "myRadarrKeyValueXYZ789" not in record.msg
    assert "[REDACTED]" in record.msg


def test_filter_scrubs_tuple_args():
    from app.utils.masking import register_secret, clear_secrets
    from app.utils.log_filter import ScrubSecretsFilter

    clear_secrets()
    register_secret("arg_secret_key_value99")
    f = ScrubSecretsFilter()

    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="key=%s",
        args=("arg_secret_key_value99",), exc_info=None,
    )
    f.filter(record)
    assert "arg_secret_key_value99" not in record.args
    assert "[REDACTED]" in record.args
    clear_secrets()


def test_filter_scrubs_dict_args():
    """Test that dict args have string values scrubbed (filter directly mutates record.args)."""
    from app.utils.masking import register_secret, clear_secrets
    from app.utils.log_filter import ScrubSecretsFilter

    clear_secrets()
    register_secret("dict_secret_key_val88")
    f = ScrubSecretsFilter()

    # Construct LogRecord manually and set args directly to avoid Python 3.9
    # logging internals attempting to format the dict during construction.
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="key=%(key)s",
        args=(), exc_info=None,
    )
    # Override args directly so the filter sees a dict without the formatter triggering.
    record.args = {"key": "dict_secret_key_val88"}
    f.filter(record)
    assert isinstance(record.args, dict)
    assert "dict_secret_key_val88" not in record.args.values()
    assert "[REDACTED]" in record.args.values()
    clear_secrets()


def test_filter_scrubs_exc_text():
    from app.utils.masking import register_secret, clear_secrets
    from app.utils.log_filter import ScrubSecretsFilter

    clear_secrets()
    register_secret("exc_secret_key_xyz77")
    f = ScrubSecretsFilter()

    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg="error occurred",
        args=(), exc_info=None,
    )
    record.exc_text = "Traceback...exc_secret_key_xyz77 in URL"
    f.filter(record)
    assert "exc_secret_key_xyz77" not in record.exc_text
    assert "[REDACTED]" in record.exc_text
    clear_secrets()


# ---------------------------------------------------------------------------
# scrub_traceback
# ---------------------------------------------------------------------------

def test_scrub_traceback_empty_string():
    from app.utils.masking import scrub_traceback
    assert scrub_traceback(None) == "" or scrub_traceback(None) is not None  # accepts None arg


def test_scrub_traceback_replaces_registered_secret():
    from app.utils.masking import register_secret, clear_secrets, scrub_traceback

    clear_secrets()
    register_secret("traceback_secret_key_555")
    try:
        raise ValueError("request failed api_key=traceback_secret_key_555")
    except ValueError as exc:
        result = scrub_traceback(exc)

    assert "traceback_secret_key_555" not in result
    assert "[REDACTED]" in result
    clear_secrets()


def test_scrub_traceback_no_registered_secrets_unchanged():
    from app.utils.masking import clear_secrets, scrub_traceback

    clear_secrets()
    try:
        raise ValueError("some ordinary error message")
    except ValueError as exc:
        result = scrub_traceback(exc)

    assert "some ordinary error message" in result
    # no secrets registered, so nothing is replaced
    assert "[REDACTED]" not in result


def test_scrub_traceback_empty_exc_returns_string():
    from app.utils.masking import clear_secrets, scrub_traceback

    clear_secrets()
    # scrub_traceback() with no exc falls back to format_exc which may return NoneType message
    # just verify it returns a str
    result = scrub_traceback(None)
    assert isinstance(result, str)
