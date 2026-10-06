import sys
import json
from app import create_app
from utils import load_users, save_users

app = create_app()
client = app.test_client()

# Clean up any previous test accounts for idempotency
users = load_users()
test_emails = {"rahul1@test.com", "rahul2@test.com", "rahul3@test.com", "rahul4@test.com", "different@test.com"}
to_del = [k for k, v in users.items() if isinstance(v, dict) and v.get("email") in test_emails]
for k in to_del:
    del users[k]
save_users(users)

results = {}

# TEST 1: Register Outside student: Name "Rahul Das", Email "rahul1@test.com", Password "123"
# Expected: Created successfully.
res1 = client.post("/signup", data={
    "name": "Rahul Das",
    "email": "rahul1@test.com",
    "password": "123",
    "confirm_password": "123"
}, follow_redirects=True)
users = load_users()
found1 = any(isinstance(v, dict) and v.get("name") == "Rahul Das" and v.get("email") == "rahul1@test.com" and v.get("user_type") == "EXTERNAL" for v in users.values())
results["TEST 1"] = "PASS" if found1 and b"created successfully" in res1.data.lower() else "FAIL"

# TEST 2: Register another Outside student with same name: Name "Rahul Das", Email "rahul2@test.com", Password "123"
# Expected: Created successfully (same name allowed).
res2 = client.post("/signup", data={
    "name": "Rahul Das",
    "email": "rahul2@test.com",
    "password": "123",
    "confirm_password": "123"
}, follow_redirects=True)
users = load_users()
found2 = any(isinstance(v, dict) and v.get("name") == "Rahul Das" and v.get("email") == "rahul2@test.com" and v.get("user_type") == "EXTERNAL" for v in users.values())
results["TEST 2"] = "PASS" if found2 and b"created successfully" in res2.data.lower() else "FAIL"

# TEST 3: Register another student with: Name "Another Student", Email "rahul1@test.com", Password "123"
# Expected: REJECTED, Error: "Email already exists. Please use a different email."
res3 = client.post("/signup", data={
    "name": "Another Student",
    "email": "rahul1@test.com",
    "password": "123",
    "confirm_password": "123"
}, follow_redirects=True)
results["TEST 3"] = "PASS" if b"Email already exists. Please use a different email." in res3.data else "FAIL"

# Admin session setup
with client.session_transaction() as sess:
    sess["admin"] = True

# TEST 4: Admin creates university student: Name "Rahul Das", Email "rahul3@test.com", Student Code "BWU/AIR/24/029", Password "123"
# Expected: Created successfully.
res4 = client.post("/admin/add_student", data={
    "name": "Rahul Das",
    "email": "rahul3@test.com",
    "password": "123",
    "program_code": "AIR",
    "department_name": "Computer Science and Engineering",
    "admission_year": "2024",
    "academic_year": "1st Year",
    "roll_number": "029"
}, follow_redirects=True)
users = load_users()
found4 = any(isinstance(v, dict) and v.get("name") == "Rahul Das" and v.get("email") == "rahul3@test.com" and v.get("student_code") == "BWU/AIR/24/029" and v.get("user_type") == "UNIVERSITY" for v in users.values())
results["TEST 4"] = "PASS" if found4 and b"added successfully" in res4.data.lower() else "FAIL"

# TEST 5: Admin creates another university student: Name "Rahul Das", Email "rahul4@test.com", Student Code "BWU/AIR/24/030", Password "123"
# Expected: Created successfully (same name allowed).
res5 = client.post("/admin/add_student", data={
    "name": "Rahul Das",
    "email": "rahul4@test.com",
    "password": "123",
    "program_code": "AIR",
    "department_name": "Computer Science and Engineering",
    "admission_year": "2024",
    "academic_year": "1st Year",
    "roll_number": "030"
}, follow_redirects=True)
users = load_users()
found5 = any(isinstance(v, dict) and v.get("name") == "Rahul Das" and v.get("email") == "rahul4@test.com" and v.get("student_code") == "BWU/AIR/24/030" and v.get("user_type") == "UNIVERSITY" for v in users.values())
results["TEST 5"] = "PASS" if found5 and b"added successfully" in res5.data.lower() else "FAIL"

# TEST 6: Admin tries to create: Name "Different Student", Email "different@test.com", Student Code "BWU/AIR/24/029", Password "123"
# Expected: REJECTED, Error: "Student Code already exists."
res6 = client.post("/admin/add_student", data={
    "name": "Different Student",
    "email": "different@test.com",
    "password": "123",
    "program_code": "AIR",
    "department_name": "Computer Science and Engineering",
    "admission_year": "2024",
    "academic_year": "1st Year",
    "roll_number": "029"
}, follow_redirects=True)
results["TEST 6"] = "PASS" if b"Student Code already exists." in res6.data else "FAIL"

# TEST 7: Admin tries to create: Name "Different Student", Email "rahul3@test.com", Student Code "BWU/AIR/24/031", Password "123"
# Expected: REJECTED, Error: "Email already exists. Please use a different email."
res7 = client.post("/admin/add_student", data={
    "name": "Different Student",
    "email": "rahul3@test.com",
    "password": "123",
    "program_code": "AIR",
    "department_name": "Computer Science and Engineering",
    "admission_year": "2024",
    "academic_year": "1st Year",
    "roll_number": "031"
}, follow_redirects=True)
results["TEST 7"] = "PASS" if b"Email already exists. Please use a different email." in res7.data else "FAIL"

# Clear admin session
with client.session_transaction() as sess:
    sess.clear()

# TEST 8: University student login with: Email "rahul3@test.com", Student Code "BWU/AIR/24/029", Password "123"
# Expected: Login successful ONLY when all 3 match the same student account.
res8_wrong_pw = client.post("/login", data={
    "login_type": "UNIVERSITY",
    "univ_email": "rahul3@test.com",
    "univ_student_code": "BWU/AIR/24/029",
    "univ_password": "wrong"
}, follow_redirects=True)
wrong_pw_rejected = b"Invalid email, student code, or password." in res8_wrong_pw.data

res8_wrong_code = client.post("/login", data={
    "login_type": "UNIVERSITY",
    "univ_email": "rahul3@test.com",
    "univ_student_code": "BWU/AIR/24/030",
    "univ_password": "123"
}, follow_redirects=True)
wrong_code_rejected = b"Invalid email, student code, or password." in res8_wrong_code.data

res8_correct = client.post("/login", data={
    "login_type": "UNIVERSITY",
    "univ_email": "rahul3@test.com",
    "univ_student_code": "BWU/AIR/24/029",
    "univ_password": "123"
}, follow_redirects=True)
correct_login = (b"Welcome back, Rahul Das!" in res8_correct.data)

results["TEST 8"] = "PASS" if (wrong_pw_rejected and wrong_code_rejected and correct_login) else "FAIL"

# TEST 9: Check users.json: Verify that multiple students named "Rahul Das" exist with different emails and student codes.
# Expected: All exist properly without overwriting each other.
users = load_users()
rahul_students = [
    v for v in users.values()
    if isinstance(v, dict) and (v.get("name") == "Rahul Das" or v.get("username") == "Rahul Das")
]
emails = set(v.get("email") for v in rahul_students)
results["TEST 9"] = "PASS" if len(rahul_students) >= 4 and len(emails) >= 4 else "FAIL"

print("\n===============================")
print("     AUTOMATED TEST RESULTS    ")
print("===============================")
all_pass = True
for k, v in results.items():
    print(f"{k}: {v}")
    if v != "PASS":
        all_pass = False

print(f"\nOVERALL RESULT: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
sys.exit(0 if all_pass else 1)
