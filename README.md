# Student Database Management System

Full-stack academic management application using Python, Flask and MySQL.

## Features
- Authentication with password hashing
- Role-based authorization: admin, faculty, student
- Student CRUD operations
- Course/department data
- Attendance and grades views
- Dashboard statistics and student search
- REST API: `/api/students`
- Relational MySQL schema with primary/foreign keys

## Setup
1. Install Python 3.10+ and MySQL 8+.
2. `python -m venv venv`
3. Activate the environment.
4. `pip install -r requirements.txt`
5. Run `mysql -u root -p < database/schema.sql`
6. Copy `.env.example` to `.env` and set your MySQL password.
7. Generate a password hash: `python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('Admin@123'))"`
8. In MySQL, insert the hash: `INSERT INTO users(name,email,password_hash,role) VALUES ('Admin','admin@example.com','PASTE_HASH_HERE','admin');`
9. Run `python app.py`
10. Open `http://127.0.0.1:5000`

## Architecture
Browser → Flask routes/API → database logic → MySQL → HTML/JSON response.

## Interview concepts
CRUD, SQL JOINs, primary/foreign keys, normalization, constraints, transactions, authentication, authorization, REST APIs and relational database design.

## Planned next upgrades
Add faculty CRUD, attendance/grade entry forms, student-specific dashboards, pagination, validation, CSRF protection, Flask blueprints, tests and deployment.
