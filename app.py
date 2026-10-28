from flask import Flask, render_template, request, redirect, session, send_from_directory
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "elearning_secret_key"

app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database connection
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# Create users table
def create_table():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            duration TEXT NOT NULL,
            instructor TEXT NOT NULL
        )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        material_type TEXT NOT NULL,
        material_link TEXT NOT NULL
    )
""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        title TEXT NOT NULL
    )
""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        option1 TEXT NOT NULL,
        option2 TEXT NOT NULL,
        option3 TEXT NOT NULL,
        option4 TEXT NOT NULL,
        correct_answer TEXT NOT NULL
    )
""")

    conn.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        quiz_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        total INTEGER NOT NULL
    )
""")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        quiz_id INTEGER,
        score INTEGER,
        total_questions INTEGER
    )
""")

    try:
        conn.execute(
            "INSERT INTO admins (username, password) VALUES (?, ?)",
            ("admin", "admin123")
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass

    conn.close()

    

# Home page
@app.route("/")
def home():
    return render_template("index.html")


# Register page
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()

        try:
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, password)
            )

            conn.commit()
            conn.close()

            return redirect("/login")

        except sqlite3.IntegrityError:
            conn.close()
            return "Email already registered!"

    return render_template("register.html")


# Login page
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, password)
        ).fetchone()

        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect("/dashboard")
        else:
            return "Invalid email or password!"

    return render_template("login.html")



@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    # All courses
    courses = conn.execute("""
        SELECT *
        FROM courses
        ORDER BY id DESC
    """).fetchall()

    # All quizzes
    quizzes = conn.execute("""
        SELECT
            quizzes.*,
            courses.title AS course_title
        FROM quizzes
        JOIN courses
        ON quizzes.course_id = courses.id
        ORDER BY quizzes.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        courses=courses,
        quizzes=quizzes
    )



@app.route("/my-results")
def my_results():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    try:
        results = conn.execute("""
            SELECT
                qr.id,
                q.title AS quiz_title,
                qr.score,
                qr.total_questions
            FROM quiz_results AS qr
            JOIN quizzes AS q
                ON qr.quiz_id = q.id
            WHERE qr.student_id = ?
              AND qr.id = (
                  SELECT MAX(qr2.id)
                  FROM quiz_results AS qr2
                  WHERE qr2.student_id = qr.student_id
                    AND qr2.quiz_id = qr.quiz_id
              )
            ORDER BY qr.id DESC
        """, (session["user_id"],)).fetchall()

        total_score = sum(
            result["score"] or 0 for result in results
        )

        total_questions = sum(
            result["total_questions"] or 0 for result in results
        )

        average_percentage = (
            (total_score / total_questions) * 100
            if total_questions > 0 else 0
        )

        return render_template(
            "my_results.html",
            results=results,
            average_percentage=average_percentage
        )

    finally:
        conn.close()


