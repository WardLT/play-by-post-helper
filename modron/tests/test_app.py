from multiprocessing import Process
from time import sleep

from modron.app import main


def test_launch():
    # Launch Modron as a subprocess
    proc = Process(target=main, daemon=True, kwargs={'testing': True})
    proc.start()

    # Issue a kill command after 30 seconds
    sleep(30)
    proc.terminate()

    # See if it exits cleanly
    proc.join(timeout=30)
    assert proc.exitcode is not None, 'Still has not terminated'
    assert proc.exitcode == 0, f'Something went awry. Exitcode: {proc.exitcode}'
