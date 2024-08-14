import os
import json
import random
import string
import base64
import psycopg
from flask import Flask, request, jsonify

app = Flask(__name__)

hostname = "YOUR_VM_IP"

db_admin_user = "postgres"
db_admin_password = "dummy_password"

username_required = "svc_impaas_postgres"
password_required = "super_secure_password"


def authenticate_request(auth_header):
    if auth_header and auth_header.startswith("Basic "):
        encoded_credentials = auth_header[len("Basic ") :]
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded_credentials.split(":", 1)
        return username == username_required and password == password_required
    return False


def get_db_connection(database=None):
    return psycopg.connect(
        host="localhost",
        user=db_admin_user,
        password=db_admin_password,
        dbname=database,
    )


def execute_sql_command(command, database=None):
    try:
        conn = get_db_connection(database)
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(command)
        cursor.close()
        conn.close()
    except psycopg.Error as e:
        raise e


@app.route("/resources/plans", methods=["GET"])
def plans():
    plans = [{"name": "Database", "description": "A Postgres database instance"}]
    return jsonify(plans)


@app.route("/resources", methods=["POST"])
def add_instance():
    auth_header = request.headers.get("Authorization")
    if not authenticate_request(auth_header):
        return "Incorrect credentials provided\n", 400

    name = request.form.get("name")
    if not name:
        return "No database name provided\n", 400

    try:
        execute_sql_command(f"CREATE DATABASE {name}")
    except psycopg.Error as e:
        return str(e), 400

    return f"The Database: {name} has been created!", 201


@app.route("/resources/<name>/bind-app", methods=["POST"])
def bind_app(name):
    auth_header = request.headers.get("Authorization")
    if not authenticate_request(auth_header):
        return "Incorrect credentials provided\n", 400

    app_name = request.form.get("app-name")
    if not app_name:
        return "No app-name provided\n", 400

    new_username = (name + app_name).replace("-", "_")[:31]
    new_user_password = app_name + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=5)
    )

    try:
        execute_sql_command(
            f"CREATE USER {new_username} WITH PASSWORD '{new_user_password}'"
        )
        execute_sql_command(
            f"GRANT ALL PRIVILEGES ON DATABASE {name} TO {new_username}"
        )
        execute_sql_command(
            f"GRANT ALL ON SCHEMA public TO {new_username}", database=name
        )
    except psycopg.Error as e:
        return str(e), 400

    envs = {
        "PGPORT": "5432",
        "PGPASSWORD": new_user_password,
        "PGUSER": new_username,
        "PGHOST": hostname,
        "PGDATABASE": name,
    }

    return jsonify(envs), 201


@app.route("/resources/<name>/bind-app", methods=["DELETE"])
def unbind_app(name):
    auth_header = request.headers.get("Authorization")
    if not authenticate_request(auth_header):
        return "Incorrect credentials provided\n", 400

    app_name = request.form.get("app-name")
    if not app_name:
        return "No app-name provided\n", 400

    user_to_delete = (name + app_name).replace("-", "_")[:31]

    try:
        execute_sql_command(
            f"REASSIGN OWNED BY {user_to_delete} TO {db_admin_user}", database=name
        )
        execute_sql_command(f"DROP OWNED BY {user_to_delete} CASCADE", database=name)
        execute_sql_command(f"DROP USER IF EXISTS {user_to_delete}")
    except psycopg.Error as e:
        return str(e), 400

    return f"{user_to_delete} has been removed; application unbound", 200


@app.route("/resources/<name>", methods=["DELETE"])
def remove_instance(name):
    auth_header = request.headers.get("Authorization")
    if not authenticate_request(auth_header):
        return "Incorrect credentials provided\n", 400

    try:
        execute_sql_command(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
    except psycopg.Error as e:
        return str(e), 400

    return f"Database: {name} has been deleted", 200


@app.route("/resources/<name>/bind", methods=["POST", "DELETE"])
def access_control(name):
    return "Server does not support this operation", 400


@app.route("/resources/<name>/status", methods=["GET"])
def status(name):
    return "Server does not support this operation", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 4999)))
