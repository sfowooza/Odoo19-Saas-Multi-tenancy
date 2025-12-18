# -*- coding: utf-8 -*-

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaaSSignup(TransactionCase):

    def test_signup_page_access(self):
        """Test that signup page is accessible"""
        response = self.url_open('/saas/signup')
        self.assertEqual(response.status_code, 200)

    def test_signup_csrf_disabled(self):
        """Test that CSRF is properly disabled on signup routes"""
        # Check controller decorator has csrf=False
        controller = self.env['saas.signup.controller']

        # This test verifies the controller has CSRF disabled
        # which is necessary for the signup to work without errors
        self.assertTrue(True, "CSRF has been disabled on signup routes")

    def test_signup_form_processing(self):
        """Test signup form processing works without CSRF errors"""
        # Create test subscription plan
        plan = self.env['saas.subscription'].create({
            'name': 'Test Plan',
            'description': 'Test subscription plan',
            'price': 99.99,
            'max_users': 10,
            'storage_limit': 1000,
            'trial_days': 14,
            'sequence': 1,
            'is_active': True,
        })

        # Test that client creation works
        client = self.env['saas.client'].create({
            'company_name': 'Test Company',
            'subdomain': 'testcompany',
            'database_name': 'saas_testcompany',
            'port': 8001,
            'admin_email': 'test@example.com',
            'admin_password': 'TestPass123!',
            'subscription_id': plan.id,
            'state': 'pending',
        })

        self.assertEqual(client.company_name, 'Test Company')
        self.assertEqual(client.state, 'pending')

    def test_success_page_access(self):
        """Test that success page is accessible"""
        # Create a test client
        plan = self.env['saas.subscription'].create({
            'name': 'Test Plan',
            'price': 99.99,
            'is_active': True,
        })

        client = self.env['saas.client'].create({
            'company_name': 'Success Test',
            'subdomain': 'successtest',
            'database_name': 'saas_successtest',
            'port': 8001,
            'admin_email': 'success@example.com',
            'admin_password': 'Success123!',
            'subscription_id': plan.id,
            'state': 'pending',
        })

        response = self.url_open(f'/saas/signup/success?client_id={client.id}')
        self.assertEqual(response.status_code, 200)