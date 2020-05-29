import os

from pytest import fixture

from modron.db import ModronState
from modron.config import get_config


@fixture
def config(tmpdir):
    config = get_config()
    config.state_path = os.path.join(tmpdir, 'state.yml')
    ModronState().save(config.state_path)
    return config


def test_save_and_load(config):
    # Test that it modifies the file
    before_time = os.path.getmtime(config.state_path)
    state = ModronState.load(config.state_path)
    state.save(config.state_path)
    after_time = os.path.getmtime(config.state_path)
    assert after_time > before_time

    # Test that it still loads again
    ModronState.load(config.state_path)
