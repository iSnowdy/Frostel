import logging

from flask import Blueprint, render_template

logger = logging.getLogger(__name__)

home_bp = Blueprint("main", __name__)


@home_bp.route("/")
def home():  # put application's code here
    return render_template("index.html")

