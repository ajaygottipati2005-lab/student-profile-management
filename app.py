from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import os
import psycopg
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from datetime import date

load_dotenv()

from database import DatabaseConfigError, DatabaseConnectionError, get_connection, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads", "students")
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

def ensure_database_initialized():
    try:
        init_db()
    except (DatabaseConfigError, DatabaseConnectionError) as error:
        app.logger.warning("Database initialization skipped: %s", error)


@app.errorhandler(DatabaseConfigError)
def handle_database_config_error(error):
    return str(error), 500


@app.errorhandler(DatabaseConnectionError)
def handle_database_connection_error(error):
    return str(error), 500


@app.before_request
def initialize_database_before_request():
    ensure_database_initialized()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]


# ================= LOGIN CHECK =================

def logged_in():
    return "student" in session


# ================= HOME =================

@app.route("/")
def home():
    return render_template("student/student_login.html")


# ================= LOGIN =================

@app.route("/login", methods=["POST"])
def login():

    roll = request.form["roll"]
    password = request.form["password"]

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM students
        WHERE roll_number=%s AND password=%s
    """, (roll, password))

    student = cursor.fetchone()

    conn.close()

    if not student:
        return "❌ Login Failed: Check Roll Number / Password"

    # Save Session

    session["student"] = {
        "roll_number": student["roll_number"]
    }

    return redirect("/profile")


# ================= PROFILE =================

@app.route("/profile")
def profile():

    student_session = session.get("student")

    if not student_session:
        return "❌ Session Missing (Login Again)"

    roll = student_session.get("roll_number")

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM students
        WHERE roll_number=%s
    """, (roll,))

    student = cursor.fetchone()

    conn.close()

    if not student:
        return "❌ Student Not Found"

    return render_template(
        "student/student_profile.html",
        student=dict(student)
    )


@app.route("/upload_dp", methods=["POST"])
def upload_dp():
    if not logged_in():
        return redirect("/")

    student_session = session.get("student")
    roll = student_session.get("roll_number")

    if "dp" not in request.files:
        return "❌ No file selected"

    file = request.files["dp"]

    if file.filename == "":
        return "❌ No file selected"

    if not allowed_file(file.filename):
        return "❌ Unsupported file type. Allowed: png, jpg, jpeg, gif"

    filename = secure_filename(file.filename)
    file_ext = filename.rsplit(".", 1)[1].lower()
    stored_name = f"{roll}_{int(__import__('time').time())}.{file_ext}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT photo_filename FROM students
        WHERE roll_number=%s
    """, (roll,))
    existing = cursor.fetchone()

    if existing and existing[0]:
        try:
            old_path = os.path.join(app.config["UPLOAD_FOLDER"], existing[0])
            if os.path.exists(old_path):
                os.remove(old_path)
        except Exception:
            pass

    file.save(file_path)

    cursor.execute("""
        UPDATE students
        SET photo_filename=%s
        WHERE roll_number=%s
    """, (stored_name, roll))

    conn.commit()
    conn.close()

    return redirect(url_for("profile"))


@app.route("/promote_student/<roll_number>")
def promote_student(roll_number):
    if not session.get("admin"):
        return redirect("/admin")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT year, semester FROM students
            WHERE roll_number=%s
        """, (roll_number,))
        current = cursor.fetchone()

        if current is None:
            return "❌ Student Not Found"

        year = current[0] or 1
        semester = current[1] or 1

        if semester == 1:
            semester = 2
        else:
            semester = 1
            year = year + 1

        cursor.execute("""
            UPDATE students
            SET year=%s, semester=%s
            WHERE roll_number=%s
        """, (year, semester, roll_number))

        conn.commit()
        conn.close()

        return f"✅ Student Promoted to Year {year}, Semester {semester}"

    except Exception as e:
        return f"❌ ERROR: {e}"


