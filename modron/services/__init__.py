"""Persistent processes that perform pre-defined projects periodically"""
from abc import ABCMeta, abstractmethod
from datetime import datetime
from math import inf
from threading import Thread
from asyncio import sleep
from typing import Optional
from discord import Guild
import logging

import humanize


logger = logging.getLogger(__name__)


class BaseService(Thread, metaclass=ABCMeta):
    """Base class for persistent services

    Start the thread to run asynchronously by calling
    :meth:`start()`. The thread will then run until
    the `stop` attribute is set to `True`. Note that the
    thread will not terminate until the the active call
    to `os.sleep` ends. If you would like the thread to terminate
    sooner, define a `max_sleep_time`

    Implementations of this class should define the `run` method,
    which will perform some tasks periodically. When the task is
    complete, the :meth:`_sleep_until` method can be used to
    cause the thread

    """
    def __init__(self, guild: Guild, max_sleep_time: float = inf, name: Optional[str] = None):
        """
        Args:
            guild: Connection to a certain guild
            max_sleep_time: Longest allowed sleep call in seconds
        """
        super().__init__(daemon=True, name=name)
        self._guild = guild
        self.stop = False
        self._max_sleep_time = max_sleep_time

    async def _sleep_until(self, wake_time: datetime):
        """Sleep until a certain time has been reached

        Args:
            wake_time (datetime): When for the sleep loop to end (UTC)
        """
        logger.info(f'Sleeping until {wake_time.isoformat()}, {humanize.naturaltime(wake_time)}.')
        while not self.stop:
            # Compute the amount of remaining time
            remaining_time = (wake_time - datetime.now()).total_seconds()
            if remaining_time <= 0:
                logger.warning(f'Requested a wake time that is {-remaining_time:.2f}s in the past.')
                return

            # Sleep for the maximum allowable time smaller
            #  than the amount of remaining time
            sleep_time = min(remaining_time, self._max_sleep_time)
            await sleep(sleep_time)

        raise ValueError('User has requested this thread to halt')

    @abstractmethod
    async def run(self):
        raise NotImplementedError()
