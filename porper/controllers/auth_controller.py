
#import json

class AuthController():

    def __init__(self, permission_connection):
        self.connection = permission_connection
        from porper.controllers.user_controller import UserController
        self.user_controller = UserController(self.connection)
        from porper.controllers.token_controller import TokenController
        self.token_controller = TokenController(self.connection)

    def authenticate(self, user_id, email, family_name, given_name, name, access_token, refresh_token):
        params = {
            'id': user_id,
            'email': email,
            'family_name': family_name,
            'given_name': given_name,
            'name': name
        }
        user_id = self.user_controller.create(None, params)

        # now save the tokens
        self.token_controller.save(access_token, refresh_token, user_id)

    def find_groups(self, email):
        from porper.models.user_group import UserGroup
        user_group = UserGroup(self.connection)
        user_groups = user_group.find({'email': email})
        return user_groups
