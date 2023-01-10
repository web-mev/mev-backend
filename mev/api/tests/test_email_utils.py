import unittest.mock as mock

from django.test import override_settings

from api.tests.base import BaseAPITestCase
from api.utilities.email_utils import send_activation_email, \
    send_password_reset_email, \
    send_email_to_admins, \
    ActivationEmail, \
    PasswordResetEmail, \
    AdminNotificationEmail


class MockRequest(object):
    def is_secure(self):
        return True


class EmailTests(BaseAPITestCase):

    def setUp(self):
        self.establish_clients()
        self.request = MockRequest()
        self.html = '''
            <html><body><p>hello!</p></body></html>
        '''
        self.plaintext = 'plaintext'

    @override_settings(FROM_EMAIL='admin@example.com')
    @mock.patch('api.utilities.email_utils.send_mail')
    @mock.patch('api.utilities.email_utils.render_to_string')
    def test_send_activation_email(self, mock_render, mock_send_mail):
        mock_render.side_effect = [self.plaintext, self.html]
        send_activation_email(self.request, self.regular_user_1)
        mock_send_mail.assert_called_with(ActivationEmail.subject,
                self.plaintext,
                'admin@example.com',
                [self.regular_user_1.email],
                html_message=self.html)

    @override_settings(FROM_EMAIL='admin@example.com')
    @mock.patch('api.utilities.email_utils.send_mail')
    @mock.patch('api.utilities.email_utils.render_to_string')
    def test_send_password_reset_email(self, mock_render, mock_send_mail):
        mock_render.side_effect = [self.plaintext, self.html]
        send_password_reset_email(self.request, self.regular_user_1)
        mock_send_mail.assert_called_with(PasswordResetEmail.subject,
                self.plaintext,
                'admin@example.com',
                [self.regular_user_1.email],
                html_message=self.html)

    @override_settings(FRONTEND_DOMAIN='something.com')
    @override_settings(SITE_NAME='WEBMEV')
    @mock.patch('api.utilities.email_utils.render_to_string')
    @mock.patch('api.utilities.email_utils.default_token_generator')
    @mock.patch('api.utilities.email_utils.encode_uid')
    def test_activation_email_template(self,
            mock_encode_uid,
            mock_token_generator,
            mock_render):
        mock_token_str = 'my_mock_token'
        mock_uid = 'abc123'
        mock_token_generator.make_token.return_value = mock_token_str
        mock_encode_uid.return_value = mock_uid
        message = ActivationEmail(self.request, self.regular_user_1)
        expected_context = {
            'activation_url': f'#/activate/{mock_uid}/{mock_token_str}',
            'site_name': 'WEBMEV',
            'protocol': 'https',
            'frontend_domain': 'something.com'
        }
        call1 = mock.call(
            ActivationEmail.plaintext_template_path,
            context=expected_context,
            request=self.request
        )
        call2 = mock.call(
            ActivationEmail.html_template_path,
            context=expected_context,
            request=self.request
        )
        mock_render.assert_called_with(ActivationEmail.html_template_path,
            context=expected_context,
            request=self.request)
        mock_render.assert_has_calls([call1, call2])

    @override_settings(FRONTEND_DOMAIN='something.com')
    @override_settings(SITE_NAME='WEBMEV')
    @mock.patch('api.utilities.email_utils.render_to_string')
    @mock.patch('api.utilities.email_utils.default_token_generator')
    @mock.patch('api.utilities.email_utils.encode_uid')
    def test_password_reset_email_template(self,
            mock_encode_uid,
            mock_token_generator,
            mock_render):
        mock_token_str = 'my_mock_token'
        mock_uid = 'abc123'
        mock_token_generator.make_token.return_value = mock_token_str
        mock_encode_uid.return_value = mock_uid
        message = PasswordResetEmail(self.request, self.regular_user_1)
        expected_context = {
            'reset_url': f'#/reset-password/{mock_uid}/{mock_token_str}',
            'site_name': 'WEBMEV',
            'protocol': 'https',
            'frontend_domain': 'something.com'
        }
        call1 = mock.call(
            PasswordResetEmail.plaintext_template_path,
            context=expected_context,
            request=self.request
        )
        call2 = mock.call(
            PasswordResetEmail.html_template_path,
            context=expected_context,
            request=self.request
        )
        mock_render.assert_has_calls([call1, call2])