import logging

from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .basic_utils import encode_uid

logger = logging.getLogger(__name__)


class BaseEmailMessage(object):

    # by default, we don't require an HTML template.
    # Child classes can declare this if they want to
    # send html email messages
    html_template_path = None

    def __init__(self,
                 context=None,
                 request=None):

        self.request = request
        self.context = {} if context is None else context
        self.from_email = settings.FROM_EMAIL

        # augment the provided context with the "common" fields
        self._get_common_context()

        # read/render the templates:
        self.plaintext_content = render_to_string(self.plaintext_template_path,
                                                  context=self.context,
                                                  request=self.request)
        if self.html_template_path is not None:
            self.html_content = render_to_string(self.html_template_path,
                                                 context=self.context,
                                                 request=self.request)
        else:
            self.html_content = None

    def send(self, recipient_list):
        success = send_mail(self.subject,
                            self.plaintext_content,
                            settings.FROM_EMAIL,
                            recipient_list,
                            html_message=self.html_content)
        if not success:
            logger.info(f'Failed to send email to {",".join(recipient_list)}')

    def _get_common_context(self):
        '''
        Returns a dictionary with common "context" parameters
        for email templates. These are parameters that are
        often injected into emails (such as frontend domain).

        The context parameters are not required to be in the
        templates, so it's fine if a parameter does not apply
        to a particular template
        '''

        # if we haven't already provided the site name in the
        # context dict, get it from the django settings. If 
        # that isn't declared in our settings, an exception
        # will be raised (which will be caught by the caller)
        if 'site_name' not in self.context:
            self.context['site_name'] = settings.SITE_NAME

        if self.request:

            protocol = self.context.get('protocol') or (
                'https' if self.request.is_secure() else 'http'
            )

            # If no frontend domain is given, fail out. The links
            # created for various activities like activation, registration,
            # etc. are dependent on the frontend taking the link and
            # forming a post request
            frontend_domain = self.context.get('frontend_domain') or (
                getattr(settings, 'FRONTEND_DOMAIN'))

            self.context.update({
                'protocol': protocol,
                'frontend_domain': frontend_domain
            })


class TokenAndUidMixin(object):
    '''
    A mixin class that has behavior for creating
    tokens and encoded UIDs
    '''
    def _get_uid_and_token(self, user):
        '''
        Common behavior for situations where we send a link to the
        user with a token and an encoded UID.

        Returns the token and encoded uid for use in
        construction of activation links, etc.
        '''
        token = default_token_generator.make_token(user)
        encoded_uid = encode_uid(user.pk)
        return token, encoded_uid


class ActivationEmail(BaseEmailMessage, TokenAndUidMixin):
    plaintext_template_path = 'email/activation.txt'
    html_template_path = 'email/activation.html'
    subject = 'Account activation for WebMeV'

    def __init__(self, request, user):
        token, uid = self._get_uid_and_token(user)
        context = {}
        context['activation_url'] = settings.ACTIVATION_URL.format(
                                        uid=uid, token=token)
        super().__init__(context=context, request=request)


class PasswordResetEmail(BaseEmailMessage, TokenAndUidMixin):
    plaintext_template_path = 'email/password_reset.txt'
    html_template_path = 'email/password_reset.html'
    subject = 'Password reset request for WebMeV'

    def __init__(self, request, user):
        token, uid = self._get_uid_and_token(user)
        context = {}
        context['reset_url'] = settings.RESET_PASSWORD_URL.format(
                            uid=uid, token=token)
        super().__init__(context=context, request=request)


class AdminNotificationEmail(BaseEmailMessage):
    plaintext_template_path = 'email/admin_notification.txt'
    subject = '[WebMeV] Admin notification'


def send_activation_email(request, user):
    '''
    Orchestrates sending of the activation email after
    a user has registered.
    '''
    logger.info(f'Sending activation email to {user.email}')
    ActivationEmail(request, user).send([user.email])


def send_password_reset_email(request, user):
    '''
    Orchestrates sending of the email to reset a user password.
    '''
    logger.info(f'Sending password reset email to {user.email}')
    PasswordResetEmail(request, user).send([user.email])


def send_email_to_admins(message):
    '''
    Orchestrates sending an email to the admins.

    If error=True, then use the AdminNotificationEmail
    '''
    context = {
        'message': message
    }
    AdminNotificationEmail(context=context).send(
        settings.ADMIN_EMAIL_LIST)
