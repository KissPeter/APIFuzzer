import argparse

import pytest
from hypothesis import given, strategies as st

from apifuzzer.utils import json_data
from test.unit_test_composer import dict_str, list_of_dicts


@given(st.text(min_size=1))
def test_json_data_invalid(data):
    with pytest.raises(argparse.ArgumentTypeError):
        json_data(data)


@given(data=dict_str())
def test_json_data_dict_valid(data):
    res = json_data(data)
    assert isinstance(res, dict)


@given(data=list_of_dicts())
def test_json_data_list_valid(data):
    res = json_data(data)
    assert isinstance(res, list)
