import os
import time

import pytest
import docker
import pymysql


@pytest.fixture
def docker_client():
    return docker.client.from_env()


@pytest.fixture
def source_database(docker_client):
    name = os.environ.get("SOURCE_DATABASE_NAME", "test_source_database")
    password = os.environ.get("SOURCE_MYSQL_ROOT_PASSWORD", "password")
    container = docker_client.containers.run(
        "datajoint/mysql:5.7",
        detach=True,
        name=name,
        environment=dict(MYSQL_ROOT_PASSWORD=password),
        network=os.environ.get("DOCKER_NETWORK", "test_network"),
    )
    time.sleep(float(os.environ.get("HEALTH_CHECK_START_PERIOD", 0)))
    n_tries = 0
    while True:
        container.reload()
        if container.attrs["State"]["Health"]["Status"] == "healthy":
            break
        if n_tries >= int(os.environ.get("HEALTH_CHECK_MAX_RETRIES", 60)):
            raise RuntimeError(f"Trying to bring up container '{name}' exceeded max number of retries")
        time.sleep(float(os.environ.get("HEALTH_CHECK_INTERVAL", 1)))
        n_tries += 1
    connection = pymysql.connect(host=name, user="root", password=password, cursorclass=pymysql.cursors.DictCursor)
    yield connection
    connection.close()
    container.stop()
    if os.environ.get("DOCKER_REMOVE_CONTAINERS", True):
        container.remove()


def test_dummy(source_database):
    assert True