@app.route("/promote_all_students")
def promote_all_students():
    if not session.get("admin"):
        return redirect("/admin")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE students
            SET
                semester = CASE
                    WHEN COALESCE(semester, 1) = 1 THEN 2
                    ELSE 1
                END,
                year = CASE
                    WHEN COALESCE(semester, 1) = 1 THEN COALESCE(year, 1)
                    ELSE COALESCE(year, 1) + 1
                END
        """)

        conn.commit()
        conn.close()

        return "✅ All students promoted to the next semester/year"

    except Exception as e:
        return f"❌ ERROR: {e}"


@app.route("/delete_student_dp/<roll_number>")
def delete_student_dp(roll_number):
    if not session.get("admin"):
        return redirect("/admin")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT photo_filename FROM students
            WHERE roll_number=%s
        """, (roll_number,))
        student = cursor.fetchone()

        if student and student[0]:
            old_path = os.path.join(app.config["UPLOAD_FOLDER"], student[0])
            if os.path.exists(old_path):
                os.remove(old_path)

        cursor.execute("""
            UPDATE students
            SET photo_filename=NULL
            WHERE roll_number=%s
        """, (roll_number,))

        conn.commit()
        conn.close()

        return "✅ Student DP Deleted Successfully"

    except Exception as e:
        return f"❌ ERROR: {e}"


# ================= STUDENT PAGES =================

@app.route("/attendance")
def attendance():
    if not logged_in():
        return redirect("/")

    student_session = session.get("student")
    roll = student_session.get("roll_number")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT roll_number, name, year, semester, department, section
        FROM students
        WHERE roll_number=%s
    """, (roll,))
    student = cursor.fetchone()

    if not student:
        conn.close()
        return "❌ Student Not Found"

    year = student["year"]
    semester = student["semester"]
    branch = student["department"]

    # Fetch subjects and attendance for current semester and year only
    cursor.execute("""
        SELECT sa.subject_name,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present_count,
               COUNT(a.id) AS total_sessions
        FROM subject_allocation sa
        LEFT JOIN attendance a
            ON a.subject_name = sa.subject_name
            AND a.student_roll = %s
            AND a.year = sa.year
            AND a.semester = sa.semester
            AND a.branch = sa.branch
        WHERE sa.year = %s AND sa.semester = %s AND sa.branch = %s
        GROUP BY sa.subject_name
        ORDER BY sa.subject_name
    """, (roll, year, semester, branch))
    attendance_rows = cursor.fetchall()

    attendance_data = []
    total_present = 0
    total_sessions = 0

    for row in attendance_rows:
        present = row["present_count"] or 0
        total = row["total_sessions"] or 0
        absent = total - present
        percent = round((present / total * 100), 2) if total else 0.0
        attendance_data.append({
            "subject": row["subject_name"],
            "present": present,
            "absent": absent,
            "total": total,
            "percent": percent
        })
        total_present += present
        total_sessions += total

    overall_percentage = round((total_present / total_sessions * 100), 2) if total_sessions else 0.0
    conn.close()

    return render_template(
        "student/attendance.html",
        attendance_data=attendance_data,
        overall_percentage=overall_percentage,
        student=dict(student),
        current_year=year,
        current_semester=semester
    )


@app.route("/assignments")
def assignments():
    return render_template("student/assignments.html")


@app.route("/results")
def results():
    return render_template("student/results.html")


@app.route("/certificate")
def certificate():
    return render_template("student/certificate.html")


@app.route("/fee_details")
def fee_details():
    if not logged_in():
        return redirect(url_for("home"))

    student_session = session.get("student")
    roll = student_session.get("roll_number")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE roll_number=%s", (roll,))
    student_row = cursor.fetchone()
    conn.close()

    if not student_row:
        return "Student Not Found"

    student = {}
    fee_fields = ("Fee", "Fee_Paid", "Fee_Balance", "Exam", "Exam_Paid", "Exam_Balance",
                  "Books", "Books_Paid", "Books_Balance", "CRT", "CRT_Paid", "CRT_Balance",
                  "Hostel", "Hostel_Paid", "Hostel_Balance", "Bus", "Bus_Paid", "Bus_Balance")
    for semester in range(1, 9):
        for field in fee_fields:
            student[f"Sem{semester}_{field}"] = 0
    student.update(dict(student_row))

    menu_items = [
        {"name": "Profile", "url": url_for("profile")},
        {"name": "Attendance", "url": url_for("attendance")},
        {"name": "Results", "url": url_for("results")},
        {"name": "Certificate", "url": url_for("certificate")},
        {"name": "Institution", "url": url_for("institution")},
        {"name": "Logout", "url": url_for("logout")},
    ]

    return render_template("student/fee_details.html", student=student, menu_items=menu_items)


@app.route("/notifications")
def notifications():
    return render_template("student/notifications.html")


# ================= INSTITUTION PAGE =================

@app.route("/institution")
def institution():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM institution
        ORDER BY id DESC
        LIMIT 1
    """)

    institution = cursor.fetchone()

    conn.close()

    return render_template(
        "student/institution.html",
        institution=institution
    )


