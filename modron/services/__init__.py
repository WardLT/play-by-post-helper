"""Persistent processes that perform pre-defined projects periodically"""
from abc import ABCMeta, abstractmethod
from datetime import datetime
from asyncio import Event, wait_for
from discord import Guild
import logging

import humanize


logger = logging.getLogger(__name__)


class BaseService(metaclass=ABCMeta):
    """Base class for persistent services

    Services are implemented as an async function which runs
    until the :attr:`stop` Event is set.

    Most of the time will be spent in the :func:`sleep_until` function
    as the service is waiting between actions.
    """

    stop: Event
    """Set this event to stop the service"""

    def __init__(self, guild: Guild):
        """
        Args:
            guild: Connection to a certain guild
        """
        super().__init__()
        self._guild = guild
        self.stop: Event = Event()

    async def sleep_until(self, wake_time: datetime):
        """Sleep until a certain time has been reached

        Args:
            wake_time (datetime): When for the sleep loop to end (UTC)
        """
        # Compute the amount of remaining time
        remaining_time = (wake_time - datetime.now()).total_seconds()
        if remaining_time <= 0:
            logger.warning(f'Requested a wake time that is {-remaining_time:.2f}s in the past.')
            return

        # Sleep for the maximum allowable time smaller
        #  than the amount of remaining time
        logger.info(f'Sleeping until {wake_time.isoformat()}, {humanize.naturaltime(wake_time)}.')
        try:
            await wait_for(self.stop.wait(), remaining_time)
        except TimeoutError:
            return

    @abstractmethod
    async def run(self):
        raise NotImplementedError()
