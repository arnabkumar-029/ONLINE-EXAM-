# 📝 Online Exam System

A secure, modern, and user-friendly **Online Examination Portal** built using **Python Flask** for conducting online exams, managing questions, evaluating student performance, and providing instant results with powerful admin controls.

---

## 🚀 Main Features

### 👨‍🎓 Student Panel
- Secure Login / Logout
- Attempt online examinations
- Course-based examinations
- Practice examinations through **Test Yourself**
- MCQ, Descriptive, and Mixed question types
- Difficulty-based practice: Easy, Medium, Hard
- Automatic result calculation
- View examination history
- View leaderboard and performance
- Personalized exam experience based on student eligibility
- Secure access to assigned course examinations

### 👨‍🏫 Admin Panel
- Secure admin authentication
- Add / update / delete examination questions
- Manage MCQ and Descriptive questions
- Organize questions by course, subject, unit, topic, and difficulty
- AI-powered question generation
- Create and manage course examinations
- Select questions from the question bank
- Assign course examinations to eligible students
- Manage student information and academic details
- View student results and examination history
- View exam statistics and performance
- Manage the examination system easily

---

## 🤖 AI-Powered Features

- AI-assisted examination question generation
- Generate MCQ and Descriptive questions
- Generate questions based on subject, topic, unit, and difficulty
- AI-powered **Test Yourself** practice mode
- Personalized practice examination experience
- Automatic question generation through the AI question engine

---

## 📝 Question Management

The system supports a structured question bank with:

- MCQ Questions
- Descriptive Questions
- Mixed Examinations
- Easy / Medium / Hard difficulty levels
- Course-wise questions
- Subject-wise questions
- Unit-wise questions
- Topic-wise questions
- Manual questions
- AI-generated questions
- Question selection for specific course examinations

---

## 🛠 Technologies Used

| Area | Technology |
|------|------------|
| Backend | Python Flask |
| Frontend | HTML, CSS, JavaScript |
| Database | PostgreSQL |
| AI | Google Gemini |
| Authentication | Flask Session + Password Hashing |
| Deployment | Render + Gunicorn |
| Database Hosting | Supabase PostgreSQL |
| Dependency Management | requirements.txt |

---

## 🔐 Admin Login

Admin authentication is protected through the application's admin login system.

> **For security reasons, admin credentials should not be published in the README.**

> Admin credentials can be managed securely through the application's authentication configuration/database.

---

## 🌍 Live Deployment

🖥 Hosted on **Render**

👉 https://arnab-kumar-examforge.onrender.com

> If the website is sleeping, the first request may take a few seconds to start the server.

---

## ▶️ How to Run Locally

```bash
# Create virtual environment (optional)
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

# Install required libraries
pip install -r requirements.txt

# Start development server
python app.py


---

<details>
<summary>🔮 Future Updates</summary>

<br>

### 👨‍🎓 Student Attendance-Based Course Exams
- Attendance-based eligibility for course examinations
- Students can be allowed or restricted from attempting an exam based on attendance percentage
- Attendance records can be connected with course and student information
- Admin can configure minimum attendance requirements for examinations

### 🤖 AI Exam & Practice System
- Advanced AI-powered examination generation
- AI-generated practice examinations
- Personalized questions based on student performance
- Adaptive difficulty based on previous attempts
- AI-powered performance analysis
- Intelligent recommendations for weak topics

### 📱 QR / Scanner-Based Questions
- QR code-based question access
- Scanner-based question identification
- Scan a QR code to load a specific question or examination
- Useful for classroom activities and practical examinations
- Support for QR-based attendance and examination workflows

### 📊 Advanced Student Analytics
- Detailed student performance reports
- Subject-wise performance analysis
- Topic-wise strengths and weaknesses
- Progress tracking over multiple examinations
- Advanced admin analytics dashboard

### 🔒 Enhanced Examination Security
- Improved exam-session security
- Secure examination access
- Anti-cheating mechanisms
- Better monitoring and examination controls

### 📱 Modern Examination Experience
- Improved responsive design
- Mobile-friendly examination interface
- Better accessibility
- More interactive dashboards
- Enhanced examination progress tracking

</details>