# ================= SETTINGS =================

@app.route("/settings")
def settings():
    return render_template("student/settings.html")


# ================= CHANGE PASSWORD =================

@app.route("/change_password", methods=["POST"])
def change_password():

    if not logged_in():
        return redirect("/")

    old_password = request.form["old_password"]
    new_password = request.form["new_password"]

    student = session.get("student")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM students
        WHERE roll_number=%s AND password=%s
    """, (student["roll_number"], old_password))

    if cursor.fetchone() is None:
        return "❌ Old Password Incorrect"

    cursor.execute("""
        UPDATE students
        SET password=%s
        WHERE roll_number=%s
    """, (new_password, student["roll_number"]))

    conn.commit()
    conn.close()

    return "✅ Password Changed Successfully"


# ================= ADMIN LOGIN PAGE =================

@app.route("/admin")
def admin_login():
    return render_template("admin/admin_login.html")


# ================= ADMIN LOGIN =================

def _fetch_admin(login_identifier, password):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM admins
            WHERE (username=%s OR LOWER(email)=LOWER(%s)) AND password=%s
            """,
            (login_identifier, login_identifier, password),
        )
        return cursor.fetchone()
    finally:
        conn.close()


@app.route("/admin_login", methods=["POST"])
def admin_login_post():

    login_identifier = request.form["username"].strip()
    password = request.form["password"]

    admin = None
    try:
        admin = _fetch_admin(login_identifier, password)
    except psycopg.errors.UndefinedTable:
        init_db(force=True)
        try:
            admin = _fetch_admin(login_identifier, password)
        except (psycopg.Error, DatabaseConnectionError):
            admin = None

    if admin or (login_identifier == "admin" and password == "admin123"):

        session["admin"] = True

        return redirect("/admin_dashboard")

    return "❌ Invalid Admin Credentials"


# ================= STAFF LOGIN PAGE =================

@app.route("/staff")
def staff_login():
    return render_template("staff/staff_login.html")


# ================= STAFF LOGIN =================

@app.route("/staff_login", methods=["POST"])
def staff_login_post():

    staff_id = request.form["staff_id"]
    password = request.form["password"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM staff
        WHERE staff_id=%s AND password=%s
    """, (staff_id, password))

    staff = cursor.fetchone()
    conn.close()

    if not staff:
        return "❌ Invalid Staff Credentials"

    session.pop("admin", None)
    session["staff"] = staff_id
    return redirect("/staff_dashboard")


# ================= STAFF DASHBOARD =================

@app.route("/staff_dashboard")
def staff_dashboard():

    if session.get("admin"):
        return redirect("/admin_dashboard")

    if not session.get("staff"):
        return redirect("/staff")

    return render_template("staff/staff_dashboard.html")


# ================= STAFF LOGOUT =================

@app.route("/staff_logout")
def staff_logout():

    session.pop("staff", None)
    return redirect("/staff")


# ================= ADMIN DASHBOARD =================

@app.route("/admin_dashboard")
def admin_dashboard():

    if not session.get("admin"):
        return redirect("/admin")

    return render_template("admin/admin_dashboard.html")


# ================= ADD STUDENT =================

@app.route("/add_student")
def add_student():

    if not session.get("admin"):
        return redirect("/admin")

    return render_template("admin/add_student.html")


# ================= SAVE STUDENT =================

@app.route("/save_student", methods=["POST"])
def save_student():

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO students (

                roll_number,
                name,
                password,
                department,
                course_name,
                age,
                section,
                father_name,
                father_phone,
                mother_name,
                mother_phone,
                phone,
                year,
                semester,
                address

            )

            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

        """, (

            request.form["roll"],
            request.form["name"],
            request.form["password"],
            request.form["department"],
            request.form["course"],
            request.form["age"],
            request.form["section"],
            request.form["father"],
            request.form["father_phone"],
            request.form["mother"],
            request.form["mother_phone"],
            request.form["phone"],
            request.form["year"],
            request.form["semester"],
            request.form["address"]

        ))

        conn.commit()
        conn.close()

        return render_template(
            "admin/add_student.html",
            success_message="✅ Student Added Successfully"
        )

    except Exception as e:

        return f"❌ ERROR: {e}"


