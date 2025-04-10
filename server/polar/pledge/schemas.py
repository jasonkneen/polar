from __future__ import annotations

from datetime import datetime
from typing import Annotated, Self

from pydantic import Field

from polar.funding.funding_schema import Funding
from polar.issue.schemas import Issue
from polar.kit.schemas import IDSchema, Schema, TimestampedSchema
from polar.models import Organization, User
from polar.models.pledge import Pledge as PledgeModel
from polar.models.pledge import PledgeState, PledgeType


# Public API
class Pledger(Schema):
    name: str
    github_username: str | None
    avatar_url: str | None

    @classmethod
    def from_pledge(cls, p: PledgeModel) -> Self | None:
        if p.on_behalf_of_organization:
            return cls(
                name=p.on_behalf_of_organization.name
                or p.on_behalf_of_organization.slug,
                github_username=p.on_behalf_of_organization.slug,
                avatar_url=p.on_behalf_of_organization.avatar_url,
            )

        if p.user:
            return cls(
                name=p.user.public_name,
                github_username=p.user.github_username,
                avatar_url=p.user.avatar_url,
            )

        if p.by_organization:
            return cls(
                name=p.by_organization.name or p.by_organization.slug,
                github_username=p.by_organization.slug,
                avatar_url=p.by_organization.avatar_url,
            )

        return None

    @classmethod
    def from_user(cls, user: User) -> Self:
        return cls(
            name=user.public_name,
            github_username=user.github_username,
            avatar_url=user.avatar_url,
        )

    @classmethod
    def from_organization(cls, organization: Organization) -> Self:
        return cls(
            name=organization.slug,
            github_username=organization.slug,
            avatar_url=organization.avatar_url,
        )


# Public API
class Pledge(IDSchema, TimestampedSchema):
    amount: int = Field(description="Amount pledged towards the issue")
    currency: str
    state: PledgeState = Field(description="Current state of the pledge")
    type: PledgeType = Field(description="Type of pledge")

    refunded_at: datetime | None = Field(
        None, description="If and when the pledge was refunded to the pledger"
    )  # noqa: E501

    scheduled_payout_at: datetime | None = Field(
        None,
        description="When the payout is scheduled to be made to the maintainers behind the issue. Disputes must be made before this date.",  # noqa: E501
    )

    issue: Issue = Field(description="The issue that the pledge was made towards")

    pledger: Pledger | None = Field(
        None, description="The user or organization that made this pledge"
    )

    hosted_invoice_url: str | None = Field(
        None, description="URL of invoice for this pledge"
    )

    authed_can_admin_sender: bool = Field(
        default=False,
        description="If the currently authenticated subject can perform admin actions on behalf of the maker of the peldge",  # noqa: E501
    )

    authed_can_admin_received: bool = Field(
        default=False,
        description="If the currently authenticated subject can perform admin actions on behalf of the receiver of the peldge",  # noqa: E501
    )

    created_by: Pledger | None = Field(
        None,
        description="For pledges made by an organization, or on behalf of an organization. This is the user that made the pledge. Only visible for members of said organization.",  # noqa: E501
    )

    @classmethod
    def from_db(
        cls,
        o: PledgeModel,
        *,
        include_receiver_admin_fields: bool = False,
        include_sender_admin_fields: bool = False,
        include_sender_fields: bool = False,
    ) -> Pledge:
        return Pledge(
            id=o.id,
            created_at=o.created_at,
            modified_at=o.modified_at,
            amount=o.amount,
            currency=o.currency,
            state=PledgeState.from_str(o.state),
            type=PledgeType.from_str(o.type),
            #
            refunded_at=o.refunded_at
            if include_sender_admin_fields or include_receiver_admin_fields
            else None,
            #
            scheduled_payout_at=o.scheduled_payout_at
            if include_receiver_admin_fields
            else None,
            #
            issue=Issue.model_validate(o.issue),
            pledger=Pledger.from_pledge(o),
            #
            hosted_invoice_url=o.invoice_hosted_url
            if include_sender_admin_fields
            else None,
            #
            created_by=Pledger.from_user(o.created_by_user)
            if o.created_by_user and include_sender_fields
            else None,
        )


class SummaryPledge(Schema):
    type: PledgeType = Field(description="Type of pledge")
    pledger: Pledger | None

    @classmethod
    def from_db(cls, o: PledgeModel) -> SummaryPledge:
        return SummaryPledge(
            type=PledgeType.from_str(o.type),
            pledger=Pledger.from_pledge(o),
        )


class PledgePledgesSummary(Schema):
    funding: Funding
    pledges: list[SummaryPledge]


class PledgeSpending(Schema):
    amount: int
    currency: str


# Internal APIs below

# Ref: https://stripe.com/docs/api/payment_intents/object#payment_intent_object-amount
MAXIMUM_AMOUNT = 99999999

PledgeCurrency = Annotated[
    str,
    Field(
        default="usd",
        pattern="usd",
        description="The currency. Currently, only `usd` is supported.",
    ),
]
