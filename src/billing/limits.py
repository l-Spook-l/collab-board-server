FREE_MAX_OWNED_BOARDS = 3
FREE_MAX_INVITED_MEMBERS = 3
PRO_MAX_INVITED_MEMBERS = 15

PRO_STATUSES = frozenset({"active", "trialing", "past_due"})


def has_pro_access(status: str | None) -> bool:
    """Keep Pro access while Stripe retries a failed subscription payment."""
    return status in PRO_STATUSES


def max_owned_boards(status: str | None) -> int | None:
    return None if has_pro_access(status) else FREE_MAX_OWNED_BOARDS


def max_invited_members(status: str | None) -> int:
    return PRO_MAX_INVITED_MEMBERS if has_pro_access(status) else FREE_MAX_INVITED_MEMBERS
