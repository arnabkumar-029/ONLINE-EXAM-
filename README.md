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

| Field | Details |
|-------|---------|
| **Username** | `admin` |
| **Password** | `admin123` |

> ⚠️ **Note:** Change the default admin credentials before using the system in a production environment.
---

## 🌍 Live Deployment

🖥 Hosted on **Render**

👉 https://arnab-kumar-examforge.onrender.com

> If the website is sleeping, the first request may take a few seconds to start the server.

---

## ▶️ How to Run Locally

```
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
```
---

> [!NOTE]
> 🔮 **Future Updates**
>
> 👨‍🎓 **Student Attendance-Based Course Exams**
> - Attendance-based eligibility for course examinations
> - Students can be allowed or restricted from attempting an exam based on attendance percentage
> - Attendance records can be connected with course and student information
> - Admin can configure minimum attendance requirements for examinations
>
> 🤖 **AI Exam & Practice System**
> - Advanced AI-powered examination generation
> - AI-generated practice examinations
> - Personalized questions based on student performance
> - Adaptive difficulty based on previous attempts
> - AI-powered performance analysis
> - Intelligent recommendations for weak topics
>
> 📱 **QR / Scanner-Based Questions**
> - QR code-based question access
> - Scanner-based question identification
> - Scan a QR code to load a specific question or examination
> - Useful for classroom activities and practical examinations
> - Support for QR-based attendance and examination workflows
>
> 📊 **Advanced Student Analytics**
> - Detailed student performance reports
> - Subject-wise performance analysis
> - Topic-wise strengths and weaknesses
> - Progress tracking over multiple examinations
> - Advanced admin analytics dashboard
>
> 🔒 **Enhanced Examination Security**
> - Improved exam-session security
> - Secure examination access
> - Anti-cheating mechanisms
> - Better monitoring and examination controls
>
> 📱 **Modern Examination Experience**
> - Improved responsive design
> - Mobile-friendly examination interface
> - Better accessibility
> - More interactive dashboards
> - Enhanced examination progress tracking

-----------------------------------------------------------------------------------


## 🏗️ System Architecture

