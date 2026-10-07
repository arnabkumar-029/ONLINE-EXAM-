-- ExamForge Supabase PostgreSQL Schema
-- Generated for Supabase Database: examforge
-- Matches SQLAlchemy models in models.py
-- Safe and idempotent: Uses IF NOT EXISTS for all objects

-- 1. programs
CREATE TABLE IF NOT EXISTS programs (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_programs_code ON programs (code);

-- 2. users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255) NOT NULL UNIQUE,
    pw_hash VARCHAR(255) NOT NULL,
    user_type VARCHAR(20) NOT NULL DEFAULT 'EXTERNAL',
    student_code VARCHAR(64) UNIQUE,
    university_code VARCHAR(20),
    program_code VARCHAR(20) REFERENCES programs(code) ON UPDATE CASCADE ON DELETE SET NULL,
    program_name VARCHAR(255),
    department_name VARCHAR(255),
    admission_year INTEGER,
    academic_year VARCHAR(50),
    roll_number VARCHAR(50),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);
CREATE INDEX IF NOT EXISTS ix_users_student_code ON users (student_code);

-- 3. questions
CREATE TABLE IF NOT EXISTS questions (
    id VARCHAR(64) PRIMARY KEY,
    course_code VARCHAR(50) NOT NULL,
    course_name VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    program_code VARCHAR(20) DEFAULT 'ALL',
    program_name VARCHAR(255),
    admission_year VARCHAR(20) DEFAULT 'ALL',
    academic_year VARCHAR(50) DEFAULT 'ALL',
    unit VARCHAR(100),
    topic VARCHAR(255),
    type VARCHAR(20) NOT NULL,
    level VARCHAR(20) NOT NULL DEFAULT 'Easy',
    question_text TEXT NOT NULL,
    options JSONB,
    correct TEXT,
    answer_key TEXT,
    max_marks NUMERIC(5, 2) DEFAULT 5.0,
    source VARCHAR(20) NOT NULL DEFAULT 'MANUAL',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_questions_course_code ON questions (course_code);
CREATE INDEX IF NOT EXISTS ix_questions_subject ON questions (subject);

-- 4. course_exams
CREATE TABLE IF NOT EXISTS course_exams (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    course_code VARCHAR(50) NOT NULL,
    course_name VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT,
    exam_type VARCHAR(20) NOT NULL DEFAULT 'MCQ',
    exam_date DATE,
    start_time VARCHAR(20),
    end_time VARCHAR(20),
    duration INTEGER NOT NULL DEFAULT 60,
    num_questions INTEGER NOT NULL DEFAULT 10,
    difficulty VARCHAR(20) NOT NULL DEFAULT 'All',
    status VARCHAR(20) NOT NULL DEFAULT 'Draft',
    target_mode VARCHAR(30) NOT NULL DEFAULT 'PROGRAM_BATCH_YEAR',
    program_code VARCHAR(20),
    program_name VARCHAR(255),
    admission_year VARCHAR(20),
    academic_year VARCHAR(50),
    all_in_batch BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_course_exams_course_code ON course_exams (course_code);

-- 5. course_exam_questions
CREATE TABLE IF NOT EXISTS course_exam_questions (
    id SERIAL PRIMARY KEY,
    exam_id VARCHAR(64) NOT NULL REFERENCES course_exams(id) ON DELETE CASCADE,
    question_id VARCHAR(64) NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    sort_order INTEGER DEFAULT 0,
    CONSTRAINT uq_exam_question UNIQUE (exam_id, question_id)
);
CREATE INDEX IF NOT EXISTS ix_course_exam_questions_exam_id ON course_exam_questions (exam_id);
CREATE INDEX IF NOT EXISTS ix_course_exam_questions_question_id ON course_exam_questions (question_id);

-- 6. course_exam_targeted_students
CREATE TABLE IF NOT EXISTS course_exam_targeted_students (
    id SERIAL PRIMARY KEY,
    exam_id VARCHAR(64) NOT NULL REFERENCES course_exams(id) ON DELETE CASCADE,
    student_code VARCHAR(64) NOT NULL,
    CONSTRAINT uq_exam_student_code UNIQUE (exam_id, student_code)
);
CREATE INDEX IF NOT EXISTS ix_course_exam_targeted_students_exam_id ON course_exam_targeted_students (exam_id);
CREATE INDEX IF NOT EXISTS ix_course_exam_targeted_students_student_code ON course_exam_targeted_students (student_code);

-- 7. exam_results
CREATE TABLE IF NOT EXISTS exam_results (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_key VARCHAR(255) NOT NULL,
    course_exam_id VARCHAR(64) REFERENCES course_exams(id) ON DELETE SET NULL,
    exam_title VARCHAR(255) NOT NULL DEFAULT 'Practice Examination',
    course_code VARCHAR(50),
    score NUMERIC(6, 2) NOT NULL DEFAULT 0.0,
    total NUMERIC(6, 2) NOT NULL DEFAULT 0.0,
    time_taken VARCHAR(50),
    submitted_at TIMESTAMP WITH TIME ZONE,
    descriptive_reports JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_exam_results_user_id ON exam_results (user_id);
CREATE INDEX IF NOT EXISTS ix_exam_results_user_key ON exam_results (user_key);
CREATE INDEX IF NOT EXISTS ix_exam_results_course_exam_id ON exam_results (course_exam_id);
