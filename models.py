# models.py
"""
SQLAlchemy Declarative Models for ExamForge / Online Examination Management System.
Matches existing JSON schemas (programs.json, users.json, questions.json, course_exams.json, results.json)
with complete relational integrity and preservation of all custom IDs.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Numeric,
    Boolean,
    Text,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    JSON,
    func
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Program(Base):
    """
    Academic Programs (programs.json)
    Primary key is auto-incrementing id; code is the unique academic program code (e.g., 'AIR', 'CSE').
    """
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("code", name="uq_programs_code"),
    )

    # Relationships
    users = relationship("User", back_populates="program")

    def to_dict(self):
        return {
            "code": self.code,
            "name": self.name
        }


class User(Base):
    """
    User & Student Accounts (users.json)
    Preserves unique IDs (e.g. 'user_7b2f4c91a0', 'admin', 'arnab_kumar').
    NOTE: Student names ('username' / 'name') are NOT unique per system requirements.
    Only 'email' and 'student_code' have uniqueness constraints.
    """
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    username = Column(String(255), nullable=False)  # Student display name - NOT UNIQUE
    name = Column(String(255), nullable=True)      # Alias for student name
    email = Column(String(255), unique=True, nullable=False, index=True)
    pw_hash = Column(String(255), nullable=False)
    user_type = Column(String(20), nullable=False, default="EXTERNAL")  # UNIVERSITY, EXTERNAL, ADMIN
    student_code = Column(String(64), unique=True, nullable=True, index=True)  # e.g. BWU/AIR/24/029
    university_code = Column(String(20), nullable=True)  # e.g. BWU
    program_code = Column(String(20), ForeignKey("programs.code", onupdate="CASCADE", ondelete="SET NULL"), nullable=True)
    program_name = Column(String(255), nullable=True)
    department_name = Column(String(255), nullable=True)
    admission_year = Column(Integer, nullable=True)
    academic_year = Column(String(50), nullable=True)  # e.g. '1st Year', '2nd Year', '3rd Year'
    roll_number = Column(String(50), nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    program = relationship("Program", back_populates="users")
    results = relationship("ExamResult", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name or self.username,
            "email": self.email,
            "pw_hash": self.pw_hash,
            "password": self.pw_hash,
            "user_type": self.user_type,
            "student_code": self.student_code or "",
            "university_code": self.university_code or "",
            "program_code": self.program_code or "",
            "program_name": self.program_name or "",
            "department_name": self.department_name or "",
            "admission_year": self.admission_year,
            "academic_year": self.academic_year or "",
            "roll_number": self.roll_number or "",
            "is_admin": self.is_admin
        }


class Question(Base):
    """
    Question Bank (questions.json)
    Preserves unique IDs (e.g. 'Q-CS301-65F8C3', 'Q-GEN101-...').
    Supports both MCQ and DESCRIPTIVE question types with all taxonomy metadata.
    """
    __tablename__ = "questions"

    id = Column(String(64), primary_key=True)
    course_code = Column(String(50), nullable=False, index=True)
    course_name = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False, index=True)
    program_code = Column(String(20), nullable=True, default="ALL")
    program_name = Column(String(255), nullable=True)
    admission_year = Column(String(20), nullable=True, default="ALL")
    academic_year = Column(String(50), nullable=True, default="ALL")
    unit = Column(String(100), nullable=True)
    topic = Column(String(255), nullable=True)
    type = Column(String(20), nullable=False)  # MCQ or DESCRIPTIVE
    level = Column(String(20), nullable=False, default="Easy")  # Easy, Medium, Hard
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # List of MCQ options
    correct = Column(Text, nullable=True)  # Correct MCQ option string
    answer_key = Column(Text, nullable=True)  # Model answer / scoring rubric for DESCRIPTIVE
    max_marks = Column(Numeric(5, 2), default=5.0)
    source = Column(String(20), nullable=False, default="MANUAL")  # MANUAL or AI
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    exam_associations = relationship("CourseExamQuestion", back_populates="question", cascade="all, delete-orphan")

    def to_dict(self):
        opts = self.options if isinstance(self.options, list) else []
        res = {
            "id": self.id,
            "course_code": self.course_code,
            "course_name": self.course_name,
            "subject": self.subject,
            "program_code": self.program_code or "ALL",
            "program_name": self.program_name or "",
            "admission_year": self.admission_year or "ALL",
            "academic_year": self.academic_year or "ALL",
            "unit": self.unit or "",
            "topic": self.topic or "",
            "type": self.type,
            "level": self.level,
            "question": self.question_text,
            "q": self.question_text,
            "source": self.source
        }
        if self.type == "MCQ":
            res["options"] = opts
            res["a"] = opts
            res["correct"] = self.correct or ""
        else:
            res["answer_key"] = self.answer_key or ""
            res["model_answer"] = self.answer_key or ""
            res["max_marks"] = float(self.max_marks or 5.0)
        return res


class CourseExam(Base):
    """
    Scheduled Course Examinations (course_exams.json)
    Preserves unique IDs (e.g. 'EXAM-CS301-MIDTERM').
    """
    __tablename__ = "course_exams"

    id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False)
    course_code = Column(String(50), nullable=False, index=True)
    course_name = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    exam_type = Column(String(20), nullable=False, default="MCQ")  # MCQ, DESCRIPTIVE, MIXED, ALL
    exam_date = Column(Date, nullable=True)
    start_time = Column(String(20), nullable=True)  # e.g. '10:00'
    end_time = Column(String(20), nullable=True)    # e.g. '12:00'
    duration = Column(Integer, nullable=False, default=60)  # minutes
    num_questions = Column(Integer, nullable=False, default=10)
    difficulty = Column(String(20), nullable=False, default="All")
    status = Column(String(20), nullable=False, default="Draft")  # Draft, Published, Closed
    target_mode = Column(String(30), nullable=False, default="PROGRAM_BATCH_YEAR")  # PROGRAM_BATCH_YEAR, SPECIFIC_STUDENTS, ALL_STUDENTS
    program_code = Column(String(20), nullable=True)
    program_name = Column(String(255), nullable=True)
    admission_year = Column(String(20), nullable=True)
    academic_year = Column(String(50), nullable=True)
    all_in_batch = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    question_associations = relationship(
        "CourseExamQuestion",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="CourseExamQuestion.sort_order"
    )
    targeted_students = relationship(
        "CourseExamTargetedStudent",
        back_populates="exam",
        cascade="all, delete-orphan"
    )
    results = relationship("ExamResult", back_populates="course_exam")

    def to_dict(self):
        qids = [assoc.question_id for assoc in self.question_associations]
        scodes = [ts.student_code for ts in self.targeted_students]
        return {
            "id": self.id,
            "title": self.title,
            "course_code": self.course_code,
            "course_name": self.course_name,
            "subject": self.subject,
            "description": self.description or "",
            "exam_type": self.exam_type,
            "exam_date": self.exam_date.strftime("%Y-%m-%d") if self.exam_date else "",
            "start_time": self.start_time or "",
            "end_time": self.end_time or "",
            "duration": self.duration,
            "num_questions": self.num_questions,
            "difficulty": self.difficulty,
            "status": self.status,
            "target_mode": self.target_mode,
            "program_code": self.program_code or "",
            "program_name": self.program_name or "",
            "admission_year": self.admission_year or "",
            "academic_year": self.academic_year or "",
            "all_in_batch": self.all_in_batch,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
            "question_ids": qids,
            "student_codes": scodes
        }


class CourseExamQuestion(Base):
    """
    Selected Questions for Course Exams (join table preserving question_ids list).
    """
    __tablename__ = "course_exam_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String(64), ForeignKey("course_exams.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String(64), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    sort_order = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),
    )

    # Relationships
    exam = relationship("CourseExam", back_populates="question_associations")
    question = relationship("Question", back_populates="exam_associations")


class CourseExamTargetedStudent(Base):
    """
    Targeted Specific Students for Course Exams (join table preserving student_codes list).
    """
    __tablename__ = "course_exam_targeted_students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exam_id = Column(String(64), ForeignKey("course_exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_code = Column(String(64), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("exam_id", "student_code", name="uq_exam_student_code"),
    )

    # Relationships
    exam = relationship("CourseExam", back_populates="targeted_students")


class ExamResult(Base):
    """
    Student Exam Submissions & Practice Quiz History (results.json).
    Links to User via user_id and optionally to CourseExam via course_exam_id (NULL for practice).
    """
    __tablename__ = "exam_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_key = Column(String(255), nullable=False, index=True)  # Legacy username/id key
    course_exam_id = Column(String(64), ForeignKey("course_exams.id", ondelete="SET NULL"), nullable=True, index=True)
    exam_title = Column(String(255), nullable=False, default="Practice Examination")
    course_code = Column(String(50), nullable=True)
    score = Column(Numeric(6, 2), nullable=False, default=0.0)
    total = Column(Numeric(6, 2), nullable=False, default=0.0)
    time_taken = Column(String(50), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    descriptive_reports = Column(JSON, nullable=True)  # AI grading and rubric feedback
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="results")
    course_exam = relationship("CourseExam", back_populates="results")

    def to_history_dict(self):
        res = {
            "score": float(self.score),
            "total": float(self.total),
            "time_taken": self.time_taken or "",
            "date": self.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if self.submitted_at else "",
            "exam_title": self.exam_title,
            "course_code": self.course_code or ""
        }
        if self.course_exam_id:
            res["course_exam_id"] = self.course_exam_id
        if self.descriptive_reports:
            res["descriptive_reports"] = self.descriptive_reports
        return res
