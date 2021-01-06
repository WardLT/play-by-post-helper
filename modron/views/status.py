"""Views related to Modron status pages"""
import platform
from datetime import datetime

import humanize
from flask import Blueprint, render_template, current_app, redirect, url_for, flash

from .decorators import enforce_login
from .. import ReminderService

bp = Blueprint('status', __name__)


@bp.route("/")
def homepage():
    awake_time = humanize.naturaldelta(datetime.now() - current_app.config['start_time'])
    hostname = platform.node()
    return render_template("home.html", awake_time=awake_time, hostname=hostname)


@bp.route('/services/reminder/<team_name>')
@enforce_login
def reminder(team_name):
    # Get the configuration for the current application
    threads = current_app.config['services']['reminder']

    # Get the service object
    if team_name not in threads:
        flash(f'No reminder service for team "{team_name}"', "danger")
        return redirect(url_for('status.homepage'))
    reminder: ReminderService = threads[team_name]

    return render_template("reminder.html", team=team_name, reminder=reminder)
