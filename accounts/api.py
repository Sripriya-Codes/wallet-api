from decimal import Decimal

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from ninja import Router
from ninja.errors import HttpError

from wallet.models import Wallet

from .auth import JWTAuth, create_token, create_token_pair, decode_token
from .schemas import AccessOut, LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut

router = Router(tags=["auth"])


@router.post("/register", response={201: UserOut})
def register(request, data: RegisterIn):
    User = get_user_model()
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username already taken")

    # TRANSACTION: user + wallet are created together or not at all
    with transaction.atomic():
        user = User.objects.create_user(
            username=data.username, email=data.email, password=data.password
        )
        Wallet.objects.create(user=user, balance=Decimal("1000.00"))
    return 201, user


@router.post("/login", response=TokenOut)
def login(request, data: LoginIn):
    user = authenticate(username=data.username, password=data.password)
    if user is None:
        raise HttpError(401, "Invalid username or password")
    return create_token_pair(user.pk)


@router.post("/refresh", response=AccessOut)
def refresh(request, data: RefreshIn):
    payload = decode_token(data.refresh, "refresh")
    if not payload:
        raise HttpError(401, "Invalid or expired refresh token")
    from django.conf import settings

    return {"access": create_token(payload["sub"], "access", settings.JWT_ACCESS_MINUTES)}


@router.get("/me", response=UserOut, auth=JWTAuth())
def me(request):
    return request.auth