import requests
from flask import Blueprint, request, current_app, session, redirect, url_for

bp = Blueprint('auth', __name__)


@bp.route('/login')
def login():
    # Retrieve the access code
    code = request.args.get('code')

    # Get the configuration
    config = current_app.config

    # Get the authorization token
    res = requests.post(
        url="https://slack.com/api/oauth.v2.access",
        data={
            'code': code,
            'client_secret': config['CLIENT_SECRET'],
            'client_id': config['CLIENT_ID'],
            'redirect_uri': request.base_url
        }
    )
    auth_data = res.json()
    token = auth_data["authed_user"]["access_token"]

    # Use the token to retrieve user data
    res = requests.get(
        url="https://slack.com/api/users.identity",
        headers={"Authorization": f"Bearer {token}"}
    )
    user_data = res.json()

    # Store it in the session information
    session["team"] = user_data["team"]
    session["user"] = user_data["user"]

    # Revoke the token now that we are done with it
    res = requests.post(
        url="https://slack.com/api/auth.revoke",
        data={'token': token}
    )
    reply_data = res.json()
    assert reply_data["revoked"]

    return redirect(url_for('status.homepage'))


@bp.route('/logout')
def logout():
    if 'team' in session:
        del session['team']
    if 'user' in session:
        del session['user']
    return redirect(url_for('status.homepage'))