@app.route("/course/<int:course_id>")
def course_details(course_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    # Course ki details
    course = conn.execute("""
        SELECT *
        FROM courses
        WHERE id = ?
    """, (course_id,)).fetchone()

    if course is None:
        conn.close()
        return "Course Not Found"

    # Course ke materials
    materials = conn.execute("""
        SELECT *
        FROM materials
        WHERE course_id = ?
        ORDER BY id DESC
    """, (course_id,)).fetchall()

    # Course ke quizzes
    quizzes = conn.execute("""
        SELECT *
        FROM quizzes
        WHERE course_id = ?
        ORDER BY id DESC
    """, (course_id,)).fetchall()

    

    conn.close()

    return render_template(
        "course_details.html",
        course=course,
        materials=materials,
        quizzes=quizzes
    )




@app.route("/quiz/<int:quiz_id>/submit", methods=["POST"])
def submit_quiz(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    try:
        quiz = conn.execute(
            "SELECT * FROM quizzes WHERE id = ?",
            (quiz_id,)
        ).fetchone()

        if quiz is None:
            return "Quiz Not Found", 404

        questions = conn.execute(
            "SELECT * FROM questions WHERE quiz_id = ?",
            (quiz_id,)
        ).fetchall()

        if not questions:
            return "No questions available for this quiz.", 400

        score = 0
        total = len(questions)

        answer_map = {
            "a": 0, "option a": 0, "option1": 0,
            "option 1": 0, "1": 0,
            "b": 1, "option b": 1, "option2": 1,
            "option 2": 1, "2": 1,
            "c": 2, "option c": 2, "option3": 2,
            "option 3": 2, "3": 2,
            "d": 3, "option d": 3, "option4": 3,
            "option 4": 3, "4": 3
        }

        for question in questions:

            answer = request.form.get(
                f"question_{question['id']}", ""
            ).strip()

            correct_raw = str(
                question["correct_answer"] or ""
            ).strip()

            options = [
                str(question["option1"] or "").strip(),
                str(question["option2"] or "").strip(),
                str(question["option3"] or "").strip(),
                str(question["option4"] or "").strip()
            ]

            key = correct_raw.casefold()

            if key in answer_map:
                correct_text = options[answer_map[key]]
            else:
                correct_text = correct_raw

            if answer and answer.casefold() == correct_text.casefold():
                score += 1

        conn.execute("""
            INSERT INTO quiz_results
            (student_id, quiz_id, score, total_questions)
            VALUES (?, ?, ?, ?)
        """, (
            session["user_id"],
            quiz_id,
            score,
            total
        ))

        conn.commit()

        return render_template(
            "quiz_result.html",
            quiz=quiz,
            score=score,
            total=total
        )

    finally:
        conn.close()





@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()

        admin = conn.execute(
            "SELECT * FROM admins WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()

        conn.close()

        if admin:
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]

            return redirect("/admin-dashboard")

        return "Invalid Admin Login!"

    return render_template("admin_login.html")



@app.route("/admin/add-course", methods=["GET", "POST"])
def admin_add_course():

    if "admin_id" not in session:
        return redirect("/admin-login")

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        duration = request.form["duration"]
        instructor = request.form["instructor"]

        conn = get_db_connection()

        conn.execute("""
            INSERT INTO courses
            (title, description, duration, instructor)
            VALUES (?, ?, ?, ?)
        """, (title, description, duration, instructor))

        conn.commit()
        conn.close()

        return redirect("/admin-dashboard")

    return render_template("add_course.html")

@app.route("/admin/add-material/<int:course_id>", methods=["GET", "POST"])
def admin_add_material(course_id):

    if "admin_id" not in session:
        return redirect("/admin-login")

    if request.method == "POST":

        title = request.form["title"]
        material_type = request.form["material_type"]

        file = request.files["material_file"]

        if file and file.filename != "":

            filename = file.filename

            file.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

            material_link = "/uploads/" + filename

            conn = get_db_connection()

            conn.execute("""
                INSERT INTO materials
                (course_id, title, material_type, material_link)
                VALUES (?, ?, ?, ?)
            """, (
                course_id,
                title,
                material_type,
                material_link
            ))

            conn.commit()
            conn.close()

            return redirect("/admin-dashboard")

    return render_template(
        "add_material.html",
        course_id=course_id
    )

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

@app.route("/admin/edit-material/<int:material_id>", methods=["GET", "POST"])
def admin_edit_material(material_id):

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    material = conn.execute("""
        SELECT *
        FROM materials
        WHERE id = ?
    """, (material_id,)).fetchone()

    if material is None:
        conn.close()
        return "Material Not Found"

    if request.method == "POST":

        title = request.form["title"]
        material_type = request.form["material_type"]
        material_link = request.form["material_link"]

        conn.execute("""
            UPDATE materials
            SET title = ?,
                material_type = ?,
                material_link = ?
            WHERE id = ?
        """, (
            title,
            material_type,
            material_link,
            material_id
        ))

        conn.commit()
        conn.close()

        return redirect("/admin-dashboard")

    conn.close()

    return render_template(
        "edit_material.html",
        material=material
    )

@app.route("/admin/delete-material/<int:material_id>")
def admin_delete_material(material_id):

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    conn.execute("""
        DELETE FROM materials
        WHERE id = ?
    """, (material_id,))

    conn.commit()
    conn.close()

    return redirect("/admin-dashboard")

@app.route("/admin/add-quiz", methods=["GET", "POST"])
def admin_add_quiz():

    if "admin_id" not in session:
        return redirect("/admin-login")

    if request.method == "POST":

        course_id = request.form["course_id"]
        title = request.form["title"]

        conn = get_db_connection()

        conn.execute("""
            INSERT INTO quizzes
            (course_id, title)
            VALUES (?, ?)
        """, (course_id, title))

        conn.commit()
        conn.close()

        return redirect("/admin-dashboard")

    conn = get_db_connection()

    courses = conn.execute(
        "SELECT * FROM courses"
    ).fetchall()

    conn.close()

    return render_template(
        "add_quiz.html",
        courses=courses
    )



@app.route("/admin/add-question/<int:quiz_id>", methods=["GET", "POST"])
def admin_add_question(quiz_id):

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    quiz = conn.execute(
        "SELECT * FROM quizzes WHERE id = ?",
        (quiz_id,)
    ).fetchone()

    if quiz is None:
        conn.close()
        return "Quiz Not Found", 404

    if request.method == "POST":

        question = request.form.get("question", "").strip()
        option1 = request.form.get("option1", "").strip()
        option2 = request.form.get("option2", "").strip()
        option3 = request.form.get("option3", "").strip()
        option4 = request.form.get("option4", "").strip()
        correct_answer = request.form.get("correct_answer", "").strip()

        options = [option1, option2, option3, option4]

        # Check that all fields are filled
        if not question or not all(options) or not correct_answer:
            conn.close()
            return "Please fill in all question and option fields.", 400

        # Convert A, B, C, D or option1, option2, etc.
        # into the actual correct option text
        answer_key = correct_answer.casefold().strip()

        answer_map = {
            "a": 0, "option a": 0, "option1": 0,
            "option 1": 0, "1": 0,
            "b": 1, "option b": 1, "option2": 1,
            "option 2": 1, "2": 1,
            "c": 2, "option c": 2, "option3": 2,
            "option 3": 2, "3": 2,
            "d": 3, "option d": 3, "option4": 3,
            "option 4": 3, "4": 3
        }

        if answer_key in answer_map:
            correct_answer = options[answer_map[answer_key]]

        else:
            # If the correct answer is entered as text,
            # match it with one of the four options
            matched_option = None

            for option in options:
                if option.casefold() == answer_key:
                    matched_option = option
                    break

            if matched_option is None:
                conn.close()
                return (
                    "Correct answer must match one of the four options. "
                    "Please go back and check the question."
                ), 400

            correct_answer = matched_option

        # Save the question and the correct option text
        conn.execute("""
            INSERT INTO questions
            (quiz_id, question, option1, option2,
             option3, option4, correct_answer)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            quiz_id,
            question,
            option1,
            option2,
            option3,
            option4,
            correct_answer
        ))

        conn.commit()
        conn.close()

        return redirect("/admin-dashboard")

    conn.close()

    return render_template(
        "add_question.html",
        quiz_id=quiz_id
    )







# Dashboard
@app.route("/courses")
def courses():

    conn = get_db_connection()

    courses = conn.execute(
        "SELECT * FROM courses"
    ).fetchall()

    conn.close()

    return render_template(
        "courses.html",
        courses=courses
    )

@app.route("/admin-dashboard")
def admin_dashboard():

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    courses = conn.execute(
        "SELECT * FROM courses"
    ).fetchall()

    quizzes = conn.execute("""
        SELECT quizzes.*, courses.title AS course_title
        FROM quizzes
        JOIN courses
        ON quizzes.course_id = courses.id
    """).fetchall()

    questions = conn.execute("""
        SELECT questions.*,
               quizzes.title AS quiz_title
        FROM questions
        LEFT JOIN quizzes
        ON questions.quiz_id = quizzes.id
    """).fetchall()




    # ALL MATERIALS
    materials = conn.execute("""
        SELECT
            materials.*,
            courses.title AS course_title
        FROM materials
        JOIN courses
        ON materials.course_id = courses.id
        ORDER BY materials.id DESC
    """).fetchall()


    conn.close()

    return render_template(
        "admin_dashboard.html",
        courses=courses,
        quizzes=quizzes,
        questions=questions,
        materials=materials
    )

@app.route("/admin/results")
def admin_results():

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    results = conn.execute("""
        SELECT
            quiz_results.id,
            users.name AS student_name,
            quizzes.title AS quiz_title,
            quiz_results.score,
            quiz_results.total_questions AS total
        FROM quiz_results
        JOIN users
            ON quiz_results.student_id = users.id
        JOIN quizzes
            ON quiz_results.quiz_id = quizzes.id
        ORDER BY quiz_results.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_results.html",
        results=results
    )


@app.route("/admin/students")
def admin_students():

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    students = conn.execute("""
        SELECT id, name, email
        FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_students.html",
        students=students
    )

@app.route("/admin/topper")
def admin_topper():

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    students = conn.execute("""
        SELECT
            users.id,
            users.name,
            users.email,
            SUM(quiz_results.score) AS total_score,
            SUM(quiz_results.total_questions) AS total_questions
        FROM users
        JOIN quiz_results
        ON users.id = quiz_results.student_id
        GROUP BY users.id
    """).fetchall()

    conn.close()

    topper = None
    highest_percentage = -1

    for student in students:

        if student["total_questions"] > 0:

            percentage = (
                student["total_score"] /
                student["total_questions"]
            ) * 100

            if percentage > highest_percentage:

                highest_percentage = percentage
                topper = student

    prize = 0

    if topper:

        if highest_percentage >= 90:
            prize = 10000

        elif highest_percentage >= 80:
            prize = 5000

        elif highest_percentage >= 60:
            prize = 2000

        else:
            prize = 0

    return render_template(
        "topper.html",
        topper=topper,
        percentage=highest_percentage,
        prize=prize
    )
@app.route("/admin/all-results")
def admin_all_results():

    # Admin login check
    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    results = conn.execute("""
        SELECT
            quiz_results.id,
            users.name AS student_name,
            users.email AS student_email,
            quizzes.title AS quiz_title,
            quiz_results.score,
            quiz_results.total_questions
        FROM quiz_results
        JOIN users
        ON quiz_results.student_id = users.id
        JOIN quizzes
        ON quiz_results.quiz_id = quizzes.id
        ORDER BY quiz_results.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "all_results.html",
        results=results
    )

@app.route("/admin/edit-course/<int:course_id>", methods=["GET", "POST"])
def admin_edit_course(course_id):

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    course = conn.execute(
        "SELECT * FROM courses WHERE id = ?",
        (course_id,)
    ).fetchone()

    if course is None:
        conn.close()
        return "Course Not Found"

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        duration = request.form["duration"]
        instructor = request.form["instructor"]

        conn.execute("""
            UPDATE courses
            SET title = ?,
                description = ?,
                duration = ?,
                instructor = ?
            WHERE id = ?
        """, (
            title,
            description,
            duration,
            instructor,
            course_id
        ))

        conn.commit()
        conn.close()

        return redirect("/admin-dashboard")

    conn.close()

    return render_template(
        "edit_course.html",
        course=course
    )

@app.route("/admin/edit-quiz/<int:quiz_id>", methods=["GET", "POST"])
def admin_edit_quiz(quiz_id):

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    # Quiz find karo
    quiz = conn.execute(
        "SELECT * FROM quizzes WHERE id = ?",
        (quiz_id,)
    ).fetchone()

    if quiz is None:
        conn.close()
        return "Quiz Not Found"

    # Update quiz
    if request.method == "POST":

        title = request.form["title"]

        conn.execute("""
            UPDATE quizzes
            SET title = ?
            WHERE id = ?
        """, (
            title,
            quiz_id
        ))

        conn.commit()
        conn.close()

        return redirect("/admin-dashboard")

    conn.close()

    return render_template(
        "edit_quiz.html",
        quiz=quiz
    )

@app.route("/admin/delete-quiz/<int:quiz_id>")
def admin_delete_quiz(quiz_id):

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    # Check quiz exists
    quiz = conn.execute("""
        SELECT *
        FROM quizzes
        WHERE id = ?
    """, (quiz_id,)).fetchone()

    if quiz is None:
        conn.close()
        return "Quiz Not Found"

    # Check whether questions are present
    question_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM questions
        WHERE quiz_id = ?
    """, (quiz_id,)).fetchone()["count"]

    # Check whether results are present
    result_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM quiz_results
        WHERE quiz_id = ?
    """, (quiz_id,)).fetchone()["count"]

    # Don't delete if quiz has questions or results
    if question_count > 0 or result_count > 0:

        conn.close()

        return f"""
        <h2>Cannot Delete This Quiz</h2>

        <p>
            This quiz has {question_count} question(s)
            and {result_count} student result(s).
        </p>

        <p>
            Please keep this quiz because student data is connected to it.
        </p>

        <a href="/admin-dashboard">
            Back to Admin Dashboard
        </a>
        """

    # Delete only if no questions/results exist
    conn.execute("""
        DELETE FROM quizzes
        WHERE id = ?
    """, (quiz_id,))

    conn.commit()
    conn.close()

    return redirect("/admin-dashboard")

@app.route("/admin/delete-course/<int:course_id>")
def admin_delete_course(course_id):

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    # Check course exists
    course = conn.execute("""
        SELECT *
        FROM courses
        WHERE id = ?
    """, (course_id,)).fetchone()

    if course is None:
        conn.close()
        return "Course Not Found"

    # Count materials
    material_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM materials
        WHERE course_id = ?
    """, (course_id,)).fetchone()["count"]

    # Count quizzes
    quiz_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM quizzes
        WHERE course_id = ?
    """, (course_id,)).fetchone()["count"]

    # Don't delete if related data exists
    if material_count > 0 or quiz_count > 0:

        conn.close()

        return f"""
        <h2>Cannot Delete This Course</h2>

        <p>
            This course has {material_count} material(s)
            and {quiz_count} quiz(zes).
        </p>

        <p>
            Please delete or manage the related data first.
        </p>

        <a href="/admin-dashboard">
            Back to Admin Dashboard
        </a>
        """

    # Delete only empty course
    conn.execute("""
        DELETE FROM courses
        WHERE id = ?
    """, (course_id,))

    conn.commit()
    conn.close()

    return redirect("/admin-dashboard")

