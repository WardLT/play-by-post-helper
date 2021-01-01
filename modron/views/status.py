"""Views related to Modron status pages"""
import platform
from datetime import datetime

import humanize
from flask import Blueprint, render_template, current_app

bp = Blueprint('status', __name__)


@bp.route("/")
def homepage():
    awake_time = humanize.naturaldelta(datetime.now() - current_app.config['start_time'])
    hostname = platform.node()
    return render_template("home.html", awake_time=awake_time, hostname=hostname)
