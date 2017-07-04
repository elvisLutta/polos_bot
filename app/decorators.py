from functools import wraps
from flask import abort
from flask_login import current_user
from models.Permission import ADMINISTER


def permission_required(permission):
    '''Wrapper required for making sure the person accessing a
    certain part of the site has the right permissions to make
    necessary changes.'''

    def decorator(f):
        @wraps(f):
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    return permission_required(ADMINISTER)(f)
