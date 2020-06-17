import logging 

from django.contrib.auth.tokens import default_token_generator

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core import mail
from django.template.context import make_context
from django.template.loader import get_template

from .basic_utils import encode_uid, decode_uid

logger = logging.getLogger(__name__)

class BaseEmailMessage(mail.EmailMultiAlternatives):
    _node_map = {
        'subject': 'subject',
        'text_body': 'body',
        'html_body': 'html',
    }
    template_name = None

    def __init__(self, request=None, context=None, template_name=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request
        self.context = {} if context is None else context
        self.html = None

        if template_name is not None:
            self.template_name = template_name

    def get_context_data(self, **kwargs):
        context = dict(**self.context)
        if self.request:
            site = get_current_site(self.request)
            domain = context.get('domain') or (
                getattr(settings, 'DOMAIN', '') or site.domain
            )
            protocol = context.get('protocol') or (
                'https' if self.request.is_secure() else 'http'
            )
            site_name = context.get('site_name') or (
                getattr(settings, 'SITE_NAME', '') or site.name
            )

            # If no frontend domain is given, default to the site name
            frontend_domain = context.get('frontend_domain') or (
                getattr(settings, 'FRONTEND_DOMAIN', '') or site.name
            )

            user = context.get('user') or self.request.user

        context.update({
            'domain': domain,
            'protocol': protocol,
            'site_name': site_name,
            'frontend_domain': frontend_domain
        })
        return context

    def render(self):
        context = make_context(self.get_context_data(), request=self.request)
        template = get_template(self.template_name)
        with context.bind_template(template.template):
            for node in template.template.nodelist:
                self._process_node(node, context)
        self._attach_body()

    def send(self, to, *args, **kwargs):
        self.render()

        self.to = to
        self.cc = kwargs.pop('cc', [])
        self.bcc = kwargs.pop('bcc', [])
        self.reply_to = kwargs.pop('reply_to', [])
        self.from_email = kwargs.pop('from_email', None)
        if self.from_email is None:
            self.from_email = settings.DEFAULT_FROM_EMAIL

        super().send(*args, **kwargs)

    def _process_node(self, node, context):
        attr = self._node_map.get(getattr(node, 'name', ''))
        if attr is not None:
            setattr(self, attr, node.render(context).strip())

    def _attach_body(self):
        if self.body and self.html:
            self.attach_alternative(self.html, 'text/html')
        elif self.html:
            self.body = self.html
            self.content_subtype = 'html'

class ActivationEmail(BaseEmailMessage):
    template_name = "email/activation.html"

    def get_context_data(self):
        context = super().get_context_data()
        context["url"] = settings.ACTIVATION_URL.format(**context)
        return context

class PasswordResetEmail(BaseEmailMessage):
    template_name = "email/password_reset.html"

    def get_context_data(self):
        context = super().get_context_data()
        context["url"] = settings.RESET_PASSWORD_URL.format(**context)
        return context

def send_uid_and_token_link(request, user, message_cls):
    '''
    Common behavior for situations where we send a link to the
    user with a token and an encoded UID.

    message_cls is a subclass of BaseEmailMessage 
    (not instantiated- just the type)
    '''
    token = default_token_generator.make_token(user)
    encoded_uid = encode_uid(user.pk)

    context = {
        "user": user,
        'uid': encoded_uid,
        'token': token
    }
    to = [user.email]
    message(request, context).send(
        to, 
        from_email=settings.FROM_EMAIL)


def send_activation_email(request, user):
    '''
    Orchestrates sending of the activation email after
    a user has registered.
    '''
    logger.info('Sending activation email to {email}'.format(email=user.email))
    message_cls = ActivationEmail
    send_uid_and_token_link(request, user, message_cls)

def send_password_reset_email(request, user):
    '''
    Orchestrates sending of the email to reset a user password.
    '''
    logger.info('Sending password reset email to {email}'.format(email=user.email))
    message_cls = PasswordResetEmail
    send_uid_and_token_link(request, user, message_cls)
