# 📝 Online Exam System

A secure and user-friendly **Online Examination Portal** built using **Python Flask** for managing online exams with instant results and admin controls.

---

## 🚀 Main Features

### 👨‍🎓 Student Panel
- Login / Logout
- Attempt online exams
- Automatic result calculation
- Leaderboard view

### 👨‍🏫 Admin Panel
- Secure admin authentication
- Add / update / delete exam questions
- View student results & exam statistics
- Manage exam system easily

---

## 🛠 Technologies Used

| Area | Technology |
|------|------------|
| Backend | Python Flask |
| Frontend | HTML, CSS, JavaScript |
| Data Storage | JSON Files |
| Deployment | Render (Gunicorn + requirements.txt) |

---

## 🔐 Admin Login

| Field | Details |
|-------|---------|
| Username | `admin` |
| Password | `admin123` |

> You can change admin credentials anytime inside `users.json`.

---

## 🌍 Live Deployment

🖥 Hosted on Render  
👉 https://arnab-kumar-examforge.onrender.com

> If the website is sleeping, first visit may take 10-15 sec to load.

---

## ▶️ How to Run Locally

```bash
# Create virtual environment (optional)
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install required libraries
pip install -r requirements.txt

# Start development server
python app.py
