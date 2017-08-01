
import json

ADMIN_GROUP_ID = 'ffffffff-ffff-ffff-ffff-ffffffffffff'

class PermissionController:

    def __init__(self, connection):
        self.connection = connection
        from porper.models.permission import Permission
        from porper.models.user_group import UserGroup
        self.permission = Permission(connection)
        self.user_group = UserGroup(connection)
        from porper.controllers.token_controller import TokenController
        self.token_controller = TokenController(connection)
        from porper.controllers.user_group_controller import UserGroupController
        self.user_group_controller = UserGroupController(connection)

    def is_admin(self, user_id):
        row = self.user_group.find({'user_id': user_id, 'group_id': ADMIN_GROUP_ID})
        if len(row) > 0:  return True
        else: return False

    def is_group_admin(self, user_id, group_id):
        rows = self.user_group.find({'user_id': user_id, 'group_id': group_id})
        if len(rows) > 0 and rows[0]['is_admin']:  return True
        else: return False

    def is_permitted_by_group(self, user_id, group_id, is_admin):
        if not group_id: return False
        if is_admin and self.is_group_admin(user_id, group_id):
            # the condition is 'is_admin: 1' and this user is the group admin, so this user is allowed
            print "is_permitted_by_group: is admin is 1 and this user is a group admin, so return true"
            return True
        elif is_admin == 0:
            # the condition is 'is_admin: 0' and this user is the member of this group, so this user is allowed
            print "is_permitted_by_group: is admin is 0 and this user is a member, so return true"
            return True
        print "is_permitted_by_group: return false"
        return False

    def are_permitted(self, access_token, params_list):
        #rows = self.token_controller.find(access_token)
        #user_id = rows[0]['user_id']
        for params in params_list:
            #if not self.is_permitted(user_id, params):  return False
            if not self.is_permitted(access_token, params):  return False
        return True

    #def is_permitted(self, user_id, params):
    def is_permitted(self, access_token, params):
        #params['user_id'] = user_id
        params['all'] = True
        #rows = self.permission.find(params)
        rows = self.find_all(access_token, params)
        print "permitted : %s" % rows
        if len(rows) == 0:  return False
        return True

    def has_allowed_permission(self, user_id, params):
        # if the target permission is 'read', check if this user has 'create' permission on that resource
        #if params['action'] != 'read':  return False
        params_for_allowed = dict(params)
        params_for_allowed['action'] = 'create'
        return self.permission.find(params_for_allowed) > 0

    def create(self, access_token, params, user_id=None):
        if not user_id:
            rows = self.token_controller.find(access_token)
            user_id = rows[0]['user_id']
        if not self.is_admin(user_id):
            if not self.has_allowed_permission(user_id, params):
              raise Exception("not permitted")
        self.permission.create(params)
        return True

    def update(self, access_token, params, user_id=None):
        raise Exception("not supported")

    def delete(self, access_token, params, user_id=None):
        if not user_id:
            rows = self.token_controller.find(access_token)
            user_id = rows[0]['user_id']
        if not self.is_admin(user_id):
            if not self.has_allowed_permission(user_id, params):
              raise Exception("not permitted")
        self.permission.delete(params)
        return True

    def filter_conditions(self, rows, user_id=None):
        # if there is no permissions with conditions, return True
        permissions = [ permission for permission in rows if permission.get('condition') ]
        if len(permissions) == 0:   return rows
        filtered = [ permission for permission in rows if not permission.get('condition') ]
        for permission in permissions:
            parent_params = json.loads(permission['condition'])
            # check when the condition is 'is_admin' and it is satisified, add it to the return list if so
            if not user_id:
                filtered.append(permission)
            elif 'is_admin' in parent_params and self.is_permitted_by_group(user_id, permission.get('group_id'), parent_params['is_admin']):
                filtered.append(permission)
            continue
            # now check if the parent permissions include the given 'parent' value
            parent_params['user_id'] = user_id
            #parent_params['group_id'] = permission['group_id']
            if not 'parent' in params:   continue
            parent_params['value'] = params['parent']
            parent_params['all'] = True     #### TODO: not sure if all have to be true......
            parent_rows = self.permission.find(parent_params)
            print "permitted parents : %s" % parent_rows
            if len(parent_rows) > 0:  filtered.append(permission)
        return filtered

    """
    1. find all of my permissions from access_token
    2. find all permissions of given user if I'm the admin
    3. find all permissions of given group if I'm the admin
    4. find member's all permissions if I'm the group admin of the given group
    5. find member's all permissions if I'm the group admin of any groups where the given user belongs
    6. find member's all permissions if I'm the given user
    """
    def find(self, access_token, params):

        rows = self.token_controller.find(access_token)
        user_id = rows[0]['user_id']

        # return my permissions
        if not params.get('user_id') and not params.get('group_id'):
            params['user_id'] = user_id
            rows = self.permission.find(params)
            return self.filter_conditions(rows, user_id)

        # return requested user/group's permissions if I'm an admin
        if self.is_admin(user_id):
            rows = self.permission.find(params)
            return self.filter_conditions(rows, params.get('user_id'))

        # return requested group's permissions if I'm a group admin
        if params.get('group_id'):
            if self.is_group_admin(user_id, params['group_id']):
                rows = self.permission.find(params)
                return self.filter_conditions(rows)
            else:   raise Exception("not permitted")

        if params.get('user_id'):
            # return my permissions when the given user is me
            if user_id == params['user_id']:
                rows = self.permission.find(params)
                return self.filter_conditions(rows, params['user_id'])

            # return requested user's permissions if I'm a group admin of any groups the given user belongs
            user_groups = self.user_group.find({'user_id': params['user_id']})
            if len(user_groups) == 0:    raise Exception("not permitted")
            for user_group in user_groups:
                if self.is_group_admin(user_id, user_group['group_id']):
                    rows = self.permission.find(params)
                    return self.filter_conditions(rows, params['user_id'])
            raise Exception("not permitted")

    def find_one(self, access_token, params):
        raise Exception("not supported")
