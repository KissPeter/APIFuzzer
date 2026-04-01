import argparse
import json

import pytest
from hypothesis import given, strategies as st

from apifuzzer.utils import (
    json_data,
    merge_cli_headers,
    parse_headers_json,
    parse_single_header,
)
from test.unit_test_composer import dict_str, list_of_dicts


@given(st.text(min_size=1).filter(lambda s: not _is_dict_or_list_json(s)))
def test_json_data_invalid(data):
    with pytest.raises(argparse.ArgumentTypeError):
        json_data(data)


def _is_dict_or_list_json(s):
    """Return True if s parses as a JSON dict or list (so it's valid input for json_data)."""
    try:
        v = json.loads(s)
        return isinstance(v, (dict, list))
    except Exception:
        return False


@given(data=dict_str())
def test_json_data_dict_valid(data):
    res = json_data(data)
    assert isinstance(res, dict)


@given(data=list_of_dicts())
def test_json_data_list_valid(data):
    res = json_data(data)
    assert isinstance(res, list)


# ── Regression tests for the space-in-header-value bug ──────────────────────
# When --headers is passed via Docker the old entrypoint.sh split on spaces,
# causing json_data to receive a truncated string.  These tests verify that
# well-formed JSON with spaces in values is accepted, and that the error
# message for truncated/invalid input is a readable string (not a tuple).

@pytest.mark.parametrize("header_json", [
    '[{"Authorization": "Basic dXNlcjpwYXNz"}]',
    '[{"Authorization": "Bearer my token with spaces"}]',
    '[{"Authorization": "Basic abc123"}, {"X-Custom": "value with spaces"}]',
    '{"Authorization": "Basic abc123"}',
])
def test_json_data_with_spaces_in_value(header_json):
    """Headers whose values contain spaces must parse successfully."""
    result = json_data(header_json)
    assert isinstance(result, (dict, list))


@pytest.mark.parametrize("truncated", [
    '[{"Authorization":"Basic',
    '[{"Authorization":',
    '[{',
])
def test_json_data_invalid_error_message_is_string(truncated):
    """The ArgumentTypeError message must be a plain string, not a tuple."""
    with pytest.raises(argparse.ArgumentTypeError) as exc_info:
        json_data(truncated)
    msg = str(exc_info.value)
    # Must NOT look like the old tuple repr  ('%s is not JSON', '...')
    assert msg.startswith("(") is False or "%" not in msg
    assert isinstance(msg, str)


def test_parse_headers_json_object_with_spaces():
    parsed = parse_headers_json('{"Authorization": "Basic abc def", "X-Name": "Jane Doe"}')
    assert parsed == {
        "Authorization": "Basic abc def",
        "X-Name": "Jane Doe",
    }


def test_parse_headers_json_list_of_objects():
    parsed = parse_headers_json('[{"Authorization": "token"}, {"X-Name": "Jane Doe"}]')
    assert parsed == {"Authorization": "token", "X-Name": "Jane Doe"}


def test_parse_single_header_with_spaces():
    key, value = parse_single_header("Authorization: Basic abc def")
    assert key == "Authorization"
    assert value == "Basic abc def"


def test_merge_cli_headers_single_header_overrides_json():
    merged = merge_cli_headers(
        '{"Authorization": "Basic old", "X-Name": "Jane"}',
        ["Authorization: Basic new token"],
    )
    assert merged == {"Authorization": "Basic new token", "X-Name": "Jane"}


def test_parse_single_header_invalid_format():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_single_header("Authorization Basic abc def")


# ── pkg_resources monkeypatch tests ─────────────────────────────────────────

def test_pkg_resources_shim_get_distribution():
    """The shim (or real pkg_resources) must resolve installed packages."""
    import apifuzzer  # noqa: F401 – triggers _ensure_pkg_resources
    from pkg_resources import get_distribution

    dist = get_distribution("kittyfuzzer")
    assert hasattr(dist, "version")
    assert isinstance(dist.version, str)
    assert len(dist.version) > 0


def test_pkg_resources_shim_not_found():
    """get_distribution must raise for non-existent packages."""
    import apifuzzer  # noqa: F401
    from pkg_resources import get_distribution, DistributionNotFound

    with pytest.raises((DistributionNotFound, Exception)):
        get_distribution("this-package-does-not-exist-xyz-42")


