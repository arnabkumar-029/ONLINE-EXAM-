import unittest
from app import create_app
import utils

class TestDepartmentNameValidation(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Backups
        self.users_backup = utils.load_users()
        self.programs_backup = utils.load_programs()

        # Admin login
        with self.client.session_transaction() as sess:
            sess['admin'] = True
            sess['user'] = 'admin'
            sess['user_id'] = 'admin'
            sess['role'] = 'admin'

    def tearDown(self):
        # Restore backups
        utils.save_users(self.users_backup)
        utils.save_programs(self.programs_backup)

    def test_01_html_form_attributes(self):
        """Verify HTML form contains 'Department Name *' and 'required' attribute."""
        res = self.client.get('/admin/students')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Check Add Student form
        self.assertIn('Department Name *', html)
        self.assertIn('name="department_name"', html)
        # Verify required attribute exists on department_name inputs
        self.assertIn('name="department_name" id="addStudentDept" placeholder="e.g. Computer Science and Engineering" required', html)
        self.assertIn('name="department_name" id="editStudentDept" placeholder="e.g. Computer Science and Engineering" required', html)

    def test_02_backend_rejects_missing_department_name(self):
        """Backend rejects student creation when department_name is omitted."""
        res = self.client.post('/admin/add_student', data={
            'name': 'Test Student 1',
            'email': 'dept_test1@example.com',
            'password': 'password123',
            'program_code': 'AIR',
            'admission_year': '2024',
            'academic_year': '1st Year',
            'roll_number': '701'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Department Name is required.', res.data)

        # Confirm user was NOT created
        user_match = utils.find_user_by_email('dept_test1@example.com')
        self.assertIsNone(user_match)

    def test_03_backend_rejects_empty_or_whitespace_department_name(self):
        """Backend rejects whitespace-only department_name values."""
        for ws_val in ['', '   ', '\t  \n ']:
            res = self.client.post('/admin/add_student', data={
                'name': 'Test Student Whitespace',
                'email': 'dept_test_ws@example.com',
                'password': 'password123',
                'program_code': 'AIR',
                'department_name': ws_val,
                'admission_year': '2024',
                'academic_year': '1st Year',
                'roll_number': '702'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Department Name is required.', res.data)
            user_match = utils.find_user_by_email('dept_test_ws@example.com')
            self.assertIsNone(user_match)

    def test_04_backend_accepts_valid_department_name(self):
        """Backend successfully creates student when department_name is provided."""
        res = self.client.post('/admin/add_student', data={
            'name': 'Valid Dept Student',
            'email': 'dept_test_valid@example.com',
            'password': 'password123',
            'program_code': 'AIR',
            'department_name': 'Robotics & Automation',
            'admission_year': '2024',
            'academic_year': '1st Year',
            'roll_number': '703'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'added successfully', res.data)

        user_match = utils.find_user_by_email('dept_test_valid@example.com')
        self.assertIsNotNone(user_match)
        _, u = user_match
        self.assertEqual(u['department_name'], 'Robotics & Automation')
        self.assertEqual(u['student_code'], 'BWU/AIR/24/703')

    def test_05_edit_student_department_name_validation(self):
        """Editing student also requires department_name."""
        # Create student first
        self.client.post('/admin/add_student', data={
            'name': 'Edit Dept Student',
            'email': 'dept_test_edit@example.com',
            'password': 'password123',
            'program_code': 'AIR',
            'department_name': 'Original Dept',
            'admission_year': '2024',
            'academic_year': '1st Year',
            'roll_number': '704'
        }, follow_redirects=True)

        user_match = utils.find_user_by_email('dept_test_edit@example.com')
        self.assertIsNotNone(user_match)
        user_key, u = user_match

        # Attempt to edit with whitespace department name
        res = self.client.post('/admin/edit_student', data={
            'user_id': u.get('id', user_key),
            'name': 'Edit Dept Student',
            'email': 'dept_test_edit@example.com',
            'program_code': 'AIR',
            'department_name': '   ',
            'admission_year': '2024',
            'academic_year': '1st Year',
            'roll_number': '704'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Department Name is required.', res.data)

        # Verify department was NOT changed to whitespace
        _, u_after = utils.find_user_by_email('dept_test_edit@example.com')
        self.assertEqual(u_after['department_name'], 'Original Dept')

if __name__ == '__main__':
    unittest.main()
