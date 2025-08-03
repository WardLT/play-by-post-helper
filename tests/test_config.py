from datetime import time

from modron.config import TeamConfig


def test_sort_window():
    cfg = TeamConfig(name='test', reminder_window=(time(hour=21), time(hour=6)))
    assert cfg.reminder_window == (time(hour=6), time(hour=21))
