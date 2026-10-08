import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
import mysql.connector
from dotenv import load_dotenv
from functools import wraps

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-this-secret-key')

def get_db():
    return mysql.connector.connect(host=os.getenv('DB_HOST','localhost'), user=os.getenv('DB_USER','root'), password=os.getenv('DB_PASSWORD',''), database=os.getenv('DB_NAME','student_management'))

def login_required(f):
    @wraps(f)
    def w(*a, **kw):
        if 'user_id' not in session:
            flash('Please login first.','warning'); return redirect(url_for('login'))
        return f(*a, **kw)
    return w

def role_required(*roles):
    def deco(f):
        @wraps(f)
        def w(*a, **kw):
            if session.get('role') not in roles:
                flash('You are not authorized for this action.','danger'); return redirect(url_for('dashboard'))
            return f(*a, **kw)
        return w
    return deco

@app.route('/')
def index(): return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        selected_role = request.form['role']

        db = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute(
            'SELECT * FROM users WHERE email=%s',
            (email,)
        )

        user = cur.fetchone()

        cur.close()
        db.close()

        if user and check_password_hash(user['password_hash'], password):

            if user['role'] != selected_role:
                flash('Selected role does not match this account.', 'danger')
                return render_template('login.html')

            session.update(
                user_id=user['id'],
                name=user['name'],
                role=user['role'],
                email=user['email']
            )

            return redirect(url_for('dashboard'))

        flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    db=get_db(); cur=db.cursor(dictionary=True); counts={}
    for table in ('students','faculty','courses'):
        cur.execute(f'SELECT COUNT(*) total FROM {table}'); counts[table]=cur.fetchone()['total']
    cur.execute('SELECT s.id,s.name,s.email,d.name department FROM students s LEFT JOIN departments d ON s.department_id=d.id ORDER BY s.id DESC LIMIT 5'); recent=cur.fetchall()
    cur.close(); db.close(); return render_template('dashboard.html',counts=counts,recent_students=recent)

@app.route('/students')
@login_required
def students():
    q=request.args.get('q','').strip(); db=get_db(); cur=db.cursor(dictionary=True)
    sql='SELECT s.*,d.name department,c.name course FROM students s LEFT JOIN departments d ON s.department_id=d.id LEFT JOIN courses c ON s.course_id=c.id'; params=()
    if q: sql+=' WHERE s.name LIKE %s OR s.email LIKE %s OR s.student_number LIKE %s'; like=f'%{q}%'; params=(like,like,like)
    cur.execute(sql+' ORDER BY s.id DESC',params); rows=cur.fetchall(); cur.close(); db.close(); return render_template('students.html',students=rows,q=q)

@app.route('/students/add',methods=['GET','POST'])
@login_required
@role_required('admin')
def add_student():
    db=get_db(); cur=db.cursor(dictionary=True); cur.execute('SELECT id,name FROM departments ORDER BY name'); departments=cur.fetchall(); cur.execute('SELECT id,name FROM courses ORDER BY name'); courses=cur.fetchall()
    if request.method=='POST':
        d=request.form
        try:
            cur.execute('INSERT INTO students(student_number,name,email,phone,date_of_birth,gender,department_id,course_id,year_of_study) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(d['student_number'],d['name'],d['email'],d['phone'],d['date_of_birth'] or None,d['gender'],d['department_id'] or None,d['course_id'] or None,d['year_of_study']))
            db.commit(); flash('Student added successfully.','success'); return redirect(url_for('students'))
        except mysql.connector.Error as e: db.rollback(); flash(f'Could not add student: {e}','danger')
    cur.close(); db.close(); return render_template('student_form.html',departments=departments,courses=courses,student=None)

@app.route('/students/edit/<int:id>',methods=['GET','POST'])
@login_required
@role_required('admin')
def edit_student(id):
    db=get_db(); cur=db.cursor(dictionary=True); cur.execute('SELECT * FROM students WHERE id=%s',(id,)); student=cur.fetchone()
    if not student: cur.close(); db.close(); return 'Student not found',404
    cur.execute('SELECT id,name FROM departments ORDER BY name'); departments=cur.fetchall(); cur.execute('SELECT id,name FROM courses ORDER BY name'); courses=cur.fetchall()
    if request.method=='POST':
        d=request.form; cur.execute('UPDATE students SET student_number=%s,name=%s,email=%s,phone=%s,date_of_birth=%s,gender=%s,department_id=%s,course_id=%s,year_of_study=%s WHERE id=%s',(d['student_number'],d['name'],d['email'],d['phone'],d['date_of_birth'] or None,d['gender'],d['department_id'] or None,d['course_id'] or None,d['year_of_study'],id)); db.commit(); cur.close(); db.close(); flash('Student updated.','success'); return redirect(url_for('students'))
    cur.close(); db.close(); return render_template('student_form.html',departments=departments,courses=courses,student=student)

@app.route('/students/delete/<int:id>',methods=['POST'])
@login_required
@role_required('admin')
def delete_student(id):
    db=get_db(); cur=db.cursor()
    try: cur.execute('DELETE FROM students WHERE id=%s',(id,)); db.commit(); flash('Student deleted.','success')
    except mysql.connector.Error as e: db.rollback(); flash(f'Delete failed: {e}','danger')
    cur.close(); db.close(); return redirect(url_for('students'))

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == 'POST':
        student_id = request.form['student_id']
        course_id = request.form['course_id']
        attendance_date = request.form['attendance_date']
        status = request.form['status']

        try:
            cur.execute(
                '''INSERT INTO attendance
                   (student_id, course_id, attendance_date, status)
                   VALUES (%s, %s, %s, %s)''',
                (student_id, course_id, attendance_date, status)
            )
            db.commit()
            flash('Attendance added successfully.', 'success')
        except mysql.connector.Error as e:
            db.rollback()
            flash(f'Could not add attendance: {e}', 'danger')

        cur.close()
        db.close()
        return redirect(url_for('attendance'))

    cur.execute(
        'SELECT id, student_number, name FROM students ORDER BY name'
    )
    students_list = cur.fetchall()

    cur.execute(
        'SELECT id, name FROM courses ORDER BY name'
    )
    courses_list = cur.fetchall()

    cur.execute(
        '''SELECT a.id,
                  s.student_number,
                  s.name,
                  c.name course,
                  a.attendance_date,
                  a.status
           FROM attendance a
           JOIN students s ON a.student_id = s.id
           JOIN courses c ON a.course_id = c.id
           ORDER BY a.attendance_date DESC, a.id DESC'''
    )
    rows = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        'attendance.html',
        attendance=rows,
        students=students_list,
        courses=courses_list
    )
