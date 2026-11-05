from ninja import Schema


class RegisterIn(Schema):
    username: str
    email: str
    password: str


class LoginIn(Schema):
    username: str
    password: str


class RefreshIn(Schema):
    refresh: str


class TokenOut(Schema):
    access: str
    refresh: str


class AccessOut(Schema):
    access: str


class UserOut(Schema):
    id: int
    username: str
    email: str