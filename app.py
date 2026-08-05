import os
import secrets
import sqlite3

from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

import pandas as pd

from dotenv import load_dotenv

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from flask_mail import Mail, Message

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)


# =========================================================
# Application configuration
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(
    dotenv_path=BASE_DIR / ".env",
    override=True
)

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    secrets.token_hex(32)
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Keep False while running locally with http://127.0.0.1
# Set SESSION_COOKIE_SECURE=true after deploying with HTTPS.
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("SESSION_COOKIE_SECURE", "false")
    .strip()
    .lower()
    == "true"
)


# =========================================================
# Email configuration
# =========================================================

app.config["MAIL_SERVER"] = os.getenv(
    "MAIL_SERVER",
    "smtp.gmail.com"
)

app.config["MAIL_PORT"] = int(
    os.getenv(
        "MAIL_PORT",
        "587"
    )
)

app.config["MAIL_USE_TLS"] = (
        os.getenv(
            "MAIL_USE_TLS",
            "true"
        ).lower() == "true"
)

app.config["MAIL_USE_SSL"] = False

app.config["MAIL_USERNAME"] = (
    os.getenv("MAIL_USERNAME", "")
    .strip()
)

app.config["MAIL_PASSWORD"] = (
    os.getenv("MAIL_PASSWORD", "")
    .replace(" ", "")
    .strip()
)

app.config["MAIL_DEFAULT_SENDER"] = (
    os.getenv("MAIL_DEFAULT_SENDER", "")
    .strip()
)

mail = Mail(app)

print("Gmail SMTP configuration:")
print(
    "MAIL_USERNAME:",
    app.config["MAIL_USERNAME"]
)
print(
    "MAIL_PASSWORD length:",
    len(app.config["MAIL_PASSWORD"])
)
print(
    "MAIL_DEFAULT_SENDER:",
    app.config["MAIL_DEFAULT_SENDER"]
)


# =========================================================
# File configuration
# =========================================================


FORECAST_FILE = (
        BASE_DIR
        / "data"
        / "june_2026_recursive_margin_forecast.csv"
)

DATABASE_FILE = Path(
    os.getenv(
        "DATABASE_PATH",
        str(BASE_DIR / "users.db")
    )
).expanduser().resolve()

ALLOWED_EMAIL_DOMAIN = os.getenv(
    "ALLOWED_EMAIL_DOMAIN",
    "columbia.edu"
).strip().lower()


# Frontend channel name -> CSV channel name
CHANNEL_TO_DATA = {
    "All Channels": None,
    "Stores": "Stores",
    "E-commerce": "E-commerce",
    "Vans": "Vans"
}


# =========================================================
# Authentication database
# =========================================================

def get_database_connection():
    """
    Open a connection to the local SQLite database.
    """

    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    """
    Create the users table and add any missing columns.
    """

    with get_database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 0,
                verification_code_hash TEXT,
                verification_expires_at TEXT,
                reset_code_hash TEXT,
                reset_expires_at TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if "reset_code_hash" not in existing_columns:
            connection.execute(
                """
                ALTER TABLE users
                ADD COLUMN reset_code_hash TEXT
                """
            )

        if "reset_expires_at" not in existing_columns:
            connection.execute(
                """
                ALTER TABLE users
                ADD COLUMN reset_expires_at TEXT
                """
            )


initialize_database()


# =========================================================
# Authentication helper functions
# =========================================================

def normalize_email(email):
    """
    Normalize an email address for comparison.
    """

    return str(email).strip().lower()


def is_allowed_email(email):
    """
    Allow registration only for the configured domain.
    """

    normalized_email = normalize_email(
        email
    )

    required_suffix = (
        f"@{ALLOWED_EMAIL_DOMAIN}"
    )

    return normalized_email.endswith(
        required_suffix
    )


def password_is_valid(password):
    """
    Require at least 8 characters, including uppercase,
    lowercase, and one number.
    """

    if len(password) < 8:
        return False

    if not any(
            character.isupper()
            for character in password
    ):
        return False

    if not any(
            character.islower()
            for character in password
    ):
        return False

    if not any(
            character.isdigit()
            for character in password
    ):
        return False

    return True


def generate_verification_code():
    """
    Generate a secure 6-digit verification code.
    """

    return (
        f"{secrets.randbelow(1_000_000):06d}"
    )


