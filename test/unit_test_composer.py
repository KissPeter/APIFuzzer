from hypothesis import strategies as st


@st.composite
def dict_str(draw):
    return draw(st.dictionaries(st.text(min_size=1), st.text(min_size=1), min_size=1))


@st.composite
def list_of_dicts(draw):
    return draw(st.lists(dict_str()))
