"""Utility decorators for functions"""
import logging

from flask import session, url_for, flash, redirect, request

logger = logging.getLogger(__name__)


def enforce_login(func):
    """Ensure that a user is logged in before moving to a page."""
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            logger.info(f'Preventing access to {request.base_url} without log in')
            flash('You must log in to access this page.')
            return redirect(url_for('status.homepage'))
        else:
            return func(*args, **kwargs)
    return wrapper
