from flask import url_for


def test_home(client):
    assert client.get(url_for('status.homepage')).status_code == 200
