from datetime import datetime
import logging

from flask import Blueprint, render_template, request, flash, session, redirect, url_for

from app.exceptions.business_logic import ResourceAlreadyExistsException, InvalidCredentialsException
from app.exceptions.database import DatabaseException
from app.exceptions.validation import ValidationException
from app.models.enums import MembershipEnum
from app.models.user import CreateUserDTO, User
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


user_service = UserService()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    try:
        logger.debug(f"Authenticating user with email={email}")
        authenticated_user = user_service.authenticate(email, password)
        logger.debug(f"Authenticated user: {authenticated_user}")


        session["user_id"] = authenticated_user.id
        session["full_name"] = authenticated_user.full_name
        session["email"] = authenticated_user.email
        flash("Login successful. Welcome back!", "success")
        return redirect(url_for("main.home"))

    except InvalidCredentialsException as e:
        flash(e.user_message, "error")
        return render_template("login.html"), 401

    except DatabaseException as e:
        flash("Unable to authenticate. Please try again later", "error")
        logger.error(f"Database error during authentication: {e}", exc_info=True)
        return render_template("login.html"), 500

    # TODO: Forgot password








@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        logger.debug("GET /register")
        return render_template("register.html")

    name = request.form.get("name")
    surname = request.form.get("surname")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    date_of_birth = request.form.get("dob")

    if password != confirm_password:
        flash("Passwords do not match", "error")
        return render_template("register.html"), 400


    try:
        membership_enum = MembershipEnum.FREE
        dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        logger.debug(
            f"Creating user with name={name}, surname={surname}, email={email}, "
            f"password={password}, date_of_birth={date_of_birth}, membership={membership_enum}"
        ) # TODO: Remove password from logs once debugged
        dto = CreateUserDTO(
            name, surname, email, password, dob, membership_enum
        )
        created_user: User = user_service.register_user(dto)

        logger.info(f"Created user data '{created_user}'")

        session["user_id"] = created_user.id
        session["full_name"] = created_user.full_name
        session["email"] = created_user.email

        flash("Registration successful. Welcome to Frostel!", "success")
        return redirect(url_for("main.home"))

    except ValidationException as e:
        flash(e.user_message, "error")
        return render_template("register.html"), 400

    except ResourceAlreadyExistsException as e:
        flash(e.user_message, "error")
        return render_template("register.html"), 409

    except DatabaseException as e:
        flash("Unable to create account. Please try again later", "error")
        logger.error(f"Database error during registration: {e}", exc_info=True)
        return render_template("register.html"), 500



