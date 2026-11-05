import hashlib
import json

from django.db import IntegrityError, transaction
from django.http import JsonResponse
from ninja import Header, Router
from ninja.errors import HttpError

from accounts.auth import JWTAuth

from .models import IdempotencyKey, Transfer, Wallet
from .schemas import TransferIn, WalletOut
from .services import TransferError, do_transfer

router = Router(tags=["wallet"], auth=JWTAuth())


@router.get("/me", response=WalletOut)
def my_wallet(request):
    wallet = Wallet.objects.filter(user=request.auth).first()
    if not wallet:
        raise HttpError(404, "Wallet not found")
    return {"username": request.auth.username, "balance": wallet.balance}


@router.get("/transfers")
def my_transfers(request):
    qs = (
        Transfer.objects.filter(from_wallet__user=request.auth)
        .select_related("to_wallet__user")
        .order_by("-created_at")[:20]
    )
    return [
        {
            "id": str(t.id),
            "to": t.to_wallet.user.username,
            "amount": str(t.amount),
            "created_at": t.created_at.isoformat(),
        }
        for t in qs
    ]


@router.post("/transfer")
def transfer(
    request,
    data: TransferIn,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    user = request.auth

    # 1. Fingerprint of the request body
    payload = data.model_dump(mode="json")
    request_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()

    # 2. Try to claim the key. The unique (user, key) constraint decides the winner
    #    if two identical requests arrive at the same moment.
    try:
        with transaction.atomic():
            record = IdempotencyKey.objects.create(
                user=user, key=idempotency_key, request_hash=request_hash
            )
    except IntegrityError:
        record = IdempotencyKey.objects.get(user=user, key=idempotency_key)

        if record.request_hash != request_hash:
            return JsonResponse(
                {"detail": "Idempotency-Key was already used with a different request"},
                status=422,
            )
        if record.response_status is None:
            return JsonResponse(
                {"detail": "A request with this key is still being processed"},
                status=409,
            )
        # Same key + same body + already finished = replay the saved response
        response = JsonResponse(record.response_body, status=record.response_status)
        response["Idempotent-Replayed"] = "true"
        return response

    # 3. First time we see this key: do the real work
    try:
        result = do_transfer(
            user, data.to_username, data.amount, data.simulate_failure
        )
        status = 201
    except TransferError as e:
        result = {"detail": str(e)}
        status = 400
    except Exception:
        # Unexpected crash: free the key so the client can safely retry
        record.delete()
        raise

    # 4. Save the response so retries get the exact same answer
    record.response_status = status
    record.response_body = result
    record.save(update_fields=["response_status", "response_body"])

    return JsonResponse(result, status=status)