# ================= ADD INSTITUTION =================

@app.route("/add_institution")
def add_institution():

    if not session.get("admin"):
        return redirect("/admin")

    return render_template("admin/add_institution.html")


# ================= SAVE INSTITUTION =================

@app.route("/save_institution", methods=["POST"])
def save_institution():

    if not session.get("admin"):
        return redirect("/admin")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""

        INSERT INTO institution (

            college_name,
            about_college,
            vision,
            mission,
            principal_message,
            address,
            email,
            phone,
            website,
            accreditation,
            placements

        )

        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)

    """, (

        request.form["college_name"],
        request.form["about_college"],
        request.form["vision"],
        request.form["mission"],
        request.form["principal_message"],
        request.form["address"],
        request.form["email"],
        request.form["phone"],
        request.form["website"],
        request.form["accreditation"],
        request.form["placements"]

    ))

    conn.commit()
    conn.close()

    return "✅ Institution Details Saved Successfully"


# ================= ADD STAFF =================

@app.route("/add_staff")
def add_staff():

    if not session.get("admin"):
        return redirect("/admin")

    return render_template("admin/add_staff.html")


# ================= SAVE STAFF =================

@app.route("/save_staff", methods=["POST"])
def save_staff():

    if not session.get("admin"):
        return redirect("/admin")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO staff (
                staff_id,
                name,
                password
            ) VALUES (%s, %s, %s)
        """, (
            request.form["staff_id"],
            request.form.get("name", ""),
            request.form["password"]
        ))

        conn.commit()
        conn.close()

        return "✅ Staff Added Successfully"

    except Exception as e:
        return f"❌ ERROR: {e}"


# ================= MODIFY STAFF - LIST =================

@app.route("/modify_staff")
def modify_staff():

    if not session.get("admin"):
        return redirect("/admin")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT staff_id, name FROM staff ORDER BY staff_id")

    staff_members = cursor.fetchall()
    conn.close()

    return render_template(
        "admin/modify_staff.html",
        staff_members=staff_members
    )


# ================= EDIT STAFF =================

@app.route("/edit_staff/<staff_id>")
def edit_staff(staff_id):

    if not session.get("admin"):
        return redirect("/admin")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM staff
        WHERE staff_id=%s
    """, (staff_id,))

    staff = cursor.fetchone()
    conn.close()

    if not staff:
        return "❌ Staff Member Not Found"

    return render_template(
        "admin/edit_staff.html",
        staff=dict(staff)
    )


# ================= UPDATE STAFF =================

@app.route("/update_staff", methods=["POST"])
def update_staff():

    if not session.get("admin"):
        return redirect("/admin")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE staff
            SET
                name=%s,
                password=%s
            WHERE staff_id=%s
        """, (
            request.form.get("name", ""),
            request.form["password"],
            request.form["staff_id"]
        ))

        conn.commit()
        conn.close()

        return "✅ Staff Profile Updated Successfully"

    except Exception as e:
        return f"❌ ERROR: {e}"


# ================= DELETE STAFF =================

