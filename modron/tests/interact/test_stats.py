"""Test replying with dice statistics"""
from tempfile import TemporaryDirectory
from pathlib import Path
import shutil

from pytest import mark, fixture

from modron.interact.stats import StatisticModule
from modron.config import config

example_path = Path(__file__).parent / 'dice-logs' / 'kaluth-test.csv'


@fixture(autouse=True)
def spoof_dice_logs():
    """Spoof the dice logs so we don't overwrite existing ones"""
    dice_path = Path(config.dice_log_dir)
    with TemporaryDirectory() as td:
        td = Path(td)
        # Move the old dice somewhere
        restore_copy = dice_path.is_dir()
        if restore_copy:
            shutil.copytree(dice_path, td / 'test-dir')

        # Copy in some examples
        shutil.copy(
            example_path,
            dice_path / 'kaluth.csv'
        )
        yield None

        if restore_copy:
            shutil.rmtree(dice_path)
            shutil.copytree(td / 'test-dir', dice_path)


@mark.asyncio
async def test_stats(payload):
    """Just make sure the commands do not error out"""
    # Make the parser
    module = StatisticModule()
    parser = module.parser

    # Run for all dice rolls
    args = parser.parse_args([])
    await module.interact(args, payload)
    assert 'No matching dice' in payload.last_message

    # Screen by player
    args = parser.parse_args(['--character', 'Adrianna'])
    await module.interact(args, payload)
    assert 'd20 rolls' in payload.last_message

    # Run for only perception checks
    args = parser.parse_args(['--reason', 'perception'])
    await module.interact(args, payload)

    # Run for only unmodified rolls
    args = parser.parse_args(['--reason', 'perception', '--no-modifiers'])
    await module.interact(args, payload)

    # Test where there should not be any rolls
    args = parser.parse_args(['--reason', 'no way', '--no-modifiers'])
    await module.interact(args, payload)

    # Screen by channel
    args = parser.parse_args(['--channel', 'ic_all'])
    await module.interact(args, payload)
