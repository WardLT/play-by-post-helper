"""Views that will be often used by players"""

from flask import Blueprint, session, flash, redirect, render_template

from modron.characters import load_character, list_available_characters
from .decorators import enforce_login

bp = Blueprint('players', __name__)


@bp.route("/character")
@enforce_login
def display_sheet():
    # Get the user id
    user_id = session['user']['id']
    team_id = session['team']['id']

    # Look up their character
    available_chars = list_available_characters(team_id, user_id)
    if len(available_chars) == 0:
        flash('You do not have a character sheet yet. Ping Logan', 'danger')
        return redirect("/")
    elif len(available_chars) > 1:
        flash('We do not yet support >1 characters per player. Bother Logan', 'danger')
        return redirect("/")
    sheet, _ = load_character(team_id, available_chars[0])

    # Render the character sheet
    return render_template('sheet.html', sheet=sheet)
