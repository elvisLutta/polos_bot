from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request
from flask_login import UserMixin, AnonymousUserMixin
from . import db, login_manager

from keys import SITE_ADMIN


class Permission:
    '''Specify permissions in hex which allow or deny users certain actions.
    Each bit represents a certain permission.'''
    FOLLOW = 0x01
    COMMENT = 0X02
    WRITE_ARTICLES = 0X04
    MODERATE_COMMENTS = 0X08
    ADMINISTER = 0x80


class Role(db.Model):
    '''Store user roles in db with availability of extensions for other types
    roles in future. Each role allows a user to perform certain activities.'''
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            'Moderator': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES |
                     Permission.MODERATE_COMMENTS, True),
            'Administrator': (0xff, False) # Admin gets all permissions default
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin, db.Model):
    '''Basic user information. User is linked to many other models so it's
    important to make it available for extension. This is one of the primary
    models.'''
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))

    @staticmethod
    def generate_fake(count=100):
        '''This is a method for generating fake users for development purposes.'''
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     phonenumber=forgery_py.address.phone(),
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=True,
                     name=forgery_py.name.full_name(),
                     # location=forgery_py.address.city(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()
        if self.role_id is None:
            if self.email == (current_app.config['SITE_ADMIN'] or SITE_ADMIN):
                self.role_id = Role.query.filter_by(permisions=0xff).first().id
            if self.role_id is None:
                self.role_id = Role.query.filter_by(default=True).first().id

    @property
    def password(self):
        '''Raise an attribute error when someone tries to read the password.'''
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        '''Generate a password hash that will be stored instead of the original
        password.'''
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        '''Verify the user password using the check_password hash method.'''
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=86400):
        '''Generate a token that lasts for 24 hours before expiry to avoid hacks.'''
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        '''Use the generated token to confirm a user to ensure they are the same
        people that registered.'''
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=43200):
        '''This is the token sent when user request to reset their password that
        lasts for 12 hours before expiry to ensure security.'''
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        '''Return True or False based on the token used for confirmation .'''
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=86400):
        '''Generates a token for users when they request their email be changed
        this token lasts 24 hours before expiry.'''
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        '''Confirms token and returns True or False based on whether the token
        is correct. Set the new email if there no other similar email exists.'''
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True

    def can(self, permissions):
        '''Utility method to check whether a user has certain Permissions.'''
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        '''Utility method to check whether a user is an administrator.'''
        return self.can(Permission.ADMINISTER)

    def ping(self):
        '''Check whether user is online for use in views.'''
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar(self, size=100, default='identicon', rating='g'):
        '''Generate gravatar to ensure users have a representational image for
        their profile using this image.'''
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def __repr__(self):
        return '<User %r>' % self.email


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser


# Flask_login requires a callback to load a user using the given identifier
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

