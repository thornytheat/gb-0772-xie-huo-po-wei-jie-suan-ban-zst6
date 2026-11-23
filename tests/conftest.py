import pytest
from fastapi.testclient import TestClient

from app.clearing import Clearing
from app.main import create_app
from app.source.packet import bundle


@pytest.fixture(scope='session')
def dirty():
    return Clearing(bundle('dirty'),b'fixture-2026')


@pytest.fixture(scope='session')
def clean():
    return Clearing(bundle('clean'),b'fixture-2026')


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'clearing.sqlite')) as client:
        yield client
