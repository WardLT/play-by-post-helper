from pytest import fixture

from modron import create_app


@fixture()
def app():
    return create_app()
