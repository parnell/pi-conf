import pytest

from pi_conf import AttrDict


@pytest.fixture
def sample_dict():
    return AttrDict({"a": {"b": {"c": 1, "d": None}, "e": 2}, "f": 3, "g": None})


def test_get_nested_existing_keys(sample_dict):
    assert sample_dict.get_nested("a.b.c") == 1
    assert sample_dict.get_nested("a.e") == 2
    assert sample_dict.get_nested("f") == 3
    assert sample_dict.get_nested("a.b.d") is None
    assert sample_dict.get_nested("g") is None


def test_get_nested_missing_keys_with_default(sample_dict):
    assert sample_dict.get_nested("a.b.x", "default") == "default"
    assert sample_dict.get_nested("x.y.z", None) is None
    assert sample_dict.get_nested("a.x", 0) == 0


def test_get_nested_missing_keys_without_default(sample_dict):
    with pytest.raises(KeyError):
        sample_dict.get_nested("a.b.x")
    with pytest.raises(KeyError):
        sample_dict.get_nested("x.y.z")


def test_get_nested_non_dict_intermediate(sample_dict):
    with pytest.raises(KeyError):
        sample_dict.get_nested("f.x")
    assert sample_dict.get_nested("f.x", "default") == "default"


def test_get_nested_empty_key(sample_dict):
    with pytest.raises(KeyError):
        sample_dict.get_nested("")


def test_get_nested_none_default(sample_dict):
    assert sample_dict.get_nested("a.b.x", None) is None
    assert sample_dict.get_nested("x.y.z", None) is None


def test_get_nested_modify_dict(sample_dict):
    sample_dict["h"] = {"i": {"j": 4}}
    assert sample_dict.get_nested("h.i.j") == 4


def test_get_nested_with_special_characters(sample_dict):
    sample_dict["special!@#"] = {"$%^&*": {"()_+": "chars"}}
    assert sample_dict.get_nested("special!@#.$%^&*.()_+") == "chars"


def test_get_nested_list_behavior():
    d = AttrDict(
        {
            "a": [{"b": 1}, {"c": 2}],
            "x": [{"y": [{"z": 3}]}],
        },
    )

    # Test basic list behavior
    assert d.get_nested("a") == [{"b": 1}, {"c": 2}]

    # Test accessing first list item by default
    assert d.get_nested("a.b") == 1

    # Test accessing second list item
    assert d.get_nested("a.c", list_item=1) == 2

    # Test deeper nesting
    assert d.get_nested("x.y.z") == 3

    # Test deeper nesting with default
    assert d.get_nested("x.y.z.notexist", default=4) == 4

    # Test error when key doesn't exist in first list item
    with pytest.raises(KeyError):
        d.get_nested("a.c")

    # Test using default value
    assert d.get_nested("a.d", default=None) is None


def test_get_nested_list_item_parameter():
    d = AttrDict({"a": [{"b": 1}, {"b": 2}, {"b": 3}]})

    # Test different list_item values
    assert d.get_nested("a.b", list_item=0) == 1
    assert d.get_nested("a.b", list_item=1) == 2
    assert d.get_nested("a.b", list_item=2) == 3

    # Test out of range
    with pytest.raises(KeyError):
        d.get_nested("a.b", list_item=3)

    # Test with default value
    assert d.get_nested("a.b", list_item=3, default="default") == "default"


def test_get_nested_disable_list_item():
    d = AttrDict({"a": [{"b": 1}, {"b": 2}]})

    # Test disabling list_item
    assert d.get_nested("a", list_item=None) == [{"b": 1}, {"b": 2}]


def test_get_nested_list_item():
    d = AttrDict({"a": [{"b": 1}, {"b": 2}]})

    assert d.get_nested("a") == [{"b": 1}, {"b": 2}]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
