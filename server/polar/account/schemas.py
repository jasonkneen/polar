from typing import Any, Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from polar.enums import AccountType
from polar.kit.schemas import Schema
from polar.models.account import Account as AccountModel
from polar.organization.schemas import Organization
from polar.user.schemas import UserBase


# Public API
class AccountCreate(Schema):
    account_type: Literal[AccountType.stripe]
    country: str = Field(
        description="Two letter uppercase country code", min_length=2, max_length=2
    )

    @model_validator(mode="after")
    def validate_country(self) -> Self:
        if self.country.upper() != self.country:
            raise ValueError("country must be uppercase")
        return self


# Public API
class Account(Schema):
    id: UUID
    account_type: AccountType
    status: AccountModel.Status
    stripe_id: str | None
    open_collective_slug: str | None
    is_details_submitted: bool
    is_charges_enabled: bool
    is_payouts_enabled: bool
    country: str = Field(min_length=2, max_length=2)

    users: list[UserBase]
    organizations: list[Organization]

    @classmethod
    def from_db(cls, o: AccountModel) -> Self:
        return cls(
            id=o.id,
            account_type=o.account_type,
            status=o.status,
            stripe_id=o.stripe_id,
            open_collective_slug=o.open_collective_slug,
            is_details_submitted=o.is_details_submitted,
            is_charges_enabled=o.is_charges_enabled,
            is_payouts_enabled=o.is_payouts_enabled,
            country=o.country,
            users=[UserBase.model_validate(user) for user in o.users],
            organizations=[
                Organization.model_validate(organization)
                for organization in o.organizations
            ],
        )


class AccountUpdate(Schema):
    email: str | None = None
    country: str
    currency: str
    is_details_submitted: bool
    is_charges_enabled: bool
    is_payouts_enabled: bool
    data: dict[str, Any]


class AccountLink(Schema):
    url: str


class AccountLoginLink(Schema):
    created: int
    url: str


class OrganizationAccountPath(Schema):
    name: str = Field(..., description="Unique name identifier of the organization")


class OrganizationAccountLinkPath(OrganizationAccountPath):
    stripe_id: str = Field(..., description="Stripe ID of the account")
