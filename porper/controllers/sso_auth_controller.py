
import os
import json
import requests
import boto3

from porper.controllers.auth_controller import AuthController

class SsoAuthController(AuthController):

    def __init__(self, permission_connection=None, loglevel="INFO"):

        AuthController.__init__(self, permission_connection, loglevel)

        client = boto3.client('ssm')
        self.host = os.environ.get('SSO_HOST')
        if self.host is None:
            self.host = client.get_parameter(Name='SSO_HOST', WithDecryption=True)['Parameter']['Value']
        self.username = os.environ.get('SSO_CLIENT_ID')
        if self.username is None:
            self.username = client.get_parameter(Name='SSO_CLIENT_ID', WithDecryption=True)['Parameter']['Value']
        self.password = os.environ.get('SSO_CLIENT_SECRET')
        if self.password is None:
            self.password = client.get_parameter(Name='SSO_CLIENT_SECRET', WithDecryption=True)['Parameter']['Value']
        self.redirect_uri = os.environ.get('SSO_REDIRECT_URI')
        if self.redirect_uri is None:
            self.redirect_uri = client.get_parameter(Name='SSO_REDIRECT_URI', WithDecryption=True)['Parameter']['Value']


    def authenticate(self, params):

        code = params['code']

        # get the tokens to see if the given code is valid
        self.logger.debug("code [{}]".format(code))
        task_url = "service/oauth2/access_token?realm=SungardAS"
        url = "https://%s/%s"%(self.host, task_url)
        client_auth = requests.auth.HTTPBasicAuth(self.username, self.password)
        post_data = {"grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri}
        r = requests.post(url, auth=client_auth, data=post_data, verify=False)
        self.logger.debug(r._content)
        # {u'access_token': u'ed8f3af2-c28a-439f-aa0c-69e0fd620502', u'id_token': u'eyAidHl...', u'expires_in': 59, u'token_type': u'Bearer', u'scope': u'phone address email cloud openid profile', u'refresh_token': u'8e044a96-2be8-45a5-b9c6-08f118f26f42'}
        tokens = json.loads(r._content)
        if not tokens.get('access_token'):
            raise Exception("unauthorized")

        # now retrieve user info from the returned access_token
        user_info = self.get_user_information(tokens['access_token'])
        self.logger.debug(user_info)

        # now save the user info & tokens
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']
        display_name = user_info.get('displayName')
        if not display_name:
            display_name = '%s %s' % (user_info['given_name'], user_info['family_name'])
        auth_params = {
            'user_id': user_info['guid'],
            'email': user_info['email'],
            'family_name': user_info['family_name'],
            'given_name': user_info['given_name'],
            'name': display_name,
            'auth_type': 'sso',
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        user_info = AuthController.authenticate(self, auth_params)

        # return the access_token if all completed successfully
        # user_info['user_id'] = user_info['guid']
        # user_info['access_token'] = access_token
        # user_info['groups'] = AuthController.find_groups(self, auth_params['user_id'])
        return user_info

    def get_user_information(self, access_token):
        task_url = "service/oauth2/userinfo?realm=SungardAS"
        url = "https://%s/%s"%(self.host, task_url)
        headers = {"Authorization":"Bearer " + access_token}
        r = requests.get(url, headers=headers, verify=False)
        #self.logger.debug(r._content)
        # {u'family_name': u'', u'userGuid': u'', u'displayName': u'', u'sub': u'', u'roles': [], u'cloudstack_secret_key': u'', u'zoneinfo': u'', u'company_guid': u'', u'updated_at': u'0', u'applications': [], u'given_name': u'', u'groups': [], u'cloudstack_api_key': u'', u'guid': u'', u'email': u'', u'employeeNumber': u''}
        return json.loads(r._content)

    def validate_token(self, refresh_token):
        task_url = "service/oauth2/access_token?realm=SungardAS"
        url = "https://%s/%s"%(self.host, task_url)
        client_auth = requests.auth.HTTPBasicAuth(self.username, self.password)
        post_data = {'grant_type':'refresh_token', 'refresh_token':refresh_token}
        r = requests.post(url, auth=client_auth, data=post_data, verify=False)
        return json.loads(r._content)
