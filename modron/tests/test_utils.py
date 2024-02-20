from modron.utils import get_version


def test_version():
    assert len(get_version()) == 40
