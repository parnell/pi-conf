import pytest
from pi_conf import AttrDict 

@pytest.fixture
def sample_dict():
    return AttrDict({
        'a': {
            'b': {
                'c': 1,
                'd': None
            },
            'e': 2
        },
        'f': 3,
        'g': None
    })

def test_get_nested_existing_keys(sample_dict):
    assert sample_dict.get_nested('a.b.c') == 1
    assert sample_dict.get_nested('a.e') == 2
    assert sample_dict.get_nested('f') == 3
    assert sample_dict.get_nested('a.b.d') is None
    assert sample_dict.get_nested('g') is None

def test_get_nested_missing_keys_with_default(sample_dict):
    assert sample_dict.get_nested('a.b.x', 'default') == 'default'
    assert sample_dict.get_nested('x.y.z', None) is None
    assert sample_dict.get_nested('a.x', 0) == 0

def test_get_nested_missing_keys_without_default(sample_dict):
    with pytest.raises(KeyError):
        sample_dict.get_nested('a.b.x')
    with pytest.raises(KeyError):
        sample_dict.get_nested('x.y.z')

def test_get_nested_non_dict_intermediate(sample_dict):
    with pytest.raises(KeyError):
        sample_dict.get_nested('f.x')
    assert sample_dict.get_nested('f.x', 'default') == 'default'

def test_get_nested_empty_key(sample_dict):
    with pytest.raises(KeyError):
        sample_dict.get_nested('')

def test_get_nested_none_default(sample_dict):
    assert sample_dict.get_nested('a.b.x', None) is None
    assert sample_dict.get_nested('x.y.z', None) is None

def test_get_nested_modify_dict(sample_dict):
    sample_dict['h'] = {'i': {'j': 4}}
    assert sample_dict.get_nested('h.i.j') == 4

def test_get_nested_with_special_characters(sample_dict):
    sample_dict['special!@#'] = {'$%^&*': {'()_+': 'chars'}}
    assert sample_dict.get_nested('special!@#.$%^&*.()_+') == 'chars'

if __name__ == '__main__':
    pytest.main(['-v', __file__])