@app.route("/delete_staff/<staff_id>")
def delete_staff(staff_id):

    if not session.get("admin"):
        return redirect("/admin")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM staff
            WHERE staff_id=%s
        """, (staff_id,))

        conn.commit()
        conn.close()

        return "✅ Staff Deleted Successfully"

    except Exception as e:
        return f"❌ ERROR: {e}"


# ================= MODIFY STUDENT - LIST =================

@app.route("/modify_student")
def modify_student():

    if not session.get("admin"):
        return redirect("/admin")

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT roll_number, name, department, year, semester, section FROM students ORDER BY roll_number")

    students = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/modify_student.html",
        students=students
    )


# ================= EDIT STUDENT =================

@app.route("/edit_student/<roll_number>")
def edit_student(roll_number):

    if not session.get("admin"):
        return redirect("/admin")

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM students
        WHERE roll_number=%s
    """, (roll_number,))

    student = cursor.fetchone()

    conn.close()

    if not student:
        return "❌ Student Not Found"

    return render_template(
        "admin/edit_student.html",
        student=dict(student)
    )


# ================= UPDATE STUDENT =================

@app.route("/update_student", methods=["POST"])
def update_student():

    if not session.get("admin"):
        return redirect("/admin")

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE students
            SET
                name=%s,
                password=%s,
                department=%s,
                course_name=%s,
                age=%s,
                section=%s,
                father_name=%s,
                father_phone=%s,
                mother_name=%s,
                mother_phone=%s,
                phone=%s,
                year=%s,
                semester=%s,
                address=%s
            WHERE roll_number=%s
        """, (

            request.form["name"],
            request.form["password"],
            request.form["department"],
            request.form["course"],
            request.form["age"],
            request.form["section"],
            request.form["father"],
            request.form["father_phone"],
            request.form["mother"],
            request.form["mother_phone"],
            request.form["phone"],
            request.form["year"],
            request.form["semester"],
            request.form["address"],
            request.form["roll"]

        ))

        conn.commit()
        conn.close()

        return "✅ Student Profile Updated Successfully"

    except Exception as e:

        return f"❌ ERROR: {e}"


# ================= DELETE STUDENT =================

@app.route("/delete_student/<roll_number>")
def delete_student(roll_number):

    if not session.get("admin"):
        return redirect("/admin")

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM students
            WHERE roll_number=%s
        """, (roll_number,))

        conn.commit()
        conn.close()

        return "✅ Student Deleted Successfully"

    except Exception as e:

        return f"❌ ERROR: {e}"


# ================= LOGOUT =================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ================= ADMIN LOGOUT =================

@app.route("/admin_logout")
def admin_logout():

    session.clear()

    return redirect("/admin")


# ================= ALLOCATE SUBJECTS =================

@app.route("/allocate_subjects")
def allocate_subjects():

    if not session.get("admin"):
        return redirect("/admin")

    conn = get_connection()
    cursor = conn.cursor()

    # Get existing allocations
    cursor.execute("""
        SELECT *
        FROM subject_allocation
        ORDER BY year, semester, branch, subject_name
    """)
    allocations = cursor.fetchall()

    conn.close()

    return render_template("admin/allocate_subjects.html",
                         allocations=allocations)


# ================= SAVE SUBJECT ALLOCATION =================

@app.route("/save_allocation", methods=["POST"])
def save_allocation():

    if not session.get("admin"):
        return redirect("/admin")

    subject_names_raw = request.form.get("subject_names", "")
    year = request.form.get("year")
    semester = request.form.get("semester")
    branch = request.form.get("branch")

    if not subject_names_raw.strip():
        return "❌ Please enter at least one subject name"

    subject_names = [
        name.strip()
        for part in subject_names_raw.splitlines()
        for name in part.split(",")
        if name.strip()
    ]

    if not subject_names:
        return "❌ Please enter at least one valid subject name"

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.executemany("""
            INSERT INTO subject_allocation (
                subject_name,
                year,
                semester,
                branch
            )
            VALUES (%s, %s, %s, %s)
        """, [
            (name, year, semester, branch)
            for name in subject_names
        ])

        conn.commit()
        conn.close()

        return redirect("/allocate_subjects")

    except Exception as e:
        return f"❌ Error: {str(e)}"


# ================= STAFF ATTENDANCE =================