@app.route("/admin/student-results/<int:student_id>")
def admin_student_results(student_id):

    if "admin_id" not in session:
        return redirect("/admin-login")

    conn = get_db_connection()

    # Student information
    student = conn.execute("""
        SELECT id, name, email
        FROM users
        WHERE id = ?
    """, (student_id,)).fetchone()

    # Student ke results
    results = conn.execute("""
        SELECT
            quiz_results.id,
            quiz_results.quiz_id,
            quiz_results.score,
            quiz_results.total_questions,
            quizzes.title AS quiz_title
        FROM quiz_results
        LEFT JOIN quizzes
        ON quiz_results.quiz_id = quizzes.id
        WHERE quiz_results.student_id = ?
        ORDER BY quiz_results.id DESC
    """, (student_id,)).fetchall()

    

    # DEBUG
    total_score = 0
    total_questions = 0

    for result in results:
        total_score += result["score"]
        total_questions += result["total_questions"]

    if total_questions > 0:
        average_percentage = (total_score / total_questions) * 100
    else:
        average_percentage = 0

    # Database close
    conn.close()

    # Student results page
    return render_template(
        "student_results.html",
        student=student,
        results=results,
        average_percentage=average_percentage
    )

    



@app.route("/quiz/<int:quiz_id>", methods=["GET", "POST"])
def take_quiz(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()

    quiz = conn.execute(
        "SELECT * FROM quizzes WHERE id = ?",
        (quiz_id,)
    ).fetchone()

    if quiz is None:
        conn.close()
        return "Quiz Not Found", 404

    questions = conn.execute(
        "SELECT * FROM questions WHERE quiz_id = ?",
        (quiz_id,)
    ).fetchall()

    if request.method == "POST":

        if not questions:
            conn.close()
            return "No questions available for this quiz."

        score = 0
        total_questions = len(questions)

        # DEBUG: Print saved answers and student selections
        print("\n========== QUIZ DEBUG ==========")

        for question in questions:
            selected_answer = request.form.get(
                "question_" + str(question["id"]), ""
            ).strip()

            print("Question ID:", question["id"])
            print("Question:", question["question"])
            print("Option 1:", question["option1"])
            print("Option 2:", question["option2"])
            print("Option 3:", question["option3"])
            print("Option 4:", question["option4"])
            print(
                "Saved correct answer:",
                repr(question["correct_answer"])
            )
            print("Student selected:", repr(selected_answer))
            print("--------------------------------")

        print("================================\n")

        # Check each submitted answer
        for question in questions:

            answer = request.form.get(
                "question_" + str(question["id"]), ""
            ).strip()

            correct_raw = str(
                question["correct_answer"] or ""
            ).strip()

            options = [
                str(question["option1"] or "").strip(),
                str(question["option2"] or "").strip(),
                str(question["option3"] or "").strip(),
                str(question["option4"] or "").strip()
            ]

            key = correct_raw.casefold()

            answer_map = {
                "a": 0, "option a": 0, "option1": 0,
                "option 1": 0, "1": 0,
                "b": 1, "option b": 1, "option2": 1,
                "option 2": 1, "2": 1,
                "c": 2, "option c": 2, "option3": 2,
                "option 3": 2, "3": 2,
                "d": 3, "option d": 3, "option4": 3,
                "option 4": 3, "4": 3
            }

            if key in answer_map:
                correct_text = options[answer_map[key]]
            else:
                correct_text = correct_raw

            # Case-insensitive comparison
            if answer and answer.casefold() == correct_text.casefold():
                score += 1

        print("FINAL SCORE:", score, "/", total_questions)

        # Save result
        conn.execute("""
            INSERT INTO quiz_results
            (student_id, quiz_id, score, total_questions)
            VALUES (?, ?, ?, ?)
        """, (
            session["user_id"],
            quiz_id,
            score,
            total_questions
        ))

        conn.commit()
        conn.close()

        return render_template(
            "quiz_result.html",
            quiz=quiz,
            score=score,
            total=total_questions
        )

    conn.close()

    return render_template(
        "take_quiz.html",
        quiz=quiz,
        questions=questions
    )











if __name__ == "__main__":
    create_table()
    app.run(debug=True)

    