def send_verification_email(
        recipient_email,
        verification_code
):
    """
    Send a verification code using Gmail SMTP.
    """

    if not app.config["MAIL_USERNAME"]:
        raise RuntimeError(
            "MAIL_USERNAME is missing from .env."
        )

    if not app.config["MAIL_PASSWORD"]:
        raise RuntimeError(
            "MAIL_PASSWORD is missing from .env."
        )

    message = Message(
        subject=(
            "JBS Swift Forecast Portal "
            "verification code"
        ),
        recipients=[
            recipient_email
        ]
    )

    message.body = (
        "Welcome to the JBS Swift Forecast Portal.\n\n"
        "Your verification code is:\n\n"
        f"{verification_code}\n\n"
        "This code expires in 10 minutes.\n\n"
        "If you did not request this code, "
        "you can ignore this email."
    )

    mail.send(message)

def send_password_reset_email(
        recipient_email,
        reset_code
):
    """
    Send a password reset code using Gmail SMTP.
    """

    if not app.config["MAIL_USERNAME"]:
        raise RuntimeError(
            "MAIL_USERNAME is missing from .env."
        )

    if not app.config["MAIL_PASSWORD"]:
        raise RuntimeError(
            "MAIL_PASSWORD is missing from .env."
        )

    message = Message(
        subject=(
            "JBS Swift Forecast Portal "
            "password reset code"
        ),
        recipients=[
            recipient_email
        ]
    )

    message.body = (
        "A password reset was requested for your "
        "JBS Swift Forecast Portal account.\n\n"
        "Your password reset code is:\n\n"
        f"{reset_code}\n\n"
        "This code expires in 10 minutes.\n\n"
        "If you did not request a password reset, "
        "you can ignore this email."
    )

    mail.send(message)

def page_login_required(route_function):
    """
    Redirect unauthenticated page visitors to /login.
    """

    @wraps(route_function)
    def wrapped_route(
            *args,
            **kwargs
    ):
        if not session.get("user_email"):
            return redirect(
                url_for("login")
            )

        return route_function(
            *args,
            **kwargs
        )

    return wrapped_route


def api_login_required(route_function):
    """
    Return JSON 401 for unauthenticated API requests.
    """

    @wraps(route_function)
    def wrapped_route(
            *args,
            **kwargs
    ):
        if not session.get("user_email"):
            return jsonify({
                "error": (
                    "You must log in before "
                    "accessing this resource."
                )
            }), 401

        return route_function(
            *args,
            **kwargs
        )

    return wrapped_route


# =========================================================
# Forecast helper functions
# =========================================================

def load_forecast_data():
    """
    Load and validate the June 2026 forecast file.
    """

    if not FORECAST_FILE.exists():
        raise FileNotFoundError(
            f"Forecast file was not found: "
            f"{FORECAST_FILE}"
        )

    forecast_df = pd.read_csv(
        FORECAST_FILE
    )

    required_columns = {
        "date",
        "channel",
        "predicted_margin",
        "forecast_origin",
        "forecast_horizon_day",
        "forecast_mode",
        "model_name",
        "feature_set",
        "weather_feature_source",
        "actual_margin_available_flag"
    }

    missing_columns = (
            required_columns
            - set(forecast_df.columns)
    )

    if missing_columns:
        raise ValueError(
            "Forecast file is missing "
            "required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    forecast_df["date"] = pd.to_datetime(
        forecast_df["date"],
        errors="coerce"
    )

    numeric_columns = [
        "predicted_margin",
        "forecast_horizon_day",
        "actual_margin_available_flag"
    ]

    for column in numeric_columns:
        forecast_df[column] = pd.to_numeric(
            forecast_df[column],
            errors="coerce"
        )

    forecast_df = forecast_df.dropna(
        subset=[
            "date",
            "channel",
            "predicted_margin"
        ]
    )

    return forecast_df


