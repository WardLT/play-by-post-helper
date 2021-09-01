"""Test replying with dice statistics"""
from pathlib import Path
import shutil

from pytest import mark, fixture

from modron.interact.stats import StatisticModule


@fixture(autouse=True)
def spoof_dice_logs():
    """Spoof the """
    cur_path = Path(__file__).parent
    cur_path.joinpath('dice-logs').mkdir(exist_ok=True)
    shutil.copy(
        cur_path.parent.parent.parent.joinpath('dice-logs/kaluth-test.csv'),
        cur_path.joinpath('dice-logs/kaluth.csv')
    )


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

