'''
This file contains various constants used to populate test databases.  

Placing these here ensure we can have consistent references between test
database generation, querying, and testing.
'''
import os

class TestUser(object):
    '''
    Simple container class for details about a user
    '''
    def __init__(self, email, plain_txt_password):
        self.email = email
        self.plain_txt_password = plain_txt_password

# create a couple of "regular" users
REGULAR_USER_1_PASSWORD = 'abc123xyz!'
REGULAR_USER_1 = TestUser('reguser1@foo.com',REGULAR_USER_1_PASSWORD)
REGULAR_USER_2 = TestUser('reguser2@foo.com','!foobarbaz!')
ADMIN_USER = TestUser('admin@foo.com','@dmin_pAss')

JUNK_EMAIL = 'does_not_exist@foo.com'
SOCIAL_AUTH_EMAIL = 'email_from_social@foo.com'