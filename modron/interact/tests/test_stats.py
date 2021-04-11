"""Test the statistical model"""
from pathlib import Path
import shutil


# Copy over the full logs before running the test
cur_path = Path(__file__).parent
shutil.copy(
    cur_path.parent.parent.parent.joinpath('dice-logs/kaluth.csv'),
    cur_path.joinpath('dice-logs/kaluth.csv')
)


def test_stats(parser, payload):
    payload.user_id = "UP4K437HT"

    # Run for all dice rolls
    args = parser.parse_args(['stats'])
    args.interact(args, payload)

    # Run for only perception checks
    args = parser.parse_args(['stats', '--reason', 'perception'])
    args.interact(args, payload)

    # Run for only unmodified rolls
    args = parser.parse_args(['stats', '--reason', 'perception', '--no-modifiers'])
    args.interact(args, payload)

    # Test where there should not be an
    args = parser.parse_args(['stats', '--reason', 'no way', '--no-modifiers'])
    args.interact(args, payload)
