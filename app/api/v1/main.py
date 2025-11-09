from flask import render_template, Blueprint

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def hello_world():  # put application's code here
    return render_template("index.html")


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    return render_template("index.html")


@main_bp.route("/register", methods=["GET", "POST"])
def register():
    return render_template("register.html")