def parse_filters():
    """
    Read and validate dashboard query parameters.
    """

    start_date = request.args.get(
        "start_date"
    )

    end_date = request.args.get(
        "end_date"
    )

    channel = request.args.get(
        "channel",
        "All Channels"
    )

    if not start_date or not end_date:
        return None, (
            jsonify({
                "error": (
                    "Start date and end date "
                    "are required."
                )
            }),
            400
        )

    try:
        parsed_start_date = pd.to_datetime(
            start_date,
            format="%Y-%m-%d"
        )

        parsed_end_date = pd.to_datetime(
            end_date,
            format="%Y-%m-%d"
        )

    except (ValueError, TypeError):
        return None, (
            jsonify({
                "error": (
                    "Dates must use "
                    "YYYY-MM-DD format."
                )
            }),
            400
        )

    if parsed_end_date < parsed_start_date:
        return None, (
            jsonify({
                "error": (
                    "End date cannot be earlier "
                    "than start date."
                )
            }),
            400
        )

    available_channels = set(
        load_forecast_data()["channel"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if (
            channel != "All Channels"
            and channel not in available_channels
    ):
        return None, (
            jsonify({
                "error": "Invalid channel."
            }),
            400
        )

    filters = {
        "start_date": parsed_start_date,
        "end_date": parsed_end_date,
        "channel": channel
    }

    return filters, None


def filter_forecast_data(
        forecast_df,
        start_date,
        end_date,
        channel
):
    """
    Filter forecast data by date and channel.
    """

    filtered_df = forecast_df[
        (
                forecast_df["date"]
                >= start_date
        )
        & (
                forecast_df["date"]
                <= end_date
        )
        ].copy()

    csv_channel = (
        None
        if channel == "All Channels"
        else channel
    )

    if csv_channel is not None:
        filtered_df = filtered_df[
            filtered_df["channel"]
            == csv_channel
            ].copy()

    return filtered_df


def format_currency(value):
    """
    Format a number as a compact US dollar value.
    """

    value = float(value)

    if abs(value) >= 1_000_000:
        return (
            f"${value / 1_000_000:.2f}M"
        )

    if abs(value) >= 1_000:
        return (
            f"${value / 1_000:.2f}K"
        )

    return f"${value:,.2f}"


def format_percentage(value):
    """
    Format a decimal or whole-number percentage.
    """

    value = float(value)

    if abs(value) <= 1:
        value *= 100

    return f"{value:.1f}%"


def calculate_summary(filtered_df):
    """
    Calculate total sales, margin, and margin rate.
    """

    if filtered_df.empty:
        return {
            "forecastSales": "$0.00",
            "forecastMargin": "$0.00",
            "marginRate": "0.0%",
            "forecastSalesRaw": 0,
            "forecastMarginRaw": 0,
            "marginRateRaw": 0
        }

    forecast_sales = float(
        filtered_df[
            "predicted_sales"
        ].sum()
    )

    forecast_margin = float(
        filtered_df[
            "predicted_margin"
        ].sum()
    )

    if forecast_sales != 0:
        margin_rate = (
                forecast_margin
                / forecast_sales
        )
    else:
        margin_rate = 0

    return {
        "forecastSales": format_currency(
            forecast_sales
        ),
        "forecastMargin": format_currency(
            forecast_margin
        ),
        "marginRate": format_percentage(
            margin_rate
        ),
        "forecastSalesRaw": forecast_sales,
        "forecastMarginRaw": forecast_margin,
        "marginRateRaw": margin_rate
    }


def build_channel_summary(
        forecast_df,
        start_date,
        end_date
):
    """
    Build summaries for the available channels.
    """

    channel_summary = {}

    for frontend_channel in [
        "Stores",
        "E-commerce",
        "SWS"
    ]:
        channel_df = filter_forecast_data(
            forecast_df,
            start_date,
            end_date,
            frontend_channel
        )

        summary = calculate_summary(
            channel_df
        )

        channel_summary[
            frontend_channel
        ] = {
            "forecastSales": (
                summary["forecastSales"]
            ),
            "forecastMargin": (
                summary["forecastMargin"]
            ),
            "marginRate": (
                summary["marginRate"]
            )
        }

    return channel_summary


# =========================================================
# Page routes
# =========================================================

@app.route("/")
@page_login_required
def home():
    return render_template(
        "index.html"
    )


@app.route("/login")
def login():
    if session.get("user_email"):
        return redirect(
            url_for("home")
        )

    return render_template(
        "login.html"
    )


@app.route("/register")
def register():
    if session.get("user_email"):
        return redirect(
            url_for("home")
        )

    return render_template(
        "register.html"
    )


@app.route("/verify")
def verify():
    if session.get("user_email"):
        return redirect(
            url_for("home")
        )

    if not session.get(
            "pending_verification_email"
    ):
        return redirect(
            url_for("register")
        )

    return render_template(
        "verify.html"
    )

@app.route("/forgot-password")
def forgot_password():
    if session.get("user_email"):
        return redirect(
            url_for("home")
        )

    return render_template(
        "forgot_password.html"
    )


@app.route("/reset-password")
def reset_password():
    if session.get("user_email"):
        return redirect(
            url_for("home")
        )

    if not session.get(
            "pending_password_reset_email"
    ):
        return redirect(
            url_for("forgot_password")
        )

    return render_template(
        "reset_password.html"
    )

# =========================================================
# Authentication API routes
# =========================================================

@app.route(
    "/api/register",
    methods=["POST"]
)
def api_register():
    """
    Register a user, save the account, and send a
    six-digit verification code to the authorized email.
    """

    data = request.get_json(
        silent=True
    ) or {}

    first_name = str(
        data.get("firstName", "")
    ).strip()

    last_name = str(
        data.get("lastName", "")
    ).strip()

    email = normalize_email(
        data.get("email", "")
    )

    password = str(
        data.get("password", "")
    )

    # -----------------------------------------------------
    # Validate submitted information
    # -----------------------------------------------------

    if not first_name:
        return jsonify({
            "error": "First name is required."
        }), 400

    if not last_name:
        return jsonify({
            "error": "Last name is required."
        }), 400

    if not email:
        return jsonify({
            "error": "Email is required."
        }), 400

    if not is_allowed_email(email):
        return jsonify({
            "error": (
                "Registration requires an "
                f"@{ALLOWED_EMAIL_DOMAIN} "
                "email address."
            )
        }), 400

    if not password_is_valid(password):
        return jsonify({
            "error": (
                "Password must contain at least "
                "8 characters, including uppercase, "
                "lowercase, and a number."
            )
        }), 400

    # -----------------------------------------------------
    # Create verification information
    # -----------------------------------------------------

    verification_code = (
        generate_verification_code()
    )

    verification_code_hash = (
        generate_password_hash(
            verification_code
        )
    )

    password_hash = (
        generate_password_hash(
            password
        )
    )

    verification_expires_at = (
            datetime.now()
            + timedelta(minutes=10)
    ).isoformat(
        timespec="seconds"
    )

    created_at = datetime.now().isoformat(
        timespec="seconds"
    )

    # -----------------------------------------------------
    # Save or update the user in SQLite
    # -----------------------------------------------------

    try:
        with get_database_connection() as connection:
            existing_user = connection.execute(
                """
                SELECT
                    id,
                    is_verified
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

            if (
                    existing_user
                    and existing_user["is_verified"]
            ):
                return jsonify({
                    "error": (
                        "An account already exists "
                        "for this email."
                    )
                }), 409

            if existing_user:
                connection.execute(
                    """
                    UPDATE users
                    SET
                        first_name = ?,
                        last_name = ?,
                        password_hash = ?,
                        is_verified = 0,
                        verification_code_hash = ?,
                        verification_expires_at = ?
                    WHERE email = ?
                    """,
                    (
                        first_name,
                        last_name,
                        password_hash,
                        verification_code_hash,
                        verification_expires_at,
                        email
                    )
                )

            else:
                connection.execute(
                    """
                    INSERT INTO users (
                        first_name,
                        last_name,
                        email,
                        password_hash,
                        is_verified,
                        verification_code_hash,
                        verification_expires_at,
                        created_at
                    )
                    VALUES (
                               ?, ?, ?, ?, 0, ?, ?, ?
                           )
                    """,
                    (
                        first_name,
                        last_name,
                        email,
                        password_hash,
                        verification_code_hash,
                        verification_expires_at,
                        created_at
                    )
                )

    except sqlite3.Error:
        app.logger.exception(
            "Unable to save the user account."
        )

        return jsonify({
            "error": (
                "The account could not be saved "
                "to the database."
            )
        }), 500

    # Save this before sending the email.
    # This allows the /verify page to recognize
    # which account is waiting for verification.
    session[
        "pending_verification_email"
    ] = email

    # -----------------------------------------------------
    # Send the verification email
    # -----------------------------------------------------

    try:
        send_verification_email(
            email,
            verification_code
        )

    except Exception:
        app.logger.exception(
            "Unable to send verification email."
        )

        return jsonify({
            "error": (
                "The account was saved, but the "
                "verification email could not be sent. "
                "Please check the Gmail App Password "
                "and email settings."
            ),
            "requiresVerification": True,
            "email": email
        }), 502

    return jsonify({
        "message": (
            "A verification code was sent "
            "to your email."
        ),
        "email": email
    }), 200


@app.route(
    "/api/verify",
    methods=["POST"]
)
def api_verify():
    """
    Validate the six-digit verification code and
    activate the user account.
    """

    data = request.get_json(
        silent=True
    ) or {}

    verification_code = str(
        data.get("code", "")
    ).strip()

    email = session.get(
        "pending_verification_email"
    )

    if not email:
        return jsonify({
            "error": (
                "No pending verification request "
                "was found. Please register again."
            )
        }), 400

    if (
            not verification_code.isdigit()
            or len(verification_code) != 6
    ):
        return jsonify({
            "error": (
                "Enter a valid 6-digit "
                "verification code."
            )
        }), 400

    try:
        with get_database_connection() as connection:
            user = connection.execute(
                """
                SELECT *
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

            if not user:
                return jsonify({
                    "error": "Account not found."
                }), 404

            if user["is_verified"]:
                session.pop(
                    "pending_verification_email",
                    None
                )

                return jsonify({
                    "message": (
                        "This account is already "
                        "verified."
                    )
                }), 200

            code_hash = user[
                "verification_code_hash"
            ]

            expiration_value = user[
                "verification_expires_at"
            ]

            if not code_hash or not expiration_value:
                return jsonify({
                    "error": (
                        "No active verification code "
                        "was found. Please request "
                        "a new code."
                    )
                }), 400

            expires_at = datetime.fromisoformat(
                expiration_value
            )

            if datetime.now() > expires_at:
                return jsonify({
                    "error": (
                        "The verification code has "
                        "expired. Please request "
                        "a new code."
                    )
                }), 400

            code_is_correct = check_password_hash(
                code_hash,
                verification_code
            )

            if not code_is_correct:
                return jsonify({
                    "error": (
                        "The verification code "
                        "is incorrect."
                    )
                }), 400

            connection.execute(
                """
                UPDATE users
                SET
                    is_verified = 1,
                    verification_code_hash = NULL,
                    verification_expires_at = NULL
                WHERE email = ?
                """,
                (email,)
            )

    except sqlite3.Error:
        app.logger.exception(
            "Unable to verify account."
        )

        return jsonify({
            "error": (
                "A database error occurred while "
                "verifying the account."
            )
        }), 500

    session.pop(
        "pending_verification_email",
        None
    )

    return jsonify({
        "message": (
            "Email verified successfully. "
            "You can now log in."
        )
    }), 200


@app.route(
    "/api/resend-code",
    methods=["POST"]
)
def api_resend_code():
    """
    Generate and send a new verification code.
    """

    email = session.get(
        "pending_verification_email"
    )

    if not email:
        return jsonify({
            "error": (
                "No pending verification request "
                "was found. Please register again."
            )
        }), 400

    verification_code = (
        generate_verification_code()
    )

    verification_code_hash = (
        generate_password_hash(
            verification_code
        )
    )

    verification_expires_at = (
            datetime.now()
            + timedelta(minutes=10)
    ).isoformat(
        timespec="seconds"
    )

    try:
        with get_database_connection() as connection:
            user = connection.execute(
                """
                SELECT
                    id,
                    is_verified
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

            if not user:
                return jsonify({
                    "error": "Account not found."
                }), 404

            if user["is_verified"]:
                return jsonify({
                    "error": (
                        "This account is already "
                        "verified."
                    )
                }), 400

            connection.execute(
                """
                UPDATE users
                SET
                    verification_code_hash = ?,
                    verification_expires_at = ?
                WHERE email = ?
                """,
                (
                    verification_code_hash,
                    verification_expires_at,
                    email
                )
            )

    except sqlite3.Error:
        app.logger.exception(
            "Unable to update verification code."
        )

        return jsonify({
            "error": (
                "The new verification code "
                "could not be saved."
            )
        }), 500

    try:
        send_verification_email(
            email,
            verification_code
        )

    except Exception:
        app.logger.exception(
            "Unable to resend verification email."
        )

        return jsonify({
            "error": (
                "The new code was created, but "
                "the email could not be sent. "
                "Please check the Gmail "
                "configuration."
            )
        }), 502

    return jsonify({
        "message": (
            "A new verification code "
            "was sent."
        )
    }), 200

@app.route(
    "/api/forgot-password",
    methods=["POST"]
)
def api_forgot_password():
    """
    Generate and send a password reset code.
    """

    data = request.get_json(
        silent=True
    ) or {}

    email = normalize_email(
        data.get("email", "")
    )

    if not email:
        return jsonify({
            "error": "Email is required."
        }), 400

    if not is_allowed_email(email):
        return jsonify({
            "error": (
                "Please use an authorized "
                f"@{ALLOWED_EMAIL_DOMAIN} "
                "email address."
            )
        }), 400

    try:
        with get_database_connection() as connection:
            user = connection.execute(
                """
                SELECT
                    id,
                    email,
                    is_verified
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

            if not user:
                return jsonify({
                    "error": (
                        "No account was found "
                        "for this email address."
                    )
                }), 404

            if not user["is_verified"]:
                return jsonify({
                    "error": (
                        "This account has not been "
                        "verified yet."
                    )
                }), 403

            reset_code = (
                generate_verification_code()
            )

            reset_code_hash = (
                generate_password_hash(
                    reset_code
                )
            )

            reset_expires_at = (
                    datetime.now()
                    + timedelta(minutes=10)
            ).isoformat(
                timespec="seconds"
            )

            connection.execute(
                """
                UPDATE users
                SET
                    reset_code_hash = ?,
                    reset_expires_at = ?
                WHERE email = ?
                """,
                (
                    reset_code_hash,
                    reset_expires_at,
                    email
                )
            )

    except sqlite3.Error:
        app.logger.exception(
            "Unable to create password reset request."
        )

        return jsonify({
            "error": (
                "A database error occurred while "
                "creating the password reset request."
            )
        }), 500

    session[
        "pending_password_reset_email"
    ] = email

    try:
        send_password_reset_email(
            email,
            reset_code
        )

    except Exception:
        app.logger.exception(
            "Unable to send password reset email."
        )

        return jsonify({
            "error": (
                "The reset code was created, but "
                "the email could not be sent. "
                "Please check the Gmail settings."
            )
        }), 502

    return jsonify({
        "message": (
            "A password reset code was sent "
            "to your email."
        )
    }), 200

@app.route(
    "/api/reset-password",
    methods=["POST"]
)
def api_reset_password():
    """
    Validate the reset code and update the password.
    """

    data = request.get_json(
        silent=True
    ) or {}

    reset_code = str(
        data.get("code", "")
    ).strip()

    new_password = str(
        data.get("password", "")
    )

    email = session.get(
        "pending_password_reset_email"
    )

    if not email:
        return jsonify({
            "error": (
                "No password reset request was found. "
                "Please request a new code."
            )
        }), 400

    if (
            not reset_code.isdigit()
            or len(reset_code) != 6
    ):
        return jsonify({
            "error": (
                "Enter a valid 6-digit reset code."
            )
        }), 400

    if not password_is_valid(new_password):
        return jsonify({
            "error": (
                "Password must contain at least "
                "8 characters, including uppercase, "
                "lowercase, and a number."
            )
        }), 400

    try:
        with get_database_connection() as connection:
            user = connection.execute(
                """
                SELECT *
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

            if not user:
                return jsonify({
                    "error": "Account not found."
                }), 404

            reset_code_hash = user[
                "reset_code_hash"
            ]

            reset_expiration = user[
                "reset_expires_at"
            ]

            if (
                    not reset_code_hash
                    or not reset_expiration
            ):
                return jsonify({
                    "error": (
                        "No active password reset "
                        "code was found."
                    )
                }), 400

            expires_at = datetime.fromisoformat(
                reset_expiration
            )

            if datetime.now() > expires_at:
                return jsonify({
                    "error": (
                        "The password reset code has "
                        "expired. Please request "
                        "a new code."
                    )
                }), 400

            code_is_correct = (
                check_password_hash(
                    reset_code_hash,
                    reset_code
                )
            )

            if not code_is_correct:
                return jsonify({
                    "error": (
                        "The password reset code "
                        "is incorrect."
                    )
                }), 400

            new_password_hash = (
                generate_password_hash(
                    new_password
                )
            )

            connection.execute(
                """
                UPDATE users
                SET
                    password_hash = ?,
                    reset_code_hash = NULL,
                    reset_expires_at = NULL
                WHERE email = ?
                """,
                (
                    new_password_hash,
                    email
                )
            )

    except (
            sqlite3.Error,
            ValueError,
            TypeError
    ):
        app.logger.exception(
            "Unable to reset password."
        )

        return jsonify({
            "error": (
                "An error occurred while "
                "resetting the password."
            )
        }), 500

    session.pop(
        "pending_password_reset_email",
        None
    )

    return jsonify({
        "message": (
            "Your password was reset successfully."
        )
    }), 200

@app.route(
    "/api/login",
    methods=["POST"]
)
def api_login():
    """
    Log in a verified user and create a Flask session.
    """

    data = request.get_json(
        silent=True
    ) or {}

    email = normalize_email(
        data.get("email", "")
    )

    password = str(
        data.get("password", "")
    )

    if not email or not password:
        return jsonify({
            "error": (
                "Email and password are required."
            )
        }), 400

    if not is_allowed_email(email):
        return jsonify({
            "error": (
                "Please use an authorized "
                f"@{ALLOWED_EMAIL_DOMAIN} "
                "email address."
            )
        }), 403

    try:
        with get_database_connection() as connection:
            user = connection.execute(
                """
                SELECT *
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

    except sqlite3.Error:
        app.logger.exception(
            "Unable to read the user account."
        )

        return jsonify({
            "error": (
                "A database error occurred "
                "while logging in."
            )
        }), 500

    if not user:
        return jsonify({
            "error": (
                "Incorrect email or password."
            )
        }), 401

    if not user["is_verified"]:
        session[
            "pending_verification_email"
        ] = email

        return jsonify({
            "error": (
                "Please verify your email "
                "before logging in."
            ),
            "requiresVerification": True
        }), 403

    password_is_correct = (
        check_password_hash(
            user["password_hash"],
            password
        )
    )

    if not password_is_correct:
        return jsonify({
            "error": (
                "Incorrect email or password."
            )
        }), 401

    session.clear()

    session["user_email"] = user["email"]

    session["user_name"] = (
        f"{user['first_name']} "
        f"{user['last_name']}"
    )

    return jsonify({
        "message": "Login successful.",
        "user": {
            "email": user["email"],
            "firstName": user["first_name"],
            "lastName": user["last_name"]
        }
    }), 200


@app.route(
    "/api/logout",
    methods=["POST"]
)
def api_logout():
    """
    Clear the authenticated user session.
    """

    session.clear()

    return jsonify({
        "message": "Logout successful."
    }), 200


@app.route(
    "/api/session",
    methods=["GET"]
)
def api_session():
    """
    Return the current login status.
    """

    user_email = session.get(
        "user_email"
    )

    if not user_email:
        return jsonify({
            "authenticated": False
        }), 200

    return jsonify({
        "authenticated": True,
        "email": user_email,
        "name": session.get(
            "user_name"
        )
    }), 200

# =========================================================
# Forecast API routes
# =========================================================

@app.route(
    "/api/health",
    methods=["GET"]
)
def health():
    return jsonify({
        "status": "ok",
        "message": (
            "JBS Swift Forecast API is running"
        ),
        "forecastFileExists": (
            FORECAST_FILE.exists()
        ),
        "databaseFileExists": (
            DATABASE_FILE.exists()
        ),
        "allowedEmailDomain": (
            ALLOWED_EMAIL_DOMAIN
        ),
        "mailConfigured": bool(
            app.config["MAIL_USERNAME"]
            and app.config["MAIL_PASSWORD"]
        )
    }), 200


@app.route(
    "/api/data-range",
    methods=["GET"]
)
@api_login_required
def data_range():
    """
    Return the available forecast date range.
    """

    try:
        forecast_df = load_forecast_data()

        return jsonify({
            "startDate": (
                forecast_df["date"]
                .min()
                .strftime("%Y-%m-%d")
            ),
            "endDate": (
                forecast_df["date"]
                .max()
                .strftime("%Y-%m-%d")
            ),
            "channels": (
                ["All Channels"]
                + forecast_df["channel"]
                .dropna()
                .astype(str)
                .drop_duplicates()
                .tolist()
            )
        }), 200

    except (
            FileNotFoundError,
            ValueError
    ) as error:
        return jsonify({
            "error": str(error)
        }), 500

    except Exception:
        app.logger.exception(
            "Unable to load data range."
        )

        return jsonify({
            "error": (
                "An unexpected error occurred "
                "while loading the data range."
            )
        }), 500


@app.route(
    "/api/dashboard",
    methods=["GET"]
)
@api_login_required
def dashboard():
    """
    Return dashboard summary and channel metrics.
    """

    filters, error_response = parse_filters()

    if error_response:
        return error_response

    try:
        forecast_df = load_forecast_data()

        filtered_df = filter_forecast_data(
            forecast_df,
            filters["start_date"],
            filters["end_date"],
            filters["channel"]
        )

        selected_summary = calculate_summary(
            filtered_df
        )

        channel_summary = build_channel_summary(
            forecast_df,
            filters["start_date"],
            filters["end_date"]
        )

        return jsonify({
            "filters": {
                "startDate": (
                    filters["start_date"]
                    .strftime("%Y-%m-%d")
                ),
                "endDate": (
                    filters["end_date"]
                    .strftime("%Y-%m-%d")
                ),
                "channel": filters["channel"]
            },
            "summary": selected_summary,
            "channels": channel_summary,
            "recordCount": int(
                len(filtered_df)
            ),
            "lastUpdated": (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )
        }), 200

    except (
            FileNotFoundError,
            ValueError
    ) as error:
        return jsonify({
            "error": str(error)
        }), 500

    except Exception:
        app.logger.exception(
            "Unable to load dashboard data."
        )

        return jsonify({
            "error": (
                "An unexpected error occurred "
                "while loading dashboard data."
            )
        }), 500


@app.route(
    "/api/forecast-results",
    methods=["GET"]
)
@api_login_required
def forecast_results():
    """
    Return daily forecast results.
    """

    filters, error_response = parse_filters()

    if error_response:
        return error_response

    try:
        forecast_df = load_forecast_data()

        filtered_df = filter_forecast_data(
            forecast_df,
            filters["start_date"],
            filters["end_date"],
            filters["channel"]
        )

        filtered_df = filtered_df.sort_values(
            [
                "date",
                "channel"
            ]
        )

        rows = []

        for _, row in filtered_df.iterrows():
            display_channel = (
                "SWS"
                if row["channel"]
                   == "Store-within-Store"
                else row["channel"]
            )

            sales = float(
                row["predicted_sales"]
            )

            margin = float(
                row["predicted_margin"]
            )

            if sales != 0:
                margin_rate = margin / sales
            else:
                margin_rate = 0

            rows.append({
                "date": (
                    row["date"].strftime(
                        "%Y-%m-%d"
                    )
                ),
                "channel": display_channel,
                "forecastSales": (
                    format_currency(sales)
                ),
                "forecastMargin": (
                    format_currency(margin)
                ),
                "marginRate": (
                    format_percentage(
                        margin_rate
                    )
                ),
                "forecastSalesRaw": sales,
                "forecastMarginRaw": margin,
                "marginRateRaw": margin_rate
            })

        return jsonify({
            "filters": {
                "startDate": (
                    filters["start_date"]
                    .strftime("%Y-%m-%d")
                ),
                "endDate": (
                    filters["end_date"]
                    .strftime("%Y-%m-%d")
                ),
                "channel": filters["channel"]
            },
            "rows": rows,
            "recordCount": len(rows)
        }), 200

    except (
            FileNotFoundError,
            ValueError
    ) as error:
        return jsonify({
            "error": str(error)
        }), 500

    except Exception:
        app.logger.exception(
            "Unable to load forecast results."
        )

        return jsonify({
            "error": (
                "An unexpected error occurred "
                "while loading forecast results."
            )
        }), 500
# =========================================================
# Run application
# =========================================================

@app.route(
    "/api/margin-dashboard",
    methods=["GET"]
)
@api_login_required
def margin_dashboard():
    """Return summaries and chart data from the margin-only CSV."""

    filters, error_response = parse_filters()
    if error_response:
        return error_response

    try:
        forecast_df = load_forecast_data()
        filtered_df = filter_forecast_data(
            forecast_df,
            filters["start_date"],
            filters["end_date"],
            filters["channel"]
        ).sort_values(["date", "channel"])

        total_margin = float(filtered_df["predicted_margin"].sum())
        average_margin = (
            float(filtered_df["predicted_margin"].mean())
            if len(filtered_df) else 0.0
        )
        peak_margin = (
            float(filtered_df["predicted_margin"].max())
            if len(filtered_df) else 0.0
        )

        channel_rows = []
        available_channels = (
            forecast_df["channel"]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .tolist()
        )
        for channel_name in available_channels:
            channel_df = filtered_df[
                filtered_df["channel"] == channel_name
            ]
            channel_rows.append({
                "channel": channel_name,
                "totalMargin": float(channel_df["predicted_margin"].sum()),
                "averageMargin": (
                    float(channel_df["predicted_margin"].mean())
                    if len(channel_df) else 0.0
                ),
                "recordCount": int(len(channel_df))
            })

        daily_rows = []
        for _, row in filtered_df.iterrows():
            daily_rows.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "channel": row["channel"],
                "predictedMargin": float(row["predicted_margin"]),
                "forecastOrigin": str(row["forecast_origin"]),
                "forecastHorizonDay": int(row["forecast_horizon_day"]),
                "forecastMode": str(row["forecast_mode"]),
                "modelName": str(row["model_name"]),
                "featureSet": str(row["feature_set"]),
                "weatherFeatureSource": str(row["weather_feature_source"]),
                "actualMarginAvailable": bool(
                    int(row["actual_margin_available_flag"])
                )
            })

        return jsonify({
            "filters": {
                "startDate": filters["start_date"].strftime("%Y-%m-%d"),
                "endDate": filters["end_date"].strftime("%Y-%m-%d"),
                "channel": filters["channel"]
            },
            "summary": {
                "totalMargin": total_margin,
                "averageMargin": average_margin,
                "peakMargin": peak_margin,
                "recordCount": int(len(filtered_df))
            },
            "channels": channel_rows,
            "rows": daily_rows,
            "lastUpdated": datetime.now().isoformat(timespec="seconds")
        }), 200

    except (FileNotFoundError, ValueError) as error:
        return jsonify({"error": str(error)}), 500
    except Exception:
        app.logger.exception("Unable to load recursive margin dashboard.")
        return jsonify({
            "error": "Unable to load recursive margin forecast data."
        }), 500


@app.route("/api/test-email")
@api_login_required
def test_email():
    try:
        message = Message(
            subject="JBS SMTP Test",
            recipients=[
                app.config["MAIL_USERNAME"]
            ],
            body=(
                "This is a Gmail SMTP test "
                "from the JBS Forecast Portal."
            )
        )

        mail.send(message)

        return jsonify({
            "status": "ok",
            "message": "Test email sent."
        })

    except Exception as error:
        app.logger.exception(
            "Test email failed."
        )

        return jsonify({
            "status": "error",
            "error": "Unable to send the test email. Check the mail configuration."
        }), 500
if __name__ == "__main__":
    app.run(
        debug=(
            os.getenv("FLASK_DEBUG", "false")
            .strip()
            .lower() == "true"
        )
    )
