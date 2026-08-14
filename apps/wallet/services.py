from decimal import Decimal

from django.db import transaction

from .models import Transaction, Wallet


class InsufficientFunds(Exception):
    pass


def get_or_create_wallet(user) -> Wallet:
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


@transaction.atomic
def debit(user, amount: Decimal, title: str, subtitle: str = "", booking=None) -> Transaction:
    if amount < 0:
        raise ValueError("Debit amount cannot be negative.")
    wallet = Wallet.objects.select_for_update().get(user=user)
    if wallet.balance_usd < amount:
        raise InsufficientFunds(f"Balance ${wallet.balance_usd} is less than ${amount}.")
    wallet.balance_usd -= amount
    wallet.save(update_fields=["balance_usd"])
    return Transaction.objects.create(
        wallet=wallet,
        kind=Transaction.Kind.OUT,
        amount=amount,
        status=Transaction.Status.SUCCESS,
        title=title,
        subtitle=subtitle,
        booking=booking,
    )


@transaction.atomic
def credit(user, amount: Decimal, title: str, subtitle: str = "", topup_request=None) -> Transaction:
    if amount < 0:
        raise ValueError("Credit amount cannot be negative.")
    wallet = Wallet.objects.select_for_update().get(user=user)
    wallet.balance_usd += amount
    wallet.save(update_fields=["balance_usd"])
    return Transaction.objects.create(
        wallet=wallet,
        kind=Transaction.Kind.IN,
        amount=amount,
        status=Transaction.Status.SUCCESS,
        title=title,
        subtitle=subtitle,
        topup_request=topup_request,
    )