@app.route('/courses')
@login_required
def courses():
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute(
        """SELECT c.*,
                  d.name department,
                  (SELECT COUNT(*)
                   FROM students s
                   WHERE s.course_id = c.id) student_count
           FROM courses c
           LEFT JOIN departments d
           ON c.department_id = d.id
           ORDER BY c.id DESC"""
    )

    rows = cur.fetchall()

    cur.close()
    db.close()

    return render_template('courses.html', courses=rows)


@app.route('/grades', methods=['GET', 'POST'])
@login_required
def grades():
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == 'POST':
        student_id = request.form['student_id']
        course_id = request.form['course_id']
        exam_type = request.form['exam_type']
        marks = request.form['marks']
        max_marks = request.form['max_marks']

        try:
            cur.execute(
                '''INSERT INTO grades
                   (student_id, course_id, exam_type, marks, max_marks)
                   VALUES (%s, %s, %s, %s, %s)''',
                (student_id, course_id, exam_type, marks, max_marks)
            )

            db.commit()
            flash('Grade added successfully.', 'success')

        except mysql.connector.Error as e:
            db.rollback()
            flash(f'Could not add grade: {e}', 'danger')

        cur.close()
        db.close()

        return redirect(url_for('grades'))

    cur.execute(
        'SELECT id, student_number, name FROM students ORDER BY name'
    )
    students_list = cur.fetchall()

    cur.execute(
        'SELECT id, name FROM courses ORDER BY name'
    )
    courses_list = cur.fetchall()

    cur.execute(
        '''SELECT g.id,
                  s.student_number,
                  s.name,
                  c.name course,
                  g.exam_type,
                  g.marks,
                  g.max_marks
           FROM grades g
           JOIN students s ON g.student_id = s.id
           JOIN courses c ON g.course_id = c.id
           ORDER BY g.id DESC'''
    )

    rows = cur.fetchall()

    cur.close()
    db.close()

    return render_template(
        'grades.html',
        grades=rows,
        students=students_list,
        courses=courses_list
    )


@app.route('/reports')
@login_required
def reports():
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute(
        '''SELECT
               s.student_number,
               s.name,
               c.name AS course,
               COALESCE(SUM(g.marks), 0) AS total_marks,
               COALESCE(SUM(g.max_marks), 0) AS max_marks
           FROM students s
           LEFT JOIN courses c
           ON s.course_id = c.id
           LEFT JOIN grades g
           ON s.id = g.student_id
           GROUP BY s.id, s.student_number, s.name, c.name
           ORDER BY s.name'''
    )

    rows = cur.fetchall()

    for row in rows:
        if row['max_marks'] and row['max_marks'] > 0:
            row['percentage'] = round(
                (row['total_marks'] / row['max_marks']) * 100, 2
            )
        else:
            row['percentage'] = 0

    cur.close()
    db.close()

    return render_template('reports.html', reports=rows)
if __name__ == "__main__":
    app.run(debug=True)
if __name__ == "__main__":
    app.run(debug=True)