@app.route("/staff_attendance", methods=["GET", "POST"])
def staff_attendance():

    if session.get("admin"):
        return redirect("/admin_dashboard")

    if not session.get("staff"):
        return redirect("/staff")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT department FROM students ORDER BY department")
    branches = [row[0] for row in cursor.fetchall() if row[0]]

    cursor.execute("SELECT DISTINCT section FROM students ORDER BY section")
    sections = [row[0] for row in cursor.fetchall() if row[0]]

    students = []
    subject_options = []
    selected = {
        "year": "",
        "semester": "",
        "branch": "",
        "section": "",
        "subject_name": "",
        "attendance_date": date.today().isoformat()
    }
    success_message = None
    error_message = None

    if request.method == "POST":
        action = request.form.get("action")
        selected["year"] = request.form.get("year", "")
        selected["semester"] = request.form.get("semester", "")
        selected["branch"] = request.form.get("branch", "")
        selected["section"] = request.form.get("section", "")
        selected["subject_name"] = request.form.get("subject_name", "")
        selected["attendance_date"] = request.form.get("attendance_date", selected["attendance_date"])

        if selected["year"] and selected["semester"] and selected["branch"]:
            cursor.execute("SELECT DISTINCT subject_name FROM subject_allocation WHERE year=%s AND semester=%s AND branch=%s ORDER BY subject_name", (selected["year"], selected["semester"], selected["branch"]))
            subject_options = [row[0] for row in cursor.fetchall() if row[0]]
        else:
            subject_options = []

        if action == "load_students":
            if selected["year"] and selected["semester"] and selected["branch"] and selected["section"] and selected["subject_name"]:
                cursor.execute("""
                    SELECT roll_number, name
                    FROM students
                    WHERE year=%s AND semester=%s AND department=%s AND section=%s
                    ORDER BY roll_number
                """, (selected["year"], selected["semester"], selected["branch"], selected["section"]))
                students = cursor.fetchall()
            else:
                error_message = "Please select year, semester, branch, section and subject first."

        elif action == "save_attendance":
            # Check attendance limit (6 times per day per section)
            cursor.execute("""
                SELECT COUNT(DISTINCT date || '_' || subject_name) as attendance_count
                FROM attendance
                WHERE year = %s AND semester = %s AND branch = %s AND section = %s AND date = %s
            """, (selected["year"], selected["semester"], selected["branch"], selected["section"], selected["attendance_date"]))
            
            attendance_count_row = cursor.fetchone()
            attendance_count = attendance_count_row[0] if attendance_count_row else 0
            
            if attendance_count >= 6:
                error_message = "Attendance limit reached! You can only take attendance 6 times per day for this section."
            else:
                student_rolls = request.form.getlist("student_rolls")
                present_rolls = set(request.form.getlist("present"))
                attendance_date = selected["attendance_date"]
                staff_id = session.get("staff") if session.get("staff") else None

                if not student_rolls:
                    error_message = "No students selected for attendance."
                else:
                    attendance_data = []
                    for roll in student_rolls:
                        status = "Present" if roll in present_rolls else "Absent"
                        attendance_data.append((
                            roll,
                            selected["subject_name"],
                            selected["year"],
                            selected["semester"],
                            selected["branch"],
                            selected["section"],
                            attendance_date,
                            status,
                            staff_id
                        ))

                    cursor.executemany("""
                        INSERT INTO attendance (
                            student_roll,
                            subject_name,
                            year,
                            semester,
                            branch,
                            section,
                            date,
                            status,
                            staff_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, attendance_data)

                    conn.commit()
                    success_message = "Attendance saved successfully!"

        elif action == "copy_previous":
            # Check if there's any previous attendance for this year/semester/branch
            cursor.execute("""
                SELECT COUNT(*) as prev_count
                FROM attendance
                WHERE year = %s AND semester = %s AND branch = %s AND date < %s
            """, (selected["year"], selected["semester"], selected["branch"], selected["attendance_date"]))
            
            prev_count_row = cursor.fetchone()
            prev_count = prev_count_row[0] if prev_count_row else 0
            
            if prev_count == 0:
                error_message = "No previous attendance found for this year/semester/branch. At least one attendance must be taken before copying."
            else:
                # Copy attendance from the most recent date for the same year/semester/branch
                cursor.execute("""
                    SELECT date, student_roll, subject_name, status
                    FROM attendance
                    WHERE year = %s AND semester = %s AND branch = %s AND date < %s
                    ORDER BY date DESC
                """, (selected["year"], selected["semester"], selected["branch"], selected["attendance_date"]))
                
                previous_attendance = cursor.fetchall()
                if previous_attendance:
                    # Group by date to find the latest date
                    attendance_by_date = {}
                    for row in previous_attendance:
                        date_key = row["date"]
                        if date_key not in attendance_by_date:
                            attendance_by_date[date_key] = []
                        attendance_by_date[date_key].append(row)
                    
                    # Get the latest date
                    latest_date = max(attendance_by_date.keys())
                    latest_attendance = attendance_by_date[latest_date]
                    
                    # Create attendance data for current date and selected subject
                    attendance_data = []
                    for row in latest_attendance:
                        attendance_data.append((
                            row["student_roll"],
                            selected["subject_name"],  # Use the selected subject
                            selected["year"],
                            selected["semester"],
                            selected["branch"],
                            selected["section"],  # Use the selected section
                            selected["attendance_date"],
                            row["status"],
                            session.get("staff") if session.get("staff") else None
                        ))
                    
                    cursor.executemany("""
                        INSERT INTO attendance (
                            student_roll,
                            subject_name,
                            year,
                            semester,
                            branch,
                            section,
                            date,
                            status,
                            staff_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, attendance_data)
                    
                    conn.commit()
                    success_message = f"Attendance copied from {latest_date} successfully!"
                else:
                    error_message = "No previous attendance found to copy."

    # Calculate remaining attendance count for the section
    remaining_count = 6
    if selected["year"] and selected["semester"] and selected["branch"] and selected["section"] and selected["attendance_date"]:
        cursor.execute("""
            SELECT COUNT(DISTINCT date || '_' || subject_name) as attendance_count
            FROM attendance
            WHERE year = %s AND semester = %s AND branch = %s AND section = %s AND date = %s
        """, (selected["year"], selected["semester"], selected["branch"], selected["section"], selected["attendance_date"]))
        
        attendance_count_row = cursor.fetchone()
        attendance_count = attendance_count_row[0] if attendance_count_row else 0
        remaining_count = max(0, 6 - attendance_count)

    conn.close()

    return render_template(
        "staff/staff_attendance.html",
        branches=branches,
        sections=sections,
        subject_options=subject_options,
        students=students,
        selected=selected,
        success_message=success_message,
        error_message=error_message,
        remaining_count=remaining_count
    )


@app.route("/subject_options")
def subject_options_api():

    if session.get("admin"):
        return redirect("/admin_dashboard")

    if not session.get("staff"):
        return jsonify([]), 401

    year = request.args.get("year")
    semester = request.args.get("semester")
    branch = request.args.get("branch")

    if not (year and semester and branch):
        return jsonify([])

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT subject_name FROM subject_allocation WHERE year=%s AND semester=%s AND branch=%s ORDER BY subject_name", (year, semester, branch))
    subjects = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()

    return jsonify(subjects)


@app.route("/section_options")
def section_options_api():

    if session.get("admin"):
        return redirect("/admin_dashboard")

    if not session.get("staff"):
        return jsonify([]), 401

    branch = request.args.get("branch")

    if not branch:
        return jsonify([])

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT section FROM students WHERE department=%s ORDER BY section", (branch,))
    sections = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()

    return jsonify(sections)


# ================= DELETE SUBJECT ALLOCATION =================

@app.route("/delete_allocation/<int:allocation_id>")
def delete_allocation(allocation_id):

    if not session.get("admin"):
        return redirect("/admin")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM subject_allocation
            WHERE id = %s
        """, (allocation_id,))

        conn.commit()
        conn.close()

        return redirect("/allocate_subjects")

    except Exception as e:
        return f"❌ Error: {str(e)}"


# ================= ANALYZE ATTENDANCE =================

@app.route("/analyze_attendance", methods=["GET", "POST"])
def analyze_attendance():

    if session.get("admin"):
        return redirect("/admin_dashboard")

    if not session.get("staff"):
        return redirect("/staff")

    conn = get_connection()
    cursor = conn.cursor()

    # Get available branches and sections
    cursor.execute("SELECT DISTINCT department FROM students ORDER BY department")
    branches = [row[0] for row in cursor.fetchall() if row[0]]

    cursor.execute("SELECT DISTINCT section FROM students ORDER BY section")
    sections = [row[0] for row in cursor.fetchall() if row[0]]

    cursor.execute("SELECT DISTINCT year FROM students ORDER BY year")
    years = [row[0] for row in cursor.fetchall() if row[0]]

    cursor.execute("SELECT DISTINCT semester FROM students ORDER BY semester")
    semesters = [row[0] for row in cursor.fetchall() if row[0]]

    analysis_data = []
    selected = {
        "year": "",
        "semester": "",
        "branch": "",
        "section": ""
    }
    error_message = None

    if request.method == "POST":
        selected["year"] = request.form.get("year", "")
        selected["semester"] = request.form.get("semester", "")
        selected["branch"] = request.form.get("branch", "")
        selected["section"] = request.form.get("section", "")

        if selected["year"] and selected["semester"] and selected["branch"] and selected["section"]:
            # Get all students matching the criteria
            cursor.execute("""
                SELECT roll_number, name
                FROM students
                WHERE year=%s AND semester=%s AND department=%s AND section=%s
                ORDER BY roll_number
            """, (selected["year"], selected["semester"], selected["branch"], selected["section"]))

            students = cursor.fetchall()

            for student in students:
                roll = student["roll_number"]
                
                # Get total attendance count
                cursor.execute("""
                    SELECT COUNT(*) as total_classes
                    FROM attendance
                    WHERE student_roll=%s AND year=%s AND semester=%s AND branch=%s AND section=%s
                """, (roll, selected["year"], selected["semester"], selected["branch"], selected["section"]))
                
                total_classes = cursor.fetchone()["total_classes"]

                # Get present count
                cursor.execute("""
                    SELECT COUNT(*) as present_count
                    FROM attendance
                    WHERE student_roll=%s AND status='Present' AND year=%s AND semester=%s AND branch=%s AND section=%s
                """, (roll, selected["year"], selected["semester"], selected["branch"], selected["section"]))
                
                present_count = cursor.fetchone()["present_count"]

                # Calculate attendance percentage
                attendance_percentage = 0 if total_classes == 0 else round((present_count / total_classes) * 100, 2)

                # Get absent dates
                cursor.execute("""
                    SELECT DISTINCT date, subject_name
                    FROM attendance
                    WHERE student_roll=%s AND status='Absent' AND year=%s AND semester=%s AND branch=%s AND section=%s
                    ORDER BY date DESC
                """, (roll, selected["year"], selected["semester"], selected["branch"], selected["section"]))

                absent_records = cursor.fetchall()
                absent_dates = [{"date": record["date"], "subject": record["subject_name"]} for record in absent_records]

                # Get all subjects for this student
                cursor.execute("""
                    SELECT DISTINCT subject_name
                    FROM attendance
                    WHERE student_roll=%s AND year=%s AND semester=%s AND branch=%s AND section=%s
                    ORDER BY subject_name
                """, (roll, selected["year"], selected["semester"], selected["branch"], selected["section"]))

                subjects = [record["subject_name"] for record in cursor.fetchall()]

                analysis_data.append({
                    "roll_number": roll,
                    "name": student["name"],
                    "attendance_percentage": attendance_percentage,
                    "total_classes": total_classes,
                    "present_count": present_count,
                    "absent_count": total_classes - present_count,
                    "absent_records": absent_dates,
                    "subjects": subjects
                })
        else:
            error_message = "Please select all filters: Year, Semester, Branch, and Section"

    conn.close()

    return render_template(
        "staff/analyze_attendance.html",
        branches=branches,
        sections=sections,
        years=years,
        semesters=semesters,
        analysis_data=analysis_data,
        selected=selected,
        error_message=error_message
    )


# ================= RUN APP =================

try:
    init_db()
except (DatabaseConfigError, DatabaseConnectionError) as error:
    app.logger.warning("Database initialization at import skipped: %s", error)


if __name__ == "__main__":
    try:
        init_db()
    except (DatabaseConfigError, DatabaseConnectionError) as error:
        print(error)
        print("Flask will start, but database-backed routes need PostgreSQL configured.")
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
