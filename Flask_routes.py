from flask import Flask, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from Model import TaskManager
from Tables import sessionLocal, Employee, Admin, TokenBlacklist
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt, get_jwt_identity
from datetime import timedelta, datetime, UTC
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"])
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
jwt = JWTManager(app)

@app.errorhandler(400)
def bad_request(e):
    return jsonify({"message": "Bad request — check your input"}), 400

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({"message": "Unauthorized — please login"}), 401

@app.errorhandler(404)
def not_found(e):
    return jsonify({"message": "Route not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"message": "Method not allowed"}), 405

@app.errorhandler(422)
def unprocessable(e):
    return jsonify({"message": "Invalid input data"}), 422

@app.errorhandler(500)
def server_error(e):
    return jsonify({"message": "Internal server error"}), 500

bc = Bcrypt(app)
taskk = TaskManager()

def get_db():
    if "db" not in g:
        g.db = sessionLocal()
    return g.db


VALID_STATUSES   = {"pending", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}

def validate_task(title, priority, status=None):
    errors = []
    if not title or not isinstance(title, str) or not title.strip():
        errors.append("Title cannot be empty")
    if priority and priority not in VALID_PRIORITIES:
        errors.append(f"Priority must be one of: {', '.join(VALID_PRIORITIES)}")
    if status and status not in VALID_STATUSES:
        errors.append(f"Status must be one of: {', '.join(VALID_STATUSES)}")
    return errors


@app.route("/api/v1/register_employee", methods=["POST"])
@limiter.limit("5 per minute")
def register_employee():
    if not request.json:
        return jsonify({"message": "Request body must be JSON"}), 400
    email    = request.json.get("email")
    password = request.json.get("password")
    try:
        db = get_db()
        if not email or not password:
            return jsonify({"message": "Missing Fields"}), 409
        existing = db.query(Employee).filter(Employee.email == email).first()
        if existing:
            return jsonify({"message": "Email Already Exists"}), 409
        hashed   = bc.generate_password_hash(password).decode("utf-8")
        employee = Employee(email=email, password=hashed)
        db.add(employee)
        db.commit()
        return jsonify({"message": "Registered Successfully"}), 201
    except Exception as e:
        return jsonify({"message": f"Server error {str(e)}"}), 500

@app.route("/api/v1/register_admin", methods=["POST"])
@limiter.limit("5 per minute")
def register_admin():
    if not request.json:
        return jsonify({"message": "Request body must be JSON"}), 400
    email    = request.json.get("email")
    password = request.json.get("password")
    try:
        db = get_db()
        if not email or not password:
            return jsonify({"message": "Missing Fields"}), 409
        existing = db.query(Admin).filter(Admin.email == email).first()
        if existing:
            return jsonify({"message": "Email Already Exists"}), 409
        hashed = bc.generate_password_hash(password).decode("utf-8")
        admin  = Admin(email=email, password=hashed)
        db.add(admin)
        db.commit()
        return jsonify({"message": "Registered Successfully"}), 201
    except Exception as e:
        return jsonify({"message": f"Server error {str(e)}"}), 500

@app.route("/api/v1/login_employee", methods=["POST"])
@limiter.limit("3 per minute")
def login_employee():
    if not request.json:
        return jsonify({"message": "Request body must be JSON"}), 400
    email    = request.json.get("email")
    password = request.json.get("password")
    try:
        db   = get_db()
        empl = db.query(Employee).filter(Employee.email == email).first()
        if not empl or not bc.check_password_hash(empl.password, password):
            return jsonify({"message": "Invalid Login attempt"}), 401
        token = create_access_token(identity=str(empl.id), additional_claims={"role": "employee"})
        return jsonify({"token": token}), 200
    except Exception as e:
        return jsonify({"message": f"Server error {str(e)}"}), 500

@app.route("/api/v1/login_admin", methods=["POST"])
@limiter.limit("3 per minute")
def login_admin():
    if not request.json:
        return jsonify({"message": "Request body must be JSON"}), 400
    email    = request.json.get("email")
    password = request.json.get("password")
    try:
        db    = get_db()
        admin = db.query(Admin).filter(Admin.email == email).first()
        if not admin or not bc.check_password_hash(admin.password, password):
            return jsonify({"message": "Invalid Login attempt"}), 401
        token = create_access_token(identity=str(admin.id), additional_claims={"role": "admin"})
        return jsonify({"token": token}), 200
    except Exception as e:
        return jsonify({"message": f"Server error {str(e)}"}), 500

@jwt.token_in_blocklist_loader
def check_blacklisted_token(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    db  = get_db()
    return db.query(TokenBlacklist).filter_by(jti=jti).first() is not None

@app.route("/api/v1/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    try:
        db = get_db()
        db.add(TokenBlacklist(jti=jti, created_at=str(datetime.now(UTC))))
        db.commit()
        return jsonify({"message": "Logged out successfully"}), 200
    except Exception as e:
        return jsonify({"message": f"Server error {str(e)}"}), 500


@app.route("/api/v1/tasks", methods=["POST"])
@jwt_required()
def create_task():
    claims = get_jwt()
    if claims["role"] != "employee":
        return jsonify({"message": "Unauthorized"}), 401
    if not request.json:
        return jsonify({"message": "Request body must be JSON"}), 400
    title       = request.json.get("title")
    description = request.json.get("description")
    priority    = request.json.get("priority", "medium")
    due_date    = request.json.get("due_date")
    errors = validate_task(title, priority)
    if errors:
        return jsonify({"errors": errors}), 422
    owner_id = int(get_jwt_identity())
    data, status = taskk.create_task(title, description, priority, due_date, owner_id)
    return jsonify(data), status

@app.route("/api/v1/tasks", methods=["GET"])
@jwt_required()
def get_all_tasks():
    claims = get_jwt()
    if claims["role"] != "admin":
        return jsonify({"message": "Unauthorized"}), 401
    data, status = taskk.get_all_tasks()
    return jsonify(data), status

@app.route("/api/v1/my_tasks", methods=["GET"])
@jwt_required()
def get_my_tasks():
    claims = get_jwt()
    if claims["role"] != "employee":
        return jsonify({"message": "Unauthorized"}), 401
    owner_id     = int(get_jwt_identity())
    data, status = taskk.get_my_tasks(owner_id)
    return jsonify(data), status


@app.route("/api/v1/tasks/filter", methods=["GET"])
@jwt_required()
def filter_tasks():
    claims     = get_jwt()
    is_admin   = claims["role"] == "admin"
    owner_id   = int(get_jwt_identity())
    status_val = request.args.get("status")
    priority   = request.args.get("priority")
    data, status = taskk.filter_tasks(owner_id, is_admin, status_val, priority)
    return jsonify(data), status

@app.route("/api/v1/tasks/<int:task_id>", methods=["GET"])
@jwt_required()
def get_task(task_id):
    claims   = get_jwt()
    is_admin = claims["role"] == "admin"
    owner_id = int(get_jwt_identity())
    data, status = taskk.get_task_by_id(task_id)
    if status == 200 and not is_admin and data.get("owner_id") != owner_id:
        return jsonify({"message": "Unauthorized"}), 401
    return jsonify(data), status

@app.route("/api/v1/tasks/<int:task_id>", methods=["PUT"])
@jwt_required()
def update_task(task_id):
    if not request.json:
        return jsonify({"message": "Request body must be JSON"}), 400
    claims   = get_jwt()
    is_admin = claims["role"] == "admin"
    owner_id = int(get_jwt_identity())
    title       = request.json.get("title")
    description = request.json.get("description")
    status_val  = request.json.get("status")
    priority    = request.json.get("priority")
    due_date    = request.json.get("due_date")
    errors = validate_task(title or "placeholder", priority, status_val)
    if errors:
        return jsonify({"errors": errors}), 422
    data, status = taskk.update_task(task_id, owner_id, is_admin, title, description, status_val, priority, due_date)
    return jsonify(data), status

@app.route("/api/v1/tasks/<int:task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(task_id):
    claims   = get_jwt()
    is_admin = claims["role"] == "admin"
    owner_id = int(get_jwt_identity())
    data, status = taskk.delete_task(task_id, owner_id, is_admin)
    return jsonify(data), status


@app.teardown_appcontext
def db_close(exception=None):
    db = g.pop("db", None)
    if db is not None:
        if exception:
            db.rollback()
        db.close()

if __name__ == "__main__":
    app.run(debug=True)
