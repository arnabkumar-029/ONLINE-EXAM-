import sys
import unittest
from app import create_app
import utils

class TestProgramAndStudentManagement(unittest.TestCase):
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

    def test_01_add_program_and_duplicate_prevention(self):
        # 1. Add valid program
        res = self.client.post('/admin/add_program', data={
            'program_name': 'Bioinformatics',
            'program_code': 'BIO'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        prog = utils.get_program_by_code('BIO')
        self.assertIsNotNone(prog)
        self.assertEqual(prog['name'], 'Bioinformatics')

        # 2. Try adding duplicate program code
        res2 = self.client.post('/admin/add_program', data={
            'program_name': 'Biological Sciences',
            'program_code': 'BIO'
        }, follow_redirects=True)
        self.assertIn(b'Program Code already exists.', res2.data)

        # 3. Try adding duplicate program name
        res3 = self.client.post('/admin/add_program', data={
            'program_name': 'Bioinformatics',
            'program_code': 'BINF'
        }, follow_redirects=True)
        self.assertIn(b'Program Name already exists.', res3.data)

    def test_02_add_student_with_program_dropdown(self):
        # Add program first
        self.client.post('/admin/add_program', data={
            'program_name': 'Robotics Engineering',
            'program_code': 'ROB'
        }, follow_redirects=True)

        # Add university student selecting program_code='ROB'
        res = self.client.post('/admin/add_student', data={
            'name': 'Priya Sharma',
            'email': 'priya.sharma@example.com',
            'password': 'password123',
            'program_code': 'ROB',
            'department_name': 'Dept of Robotics & Automation',
            'admission_year': '2024',
            'academic_year': '3rd Year',
            'roll_number': '015'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify student record in users.json
        res_found = utils.find_user_by_email('priya.sharma@example.com')
        self.assertIsNotNone(res_found)
        _, user = res_found
        self.assertEqual(user['student_code'], 'BWU/ROB/24/015')
        self.assertEqual(user['program_code'], 'ROB')
        self.assertEqual(user['program_name'], 'Robotics Engineering')
        self.assertEqual(user['department_name'], 'Dept of Robotics & Automation')
        self.assertEqual(user['academic_year'], '3rd Year')
        self.assertEqual(user['roll_number'], '015')
        self.assertEqual(user['admission_year'], 2024)
        self.assertEqual(user['user_type'], 'UNIVERSITY')

        # Verify student login with 3 credentials
        login_res = self.client.post('/login', data={
            'login_type': 'university',
            'univ_email': 'priya.sharma@example.com',
            'univ_student_code': 'BWU/ROB/24/015',
            'univ_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Welcome', login_res.data)

    def test_03_delete_program_restrictions(self):
        # Program with assigned students cannot be deleted
        # 'AIR' has assigned students in test data
        air_count = utils.count_students_in_program('AIR')
        self.assertGreater(air_count, 0)

        res = self.client.post('/admin/delete_program/AIR', follow_redirects=True)
        self.assertIn(b'This program is currently assigned to students and cannot be deleted.', res.data)
        self.assertIsNotNone(utils.get_program_by_code('AIR'))

        # Add new empty program and delete it
        self.client.post('/admin/add_program', data={
            'program_name': 'Environmental Engineering',
            'program_code': 'ENV'
        }, follow_redirects=True)
        self.assertIsNotNone(utils.get_program_by_code('ENV'))

        del_res = self.client.post('/admin/delete_program/ENV', follow_redirects=True)
        self.assertIn(b'deleted successfully', del_res.data)
        self.assertIsNone(utils.get_program_by_code('ENV'))

    def test_04_edit_student_program_cascade(self):
        # Create student with BAR
        self.client.post('/admin/add_student', data={
            'name': 'Amit Roy',
            'email': 'amit.roy@example.com',
            'password': 'password123',
            'program_code': 'BAR',
            'department_name': 'Humanities',
            'admission_year': '2023',
            'academic_year': '2nd Year',
            'roll_number': '088'
        }, follow_redirects=True)

        found_amit = utils.find_user_by_email('amit.roy@example.com')
        self.assertIsNotNone(found_amit)
        amit_key, user = found_amit
        self.assertEqual(user['student_code'], 'BWU/BAR/23/088')

        # Edit student to CSE and new roll 099 and 3rd Year
        res = self.client.post('/admin/edit_student', data={
            'user_id': user.get('id', amit_key),
            'name': 'Amit Roy',
            'email': 'amit.roy@example.com',
            'password': '',
            'program_code': 'CSE',
            'department_name': 'Computer Science',
            'admission_year': '2023',
            'academic_year': '3rd Year',
            'roll_number': '099'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        _, updated_user = utils.find_user_by_email('amit.roy@example.com')
        self.assertEqual(updated_user['program_code'], 'CSE')
        self.assertEqual(updated_user['program_name'], 'Computer Science & Engineering')
        self.assertEqual(updated_user['student_code'], 'BWU/CSE/23/099')
        self.assertEqual(updated_user['department_name'], 'Computer Science')
        self.assertEqual(updated_user['academic_year'], '3rd Year')

    def test_05_duplicate_name_allowed(self):
        # Add student 1
        self.client.post('/admin/add_student', data={
            'name': 'Rahul Das',
            'email': 'rahul1@example.com',
            'password': 'password123',
            'program_code': 'CSE',
            'department_name': 'Computer Science',
            'admission_year': '2024',
            'academic_year': '1st Year',
            'roll_number': '101'
        }, follow_redirects=True)

        # Add student 2 with identical name 'Rahul Das' but different email/roll
        res = self.client.post('/admin/add_student', data={
            'name': 'Rahul Das',
            'email': 'rahul2@example.com',
            'password': 'password123',
            'program_code': 'CSE',
            'department_name': 'Computer Science',
            'admission_year': '2024',
            'academic_year': '1st Year',
            'roll_number': '102'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'added successfully', res.data)

        _, u1 = utils.find_user_by_email('rahul1@example.com')
        _, u2 = utils.find_user_by_email('rahul2@example.com')
        self.assertEqual(u1['username'], 'Rahul Das')
        self.assertEqual(u2['username'], 'Rahul Das')
        self.assertNotEqual(u1['student_code'], u2['student_code'])

if __name__ == '__main__':
    unittest.main()
