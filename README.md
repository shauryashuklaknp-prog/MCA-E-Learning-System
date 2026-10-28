# MCA E-Learning System

A Flask-based MCA mini project for an online learning portal. Students can register and log in, browse courses and learning materials, take quizzes, and view quiz results. The admin panel can manage courses, materials, quizzes, questions, and student/result views.

## Technology Stack

- Python
- Flask
- SQLite
- HTML and CSS
- JavaScript

## Project Structure

```text
E_LEARNING_SYSTEM/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── database.db          # created locally when the app starts; not included in Git
├── static/
│   ├── script.js
│   └── style.css
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── login.html
│   ├── dashboard.html
│   ├── courses.html
│   ├── course_details.html
│   ├── take_quiz.html
│   ├── quiz_result.html
│   ├── my_results.html
│   └── ... other admin and result templates
└── uploads/             # add your own sample learning files locally
```

## Requirements

- Python 3.10 or newer
- pip

## Run on Windows

1. Download or clone this repository.
2. Open the project folder in VS Code.
3. Open Terminal (**Terminal → New Terminal**).
4. Create a virtual environment:

   ```powershell
   py -m venv venv
   ```

5. Activate it:

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run the commands below in Command Prompt instead:

   ```bat
   venv\Scripts\activate.bat
   ```

6. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

7. Start the application:

   ```powershell
   python app.py
   ```

8. Open `http://127.0.0.1:5000` in your browser.

The SQLite database is created locally when the application starts. The repository intentionally does not include the previous local database or uploaded personal PDFs, because those may contain private student information. Add courses and materials again using the admin panel, or add only non-sensitive demo data.

## Demo Admin Login

The current project code creates a demo administrator account:

- Username: `admin`
- Password: `admin123`

This is for local demonstration only. Do not deploy this project publicly with the demo credentials or use real student data without first improving authentication, password storage, session-secret handling, and production configuration.

## Main Features

- Student registration and login
- Course listing and course details
- Learning materials (such as notes, PDFs, videos, and links)
- Quizzes and automatic score calculation
- Student quiz-result history
- Admin pages for managing courses, materials, quizzes, questions, and viewing results

## Notes

- This is an academic demonstration project, not a production-ready learning platform.
- Keep `database.db`, personal documents, credentials, and private uploaded files out of public Git repositories.
- The Flask development server is intended for local testing only.