```mermaid
flowchart TD
    A[👨‍🎓 Student] --> B[🌐 Online Exam Portal]
    C[👨‍🏫 Admin] --> B

    B --> D[🔐 Authentication]

    D --> E{User Type}

    E -->|University Student| F[🎓 Student Dashboard]
    E -->|External Candidate| G[🎯 Test Yourself]
    E -->|Admin| H[⚙️ Admin Dashboard]

    F --> I[📚 Course Exams]
    F --> G

    I --> J{Eligibility Check}
    J -->|Eligible| K[📝 Start Course Exam]
    J -->|Not Eligible| L[🚫 Access Restricted]

    G --> M[🎯 Choose Practice Exam]

    M --> N{Exam Type}
    N -->|MCQ| O[❓ MCQ]
    N -->|Descriptive| P[✍️ Descriptive]
    N -->|Mixed| Q[🔀 Mixed]

    K --> R[⏱️ Exam Engine]
    O --> R
    P --> R
    Q --> R

    R --> S[📋 Questions]
    R --> T[⏳ Timer]
    R --> U[➡️ Navigation]
    R --> V[📤 Submit Exam]

    V --> W[🧮 Result Calculation]
    W --> X[📊 Result]
    X --> Y[🏆 Leaderboard]
    X --> Z[📜 Exam History]

    H --> H1[👥 Student Management]
    H --> H2[📚 Course Exam Management]
    H --> H3[📝 Question Bank]
    H --> H4[🤖 AI Question Generator]
    H --> H5[📊 Results & Statistics]

    H1 --> DB[(🗄️ PostgreSQL)]
    H2 --> DB
    H3 --> DB
    H5 --> DB

    H4 --> AI[🤖 Google Gemini]
    AI --> H4
    H4 --> DB

    R --> DB
    W --> DB
    F --> DB
    G --> DB

    DB --> SUPA[☁️ Supabase PostgreSQL]

    B --> REN[🚀 Render]
    REN --> GUN[🐍 Gunicorn]
    GUN --> B

🔄 Examination Workflow
#chatgpt-mermaid-_r_1ml_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_1ml_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_1ml_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_1ml_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-_r_1ml_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1ml_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_1ml_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_1ml_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_1ml_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_1ml_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_1ml_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_1ml_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1ml_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1ml_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_1ml_ p{margin:0;}#chatgpt-mermaid-_r_1ml_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1ml_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1ml_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1ml_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_1ml_ .label text,#chatgpt-mermaid-_r_1ml_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1ml_ .node rect,#chatgpt-mermaid-_r_1ml_ .node circle,#chatgpt-mermaid-_r_1ml_ .node ellipse,#chatgpt-mermaid-_r_1ml_ .node polygon,#chatgpt-mermaid-_r_1ml_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-_r_1ml_ .rough-node .label text,#chatgpt-mermaid-_r_1ml_ .node .label text,#chatgpt-mermaid-_r_1ml_ .image-shape .label,#chatgpt-mermaid-_r_1ml_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_1ml_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_1ml_ .rough-node .label,#chatgpt-mermaid-_r_1ml_ .node .label,#chatgpt-mermaid-_r_1ml_ .image-shape .label,#chatgpt-mermaid-_r_1ml_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_1ml_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_1ml_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1ml_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1ml_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-_r_1ml_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-_r_1ml_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_1ml_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1ml_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1ml_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-_r_1ml_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-_r_1ml_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1ml_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1ml_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_1ml_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1ml_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_1ml_ .icon-shape,#chatgpt-mermaid-_r_1ml_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_1ml_ .icon-shape p,#chatgpt-mermaid-_r_1ml_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-_r_1ml_ .icon-shape .label rect,#chatgpt-mermaid-_r_1ml_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1ml_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_1ml_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_1ml_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-_r_1ml_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_1ml_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_1ml_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_1ml_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1ml_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_1ml_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_1ml_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_1ml_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1ml_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-_r_1ml_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_1ml_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1ml_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_1ml_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_1ml_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1ml_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_1ml_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1ml_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_1ml_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_1ml_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_1ml_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_1ml_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-_r_1ml_ .node rect,#chatgpt-mermaid-_r_1ml_ .node circle,#chatgpt-mermaid-_r_1ml_ .node ellipse,#chatgpt-mermaid-_r_1ml_ .node polygon,#chatgpt-mermaid-_r_1ml_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_1ml_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_1ml_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-_r_1ml_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_1ml_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1ml_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}🔐 LoginUser Type🎓 Student Dashboard🎯 Test Yourself📚 Course Exam⚙️ Select Practice Exam🔎 Eligibility Check📝 Start Exam❓ Answer Questions⏱️ Timer➡️ Next / Previous / Skip📤 Submit🧮 Automatic Evaluation📊 Result📜 Exam History🏆 Leaderboard📈 Performance AnalysisUniversity StudentExternal Candidate




🤖 AI Question Generation Workflow
#chatgpt-mermaid-_r_1mu_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_1mu_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_1mu_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_1mu_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-_r_1mu_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1mu_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_1mu_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_1mu_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_1mu_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_1mu_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_1mu_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_1mu_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1mu_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1mu_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_1mu_ p{margin:0;}#chatgpt-mermaid-_r_1mu_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1mu_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1mu_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1mu_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_1mu_ .label text,#chatgpt-mermaid-_r_1mu_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1mu_ .node rect,#chatgpt-mermaid-_r_1mu_ .node circle,#chatgpt-mermaid-_r_1mu_ .node ellipse,#chatgpt-mermaid-_r_1mu_ .node polygon,#chatgpt-mermaid-_r_1mu_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-_r_1mu_ .rough-node .label text,#chatgpt-mermaid-_r_1mu_ .node .label text,#chatgpt-mermaid-_r_1mu_ .image-shape .label,#chatgpt-mermaid-_r_1mu_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_1mu_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_1mu_ .rough-node .label,#chatgpt-mermaid-_r_1mu_ .node .label,#chatgpt-mermaid-_r_1mu_ .image-shape .label,#chatgpt-mermaid-_r_1mu_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_1mu_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_1mu_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1mu_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1mu_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-_r_1mu_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-_r_1mu_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_1mu_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1mu_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1mu_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-_r_1mu_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-_r_1mu_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1mu_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1mu_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_1mu_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1mu_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_1mu_ .icon-shape,#chatgpt-mermaid-_r_1mu_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_1mu_ .icon-shape p,#chatgpt-mermaid-_r_1mu_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-_r_1mu_ .icon-shape .label rect,#chatgpt-mermaid-_r_1mu_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1mu_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_1mu_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_1mu_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-_r_1mu_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_1mu_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_1mu_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_1mu_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1mu_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_1mu_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_1mu_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_1mu_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1mu_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-_r_1mu_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_1mu_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1mu_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_1mu_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_1mu_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1mu_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_1mu_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1mu_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_1mu_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_1mu_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_1mu_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_1mu_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-_r_1mu_ .node rect,#chatgpt-mermaid-_r_1mu_ .node circle,#chatgpt-mermaid-_r_1mu_ .node ellipse,#chatgpt-mermaid-_r_1mu_ .node polygon,#chatgpt-mermaid-_r_1mu_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_1mu_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_1mu_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-_r_1mu_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_1mu_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1mu_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}👨‍🏫 Admin⚙️ Admin Dashboard🤖 AI Question Generator📚 Select Course📖 Select Subject📑 Select Unit / Topic🎚️ Select Difficulty❓ Select Question Type🚀 Generate Questions🤖 Google Gemini🧠 Generated Questions🔍 Validate Questions👀 Preview QuestionsAdmin Approval💾 Save to Question Bank🗄️ PostgreSQL📝 Available for ExamsApprovedRejected




🗄️ Database Architecture
#chatgpt-mermaid-_r_1na_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_1na_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_1na_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_1na_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-_r_1na_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1na_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_1na_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_1na_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_1na_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_1na_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_1na_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_1na_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1na_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1na_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_1na_ p{margin:0;}#chatgpt-mermaid-_r_1na_ .entityBox{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);}#chatgpt-mermaid-_r_1na_ .relationshipLabelBox{fill:rgb(48, 48, 48);opacity:0.7;background-color:rgb(48, 48, 48);}#chatgpt-mermaid-_r_1na_ .relationshipLabelBox rect{opacity:0.5;}#chatgpt-mermaid-_r_1na_ .labelBkg{background-color:rgba(48, 48, 48, 0.5);}#chatgpt-mermaid-_r_1na_ .edgeLabel{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1na_ .edgeLabel .label rect{fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1na_ .edgeLabel .label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1na_ .edgeLabel .label{fill:rgb(31, 78, 148);font-size:14px;}#chatgpt-mermaid-_r_1na_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1na_ .edge-pattern-dashed{stroke-dasharray:8,8;}#chatgpt-mermaid-_r_1na_ .node rect,#chatgpt-mermaid-_r_1na_ .node circle,#chatgpt-mermaid-_r_1na_ .node ellipse,#chatgpt-mermaid-_r_1na_ .node polygon{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-_r_1na_ .relationshipLine{stroke:rgb(175, 175, 175);stroke-width:1px;fill:none;}#chatgpt-mermaid-_r_1na_ .marker{fill:none!important;stroke:rgb(175, 175, 175)!important;stroke-width:1;}#chatgpt-mermaid-_r_1na_ [data-look=neo].labelBkg{background-color:rgba(48, 48, 48, 0.5);}#chatgpt-mermaid-_r_1na_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-_r_1na_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_1na_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_1na_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_1na_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1na_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_1na_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_1na_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_1na_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1na_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-_r_1na_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_1na_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1na_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_1na_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_1na_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1na_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_1na_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1na_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}USERSstringidstringnamestringemailstringpasswordstringuser_typestringstudent_codestringprogramstringprogram_codestringdepartmentstringadmission_yearstringacademic_yearstringroll_numberPROGRAMSstringidstringnamestringcodestringdepartmentQUESTIONSstringidstringcourse_codestringcourse_namestringsubjectstringunitstringtopicstringtypestringlevelstringsourceCOURSE_EXAMSstringidstringtitlestringcourse_codestringsubjectstringstatusstringstart_timestringend_timeCOURSE_EXAM_QUESTIONSstringexam_idstringquestion_idCOURSE_EXAM_TARGETED_STUDENTSstringexam_idstringstudent_idEXAM_RESULTSstringidstringuser_idstringcourse_exam_idstringscorestringtotalstringtime_takenstringsubmitted_atcontainsreceivescontainsselectedtargetsassignedgenerates




☁️ Deployment Architecture
#chatgpt-mermaid-_r_1o8_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(237, 237, 237);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-_r_1o8_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_1o8_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-_r_1o8_ .error-icon{fill:rgb(48, 48, 48);}#chatgpt-mermaid-_r_1o8_ .error-text{fill:rgb(237, 237, 237);stroke:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1o8_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-_r_1o8_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-_r_1o8_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-_r_1o8_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-_r_1o8_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-_r_1o8_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-_r_1o8_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1o8_ .marker.cross{stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1o8_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-_r_1o8_ p{margin:0;}#chatgpt-mermaid-_r_1o8_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1o8_ .cluster-label text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1o8_ .cluster-label span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1o8_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-_r_1o8_ .label text,#chatgpt-mermaid-_r_1o8_ span{fill:rgb(237, 237, 237);color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1o8_ .node rect,#chatgpt-mermaid-_r_1o8_ .node circle,#chatgpt-mermaid-_r_1o8_ .node ellipse,#chatgpt-mermaid-_r_1o8_ .node polygon,#chatgpt-mermaid-_r_1o8_ .node path{fill:rgb(9, 23, 44);stroke:rgb(31, 78, 148);stroke-width:1px;}#chatgpt-mermaid-_r_1o8_ .rough-node .label text,#chatgpt-mermaid-_r_1o8_ .node .label text,#chatgpt-mermaid-_r_1o8_ .image-shape .label,#chatgpt-mermaid-_r_1o8_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-_r_1o8_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-_r_1o8_ .rough-node .label,#chatgpt-mermaid-_r_1o8_ .node .label,#chatgpt-mermaid-_r_1o8_ .image-shape .label,#chatgpt-mermaid-_r_1o8_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-_r_1o8_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-_r_1o8_ .root .anchor path{fill:rgb(175, 175, 175)!important;stroke-width:0;stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1o8_ .arrowheadPath{fill:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1o8_ .edgePath .path{stroke:rgb(175, 175, 175);stroke-width:1px;}#chatgpt-mermaid-_r_1o8_ .flowchart-link{stroke:rgb(175, 175, 175);fill:none;}#chatgpt-mermaid-_r_1o8_ .edgeLabel{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_1o8_ .edgeLabel p{background-color:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1o8_ .edgeLabel rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1o8_ .labelBkg{background-color:rgba(0, 0, 0, 0.5);}#chatgpt-mermaid-_r_1o8_ .cluster rect{fill:rgb(48, 48, 48);stroke:rgba(255, 255, 255, 0.15);stroke-width:1px;}#chatgpt-mermaid-_r_1o8_ .cluster text{fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1o8_ .cluster span{color:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1o8_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(48, 48, 48);border:1px solid rgba(255, 255, 255, 0.15);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-_r_1o8_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(237, 237, 237);}#chatgpt-mermaid-_r_1o8_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-_r_1o8_ .icon-shape,#chatgpt-mermaid-_r_1o8_ .image-shape{background-color:rgb(0, 0, 0);text-align:center;}#chatgpt-mermaid-_r_1o8_ .icon-shape p,#chatgpt-mermaid-_r_1o8_ .image-shape p{background-color:rgb(0, 0, 0);padding:2px;}#chatgpt-mermaid-_r_1o8_ .icon-shape .label rect,#chatgpt-mermaid-_r_1o8_ .image-shape .label rect{opacity:0.5;background-color:rgb(0, 0, 0);fill:rgb(0, 0, 0);}#chatgpt-mermaid-_r_1o8_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-_r_1o8_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-_r_1o8_ .node .neo-node{stroke:rgb(31, 78, 148);}#chatgpt-mermaid-_r_1o8_ [data-look="neo"].node rect,#chatgpt-mermaid-_r_1o8_ [data-look="neo"].cluster rect,#chatgpt-mermaid-_r_1o8_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-_r_1o8_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1o8_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-_r_1o8_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-_r_1o8_-gradient);stroke-width:1px;}#chatgpt-mermaid-_r_1o8_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1o8_ [data-look="neo"].node .neo-line path{stroke:rgb(31, 78, 148);filter:none;}#chatgpt-mermaid-_r_1o8_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-_r_1o8_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1o8_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-_r_1o8_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-_r_1o8_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1o8_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-_r_1o8_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-_r_1o8_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_1o8_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(153, 206, 255);}#chatgpt-mermaid-_r_1o8_ .node tspan[font-weight="normal"],#chatgpt-mermaid-_r_1o8_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-_r_1o8_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-width:1px;}#chatgpt-mermaid-_r_1o8_ .node rect,#chatgpt-mermaid-_r_1o8_ .node circle,#chatgpt-mermaid-_r_1o8_ .node ellipse,#chatgpt-mermaid-_r_1o8_ .node polygon,#chatgpt-mermaid-_r_1o8_ .node path{fill:rgb(0, 40, 77);stroke:rgba(255, 255, 255, 0.1);stroke-width:1px;}#chatgpt-mermaid-_r_1o8_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-_r_1o8_ .node.mermaid-decision .label-container{fill:rgb(0, 14, 26);stroke:rgb(26, 62, 95);stroke-dasharray:2,2;}#chatgpt-mermaid-_r_1o8_ .edgePaths .flowchart-link{stroke:rgb(175, 175, 175);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-_r_1o8_ .marker{fill:rgb(175, 175, 175);stroke:rgb(175, 175, 175);}#chatgpt-mermaid-_r_1o8_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}👨‍🎓 Student / 👨‍🏫 Admin🌐 Web Browser🚀 Render🐍 Gunicorn🌐 Flask Application🔐 Authentication📝 Exam Engine⚙️ Admin Panel🤖 AI Question Generator☁️ Supabase PostgreSQL🤖 Google Gemini




🛠 Technologies Used
Area	Technology
Backend	Python Flask
Frontend	HTML, CSS, JavaScript
Database	PostgreSQL
AI	Google Gemini
Authentication	Flask Session + Password Hashing
Deployment	Render + Gunicorn
Database Hosting	Supabase PostgreSQL
Dependency Management	requirements.txt


🔐 Admin Login
Admin authentication is protected through the application's admin login system.
Field	Details
Username	admin
Password	admin123


⚠️ Note: Change the default admin credentials before using the system in a production environment.
