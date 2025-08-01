import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy.exc import IntegrityError

from polar.account.service import account as account_service
from polar.auth.models import AuthSubject
from polar.exceptions import PolarError, PolarRequestValidationError
from polar.integrations.loops.service import loops as loops_service
from polar.kit.anonymization import anonymize_email_for_deletion, anonymize_for_deletion
from polar.kit.pagination import PaginationParams
from polar.kit.sorting import Sorting
from polar.models import Account, Organization, User, UserOrganization
from polar.models.transaction import TransactionType
from polar.models.webhook_endpoint import WebhookEventType
from polar.postgres import AsyncSession, sql
from polar.posthog import posthog
from polar.transaction.service.transaction import transaction as transaction_service
from polar.webhook.service import webhook as webhook_service
from polar.worker import enqueue_job

from .repository import OrganizationRepository
from .schemas import OrganizationCreate, OrganizationUpdate
from .sorting import OrganizationSortProperty

log = structlog.get_logger()


class OrganizationError(PolarError): ...


class InvalidAccount(OrganizationError):
    def __init__(self, account_id: UUID) -> None:
        self.account_id = account_id
        message = (
            f"The account {account_id} does not exist or you don't have access to it."
        )
        super().__init__(message)


class OrganizationService:
    async def list(
        self,
        session: AsyncSession,
        auth_subject: AuthSubject[User | Organization],
        *,
        slug: str | None = None,
        pagination: PaginationParams,
        sorting: list[Sorting[OrganizationSortProperty]] = [
            (OrganizationSortProperty.created_at, False)
        ],
    ) -> tuple[Sequence[Organization], int]:
        repository = OrganizationRepository.from_session(session)
        statement = repository.get_readable_statement(auth_subject)

        if slug is not None:
            statement = statement.where(Organization.slug == slug)

        statement = repository.apply_sorting(statement, sorting)

        return await repository.paginate(
            statement, limit=pagination.limit, page=pagination.page
        )

    async def get(
        self,
        session: AsyncSession,
        auth_subject: AuthSubject[User | Organization],
        id: uuid.UUID,
    ) -> Organization | None:
        repository = OrganizationRepository.from_session(session)
        statement = repository.get_readable_statement(auth_subject).where(
            Organization.id == id
        )
        return await repository.get_one_or_none(statement)

    async def create(
        self,
        session: AsyncSession,
        create_schema: OrganizationCreate,
        auth_subject: AuthSubject[User],
    ) -> Organization:
        repository = OrganizationRepository.from_session(session)
        existing_slug = await repository.get_by_slug(create_schema.slug)
        if existing_slug is not None:
            raise PolarRequestValidationError(
                [
                    {
                        "loc": ("body", "slug"),
                        "msg": "An organization with this slug already exists.",
                        "type": "value_error",
                        "input": create_schema.slug,
                    }
                ]
            )

        organization = await repository.create(
            Organization(
                **create_schema.model_dump(exclude_unset=True, exclude_none=True),
                customer_invoice_prefix=create_schema.slug.upper(),
            )
        )
        await self.add_user(session, organization, auth_subject.subject)

        enqueue_job("organization.created", organization_id=organization.id)

        posthog.auth_subject_event(
            auth_subject,
            "organizations",
            "create",
            "done",
            {
                "id": organization.id,
                "name": organization.name,
                "slug": organization.slug,
            },
        )
        return organization

    async def update(
        self,
        session: AsyncSession,
        organization: Organization,
        update_schema: OrganizationUpdate,
    ) -> Organization:
        repository = OrganizationRepository.from_session(session)

        if organization.onboarded_at is None:
            organization.onboarded_at = datetime.now(UTC)

        if update_schema.feature_settings is not None:
            organization.feature_settings = {
                **organization.feature_settings,
                **update_schema.feature_settings.model_dump(
                    mode="json", exclude_unset=True, exclude_none=True
                ),
            }

        if update_schema.subscription_settings is not None:
            organization.subscription_settings = update_schema.subscription_settings

        if update_schema.notification_settings is not None:
            organization.notification_settings = update_schema.notification_settings

        previous_details = organization.details
        update_dict = update_schema.model_dump(
            by_alias=True,
            exclude_unset=True,
            exclude={
                "profile_settings",
                "feature_settings",
                "subscription_settings",
                "details",
            },
        )

        # Only store details once to avoid API overrides later w/o review
        if not previous_details and update_schema.details:
            organization.details = update_schema.details.model_dump()
            organization.details_submitted_at = datetime.now(UTC)

        organization = await repository.update(organization, update_dict=update_dict)

        await self._after_update(session, organization)
        return organization

    async def delete(
        self,
        session: AsyncSession,
        organization: Organization,
    ) -> Organization:
        """Anonymizes fields on the Organization that can contain PII and then
        soft-deletes the Organization.

        DOES NOT:
        - Delete or anonymize Users related Organization
        - Delete or anonymize Account of the Organization
        - Delete or anonymize Customers, Products, Discounts, Benefits, Checkouts of the Organization
        - Revoke Benefits granted
        - Remove API tokens (organization or personal)
        """
        repository = OrganizationRepository.from_session(session)

        update_dict: dict[str, Any] = {}

        pii_fields = ["name", "slug", "website", "customer_invoice_prefix"]
        github_fields = ["bio", "company", "blog", "location", "twitter_username"]
        for pii_field in pii_fields + github_fields:
            value = getattr(organization, pii_field)
            if value:
                update_dict[pii_field] = anonymize_for_deletion(value)

        if organization.email:
            update_dict["email"] = anonymize_email_for_deletion(organization.email)

        if organization.avatar_url:
            # Anonymize by setting to Polar logo
            update_dict["avatar_url"] = (
                "https://avatars.githubusercontent.com/u/105373340?s=48&v=4"
            )
        if organization.details:
            update_dict["details"] = {}

        if organization.socials:
            update_dict["socials"] = []

        organization = await repository.update(organization, update_dict=update_dict)
        await repository.soft_delete(organization)

        return organization

    async def add_user(
        self,
        session: AsyncSession,
        organization: Organization,
        user: User,
    ) -> None:
        nested = await session.begin_nested()
        try:
            relation = UserOrganization(
                user_id=user.id, organization_id=organization.id
            )
            session.add(relation)
            await session.flush()
            log.info(
                "organization.add_user.created",
                user_id=user.id,
                organization_id=organization.id,
            )
        except IntegrityError:
            # TODO: Currently, we treat this as success since the connection
            # exists. However, once we use status to distinguish active/inactive
            # installations we need to change this.
            log.info(
                "organization.add_user.already_exists",
                organization_id=organization.id,
                user_id=user.id,
            )
            await nested.rollback()
            # Update
            stmt = (
                sql.Update(UserOrganization)
                .where(
                    UserOrganization.user_id == user.id,
                    UserOrganization.organization_id == organization.id,
                )
                .values(
                    deleted_at=None,  # un-delete user if exists
                )
            )
            await session.execute(stmt)
            await session.flush()
        finally:
            await loops_service.user_organization_added(session, user)

    async def set_account(
        self,
        session: AsyncSession,
        auth_subject: AuthSubject[User | Organization],
        organization: Organization,
        account_id: UUID,
    ) -> Organization:
        account = await account_service.get(session, auth_subject, account_id)
        if account is None:
            raise InvalidAccount(account_id)

        first_account_set = organization.account_id is None

        repository = OrganizationRepository.from_session(session)
        organization = await repository.update(
            organization, update_dict={"account": account}
        )

        if first_account_set:
            enqueue_job("organization.account_set", organization.id)

        await self._after_update(session, organization)

        return organization

    async def get_next_invoice_number(
        self,
        session: AsyncSession,
        organization: Organization,
    ) -> str:
        invoice_number = f"{organization.customer_invoice_prefix}-{organization.customer_invoice_next_number:04d}"
        repository = OrganizationRepository.from_session(session)
        organization = await repository.update(
            organization,
            update_dict={
                "customer_invoice_next_number": organization.customer_invoice_next_number
                + 1
            },
        )
        return invoice_number

    async def _after_update(
        self,
        session: AsyncSession,
        organization: Organization,
    ) -> None:
        await webhook_service.send(
            session, organization, WebhookEventType.organization_updated, organization
        )

    async def check_review_threshold(
        self, session: AsyncSession, organization: Organization
    ) -> Organization:
        if organization.is_under_review():
            return organization

        transfers_sum = await transaction_service.get_transactions_sum(
            session, organization.account_id, type=TransactionType.balance
        )
        if (
            organization.next_review_threshold >= 0
            and transfers_sum >= organization.next_review_threshold
        ):
            organization.status = Organization.Status.UNDER_REVIEW
            await self._sync_account_status(session, organization)
            session.add(organization)

            enqueue_job("organization.under_review", organization_id=organization.id)

        return organization

    async def confirm_organization_reviewed(
        self,
        session: AsyncSession,
        organization: Organization,
        next_review_threshold: int,
    ) -> Organization:
        organization.status = Organization.Status.ACTIVE
        organization.next_review_threshold = next_review_threshold
        await self._sync_account_status(session, organization)
        session.add(organization)
        enqueue_job("organization.reviewed", organization_id=organization.id)
        return organization

    async def deny_organization(
        self, session: AsyncSession, organization: Organization
    ) -> Organization:
        organization.status = Organization.Status.DENIED
        await self._sync_account_status(session, organization)
        session.add(organization)
        return organization

    async def set_organization_under_review(
        self, session: AsyncSession, organization: Organization
    ) -> Organization:
        organization.status = Organization.Status.UNDER_REVIEW
        await self._sync_account_status(session, organization)
        session.add(organization)
        enqueue_job("organization.under_review", organization_id=organization.id)
        return organization

    async def update_status_from_stripe_account(
        self, session: AsyncSession, account: Account
    ) -> None:
        """Update organization status based on Stripe account capabilities."""
        repository = OrganizationRepository.from_session(session)
        organizations = await repository.get_all_by_account(account.id)

        for organization in organizations:
            # Don't override organizations that are under review or denied
            if organization.status in (
                Organization.Status.UNDER_REVIEW,
                Organization.Status.DENIED,
            ):
                continue

            # If account is fully set up, set organization to ACTIVE
            if all(
                (
                    account.currency is not None,
                    account.is_details_submitted,
                    account.is_charges_enabled,
                    account.is_payouts_enabled,
                )
            ):
                organization.status = Organization.Status.ACTIVE
            else:
                # If Stripe capabilities are missing, set to ONBOARDING_STARTED
                organization.status = Organization.Status.ONBOARDING_STARTED

            await self._sync_account_status(session, organization)
            session.add(organization)

    async def _sync_account_status(
        self, session: AsyncSession, organization: Organization
    ) -> None:
        """Sync organization status to the related account."""
        if not organization.account_id:
            return

        # Map organization status to account status
        status_mapping = {
            Organization.Status.ONBOARDING_STARTED: Account.Status.ONBOARDING_STARTED,
            Organization.Status.ACTIVE: Account.Status.ACTIVE,
            Organization.Status.UNDER_REVIEW: Account.Status.UNDER_REVIEW,
            Organization.Status.DENIED: Account.Status.DENIED,
        }

        if organization.status in status_mapping:
            account_status = status_mapping[organization.status]
            await session.execute(
                sqlalchemy_update(Account)
                .where(Account.id == organization.account_id)
                .values(status=account_status)
            )


organization = OrganizationService()
