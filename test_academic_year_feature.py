import unittest
import re
from app import create_app
import utils

class TestAcademicYearFeature(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Backup files
        self.users_backup = utils.load_users()
        self.programs_backup = utils.load_programs()

        # Login admin session
        with self.client.session_transaction() as sess:
            sess['admin'] = True
            sess['user'] = 'admin'
            sess['user_id'] = 'admin'
            sess['role'] = 'admin'

    def tearDown(self):
        # Restore backups
        utils.save_users(self.users_backup)
        utils.save_programs(self.programs_backup)

    def test_01_add_student_with_1st_year(self):
        """TEST 1: Select Academic Year = 1st Year. Student saved with academic_year = '1st Year'."""
        res = self.client.post('/admin/add_student', data={
            'name': 'Rahul Das',
            'email': 'rahul_1st@test.com',
            'password': 'password123',
            'program_code': 'AIR',
            'department_name': 'Computer Science and Engineering',
            'admission_year': '2024',
            'academic_year': '1st Year',
            'roll_number': '901'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'added successfully', res.data)

        user_match = utils.find_user_by_email('rahul_1st@test.com')
        self.assertIsNotNone(user_match)
        _, u = user_match
        self.assertEqual(u['academic_year'], '1st Year')
        self.assertEqual(u['student_code'], 'BWU/AIR/24/901')

    def test_02_add_student_with_3rd_year(self):
        """TEST 2: Select Academic Year = 3rd Year. Student saved with academic_year = '3rd Year'."""
        res = self.client.post('/admin/add_student', data={
            'name': 'Rahul Das',
            'email': 'rahul_3rd@test.com',
            'password': 'password123',
            'program_code': 'AIR',
            'department_name': 'Computer Science and Engineering',
            'admission_year': '2024',
            'academic_year': '3rd Year',
            'roll_number': '902'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'added successfully', res.data)

        user_match = utils.find_user_by_email('rahul_3rd@test.com')
        self.assertIsNotNone(user_match)
        _, u = user_match
        self.assertEqual(u['academic_year'], '3rd Year')
        self.assertEqual(u['student_code'], 'BWU/AIR/24/902')

    def test_03_add_student_with_7th_year(self):
        """TEST 3: Select Academic Year = 7th Year. Student saved successfully."""
        res = self.client.post('/admin/add_student', data={
            'name': 'Senior Scholar',
            'email': 'scholar_7th@test.com',
            'password': 'password123',
            'program_code': 'AIR',
            'department_name': 'Robotics Research',
            'admission_year': '2020',
            'academic_year': '7th Year',
            'roll_number': '001'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'added successfully', res.data)

        user_match = utils.find_user_by_email('scholar_7th@test.com')
        self.assertIsNotNone(user_match)
        _, u = user_match
        self.assertEqual(u['academic_year'], '7th Year')
        self.assertEqual(u['student_code'], 'BWU/AIR/20/001')

    def test_04_reject_empty_academic_year(self):
        """TEST 4: Leave Academic Year empty. Student creation rejected."""
        res = self.client.post('/admin/add_student', data={
            'name': 'No Year Student',
            'email': 'noyear@test.com',
            'password': 'password123',
            'program_code': 'AIR',
            'department_name': 'Computer Science',
            'admission_year': '2024',
            'academic_year': '',
            'roll_number': '031'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Academic Year is required.', res.data)

        # Confirm student was NOT created
        user_match = utils.find_user_by_email('noyear@test.com')
        self.assertIsNone(user_match)

    def test_05_edit_academic_year_student_code_unchanged(self):
        """TEST 5: Change Academic Year from 3rd Year -> 4th Year. Student updated. Student Code remains unchanged."""
        # Create student with 3rd Year
        self.client.post('/admin/add_student', data={
            'name': 'Promoted Student',
            'email': 'promoted@test.com',
            'password': 'password123',
            'program_code': 'AIR',
            'department_name': 'Computer Science and Engineering',
            'admission_year': '2024',
            'academic_year': '3rd Year',
            'roll_number': '055'
        }, follow_redirects=True)

        user_match = utils.find_user_by_email('promoted@test.com')
        self.assertIsNotNone(user_match)
        user_key, u = user_match
        initial_code = u['student_code']
        self.assertEqual(initial_code, 'BWU/AIR/24/055')
        self.assertEqual(u['academic_year'], '3rd Year')

        # Edit student to 4th Year
        res = self.client.post('/admin/edit_student', data={
            'user_id': u.get('id', user_key),
            'name': 'Promoted Student',
            'email': 'promoted@test.com',
            'program_code': 'AIR',
            'department_name': 'Computer Science and Engineering',
            'admission_year': '2024',
            'academic_year': '4th Year',
            'roll_number': '055'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'updated successfully', res.data)

        # Verify updated student
        _, u_after = utils.find_user_by_email('promoted@test.com')
        self.assertEqual(u_after['academic_year'], '4th Year')
        self.assertEqual(u_after['student_code'], initial_code)

    def test_06_frontend_form_dropdown_and_order(self):
        """Verify frontend Add & Edit student forms have required dropdown with exact 7 options in order."""
        res = self.client.get('/admin/students')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Check required labels and inputs
        self.assertIn('Academic Year *', html)
        self.assertIn('name="academic_year" id="addStudentAcadYear" required', html)
        self.assertIn('name="academic_year" id="editStudentAcadYear" required', html)

        # Check exact options present
        exact_options = ['1st Year', '2nd Year', '3rd Year', '4th Year', '5th Year', '6th Year', '7th Year']
        for opt in exact_options:
            self.assertIn(f'<option value="{opt}">{opt}</option>', html)
        self.assertNotIn('8th Year', html)

        # Check field order in Add Student modal:
        # Name * -> Email * -> Password * -> Program * -> Department Name * -> Admission Year * -> Academic Year * -> Roll Number *
        name_pos = html.find('id="addStudentName"')
        email_pos = html.find('id="addStudentEmail"')
        pw_pos = html.find('id="addStudentPassword"')
        prog_pos = html.find('id="addStudentProgram"')
        dept_pos = html.find('id="addStudentDept"')
        adm_pos = html.find('id="addStudentAdmYear"')
        acad_pos = html.find('id="addStudentAcadYear"')
        roll_pos = html.find('id="addStudentRoll"')

        self.assertTrue(0 < name_pos < email_pos < pw_pos < prog_pos < dept_pos < adm_pos < acad_pos < roll_pos)

    def test_07_existing_students_without_academic_year_safe(self):
        """Existing students without academic_year do not have a value invented."""
        users = utils.load_users()
        # Create a mock legacy student with no academic_year
        users['legacy_student_test'] = {
            'id': 'legacy_student_test',
            'name': 'Legacy Student',
            'username': 'Legacy Student',
            'email': 'legacy@test.com',
            'user_type': 'UNIVERSITY',
            'student_code': 'BWU/AIR/22/010',
            'program_code': 'AIR',
            'admission_year': 2022,
            'department_name': 'AI'
        }
        utils.save_users(users)

        # Reload users and verify academic_year is NOT invented
        reloaded = utils.load_users()
        self.assertNotIn('academic_year', reloaded['legacy_student_test'])

        # Check admin students table rendering handles it safely
        res = self.client.get('/admin/students')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Legacy Student', html)

if __name__ == '__main__':
    unittest.main()
