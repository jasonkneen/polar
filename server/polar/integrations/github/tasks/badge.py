from uuid import UUID

import httpx
import structlog
from arq import Retry

from polar.worker import (
    AsyncSessionMaker,
    JobContext,
    PolarWorkerContext,
    compute_backoff,
    enqueue_job,
    get_worker_redis,
    task,
)

from ..service.issue import github_issue
from .utils import get_external_organization_and_repo, github_rate_limit_retry

log = structlog.get_logger()

BADGE_UPDATE_MAX_RETRIES = 10


@task("github.badge.embed_on_issue", max_tries=BADGE_UPDATE_MAX_RETRIES)
@github_rate_limit_retry
async def embed_badge(
    ctx: JobContext,
    issue_id: UUID,
    polar_context: PolarWorkerContext,
) -> None:
    with polar_context.to_execution_context():
        async with AsyncSessionMaker(ctx) as session:
            issue = await github_issue.get(session, issue_id)
            if not issue or not issue.organization_id or not issue.repository_id:
                log.warning(
                    "github.badge.embed_on_issue",
                    error="issue not found",
                    issue_id=issue_id,
                )
                return

            (
                external_organization,
                repository,
            ) = await get_external_organization_and_repo(
                session, issue.organization_id, issue.repository_id
            )

            try:
                await github_issue.embed_badge(
                    session,
                    get_worker_redis(ctx),
                    external_organization=external_organization,
                    repository=repository,
                    issue=issue,
                    organization=external_organization.safe_organization,
                    triggered_from_label=False,
                )
            except httpx.HTTPError as e:
                raise Retry(compute_backoff(ctx["job_try"])) from e


@task("github.badge.update_on_issue")
@github_rate_limit_retry
async def update_on_issue(
    ctx: JobContext,
    issue_id: UUID,
    polar_context: PolarWorkerContext,
) -> None:
    with polar_context.to_execution_context():
        async with AsyncSessionMaker(ctx) as session:
            issue = await github_issue.get(session, issue_id)
            if not issue or not issue.organization_id or not issue.repository_id:
                log.warning(
                    "github.badge.update_on_issue",
                    error="issue not found",
                    issue_id=issue_id,
                )
                return

            (
                external_organization,
                repository,
            ) = await get_external_organization_and_repo(
                session, issue.organization_id, issue.repository_id
            )

            try:
                await github_issue.update_embed_badge(
                    session,
                    get_worker_redis(ctx),
                    external_organization=external_organization,
                    repository=repository,
                    issue=issue,
                    organization=external_organization.safe_organization,
                )
            except httpx.HTTPError as e:
                if ctx["job_try"] <= BADGE_UPDATE_MAX_RETRIES:
                    raise Retry(compute_backoff(ctx["job_try"])) from e
                else:
                    raise


@task("github.badge.remove_on_issue", max_tries=BADGE_UPDATE_MAX_RETRIES)
@github_rate_limit_retry
async def remove_badge(
    ctx: JobContext,
    issue_id: UUID,
    polar_context: PolarWorkerContext,
) -> None:
    with polar_context.to_execution_context():
        async with AsyncSessionMaker(ctx) as session:
            issue = await github_issue.get(session, issue_id, allow_deleted=True)
            if not issue or not issue.organization_id or not issue.repository_id:
                log.warning(
                    "github.badge.embed_on_issue",
                    error="issue not found",
                    issue_id=issue_id,
                )
                return

            (
                external_organization,
                repository,
            ) = await get_external_organization_and_repo(
                session, issue.organization_id, issue.repository_id, allow_deleted=True
            )

            try:
                await github_issue.remove_badge(
                    session,
                    get_worker_redis(ctx),
                    external_organization=external_organization,
                    repository=repository,
                    issue=issue,
                    organization=external_organization.safe_organization,
                    triggered_from_label=False,
                )
            except httpx.HTTPError as e:
                raise Retry(compute_backoff(ctx["job_try"])) from e


@task("github.badge.embed_retroactively_on_repository")
@github_rate_limit_retry
async def embed_badge_retroactively_on_repository(
    ctx: JobContext,
    organization_id: UUID,
    repository_id: UUID,
    polar_context: PolarWorkerContext,
) -> None:
    with polar_context.to_execution_context():
        async with AsyncSessionMaker(ctx) as session:
            organization, repository = await get_external_organization_and_repo(
                session, organization_id, repository_id
            )

            if repository.is_private:
                log.warn(
                    "github.embed_badge_retroactively_on_repository.skip_repo_is_private"
                )
                return

            for i in await github_issue.list_issues_to_add_badge_to_auto(
                session=session,
                repository=repository,
                external_organization=organization,
            ):
                enqueue_job("github.badge.embed_on_issue", i.id)


@task("github.badge.remove_on_repository")
@github_rate_limit_retry
async def remove_badges_on_repository(
    ctx: JobContext,
    organization_id: UUID,
    repository_id: UUID,
    polar_context: PolarWorkerContext,
) -> None:
    with polar_context.to_execution_context():
        async with AsyncSessionMaker(ctx) as session:
            organization, repository = await get_external_organization_and_repo(
                session, organization_id, repository_id
            )

            if repository.is_private:
                log.warn("github.remove_badges_on_repository.skip_repo_is_private")
                return

            for i in await github_issue.list_issues_to_remove_badge_from_auto(
                session=session,
                repository=repository,
                external_organization=organization,
            ):
                enqueue_job("github.badge.remove_on_issue", i.id)


@task("github.badge.remove_label", max_tries=BADGE_UPDATE_MAX_RETRIES)
@github_rate_limit_retry
async def remove_label(
    ctx: JobContext,
    issue_id: UUID,
    polar_context: PolarWorkerContext,
) -> None:
    with polar_context.to_execution_context():
        async with AsyncSessionMaker(ctx) as session:
            issue = await github_issue.get(session, issue_id, allow_deleted=True)
            if not issue or not issue.organization_id or not issue.repository_id:
                log.warning(
                    "github.badge.embed_on_issue",
                    error="issue not found",
                    issue_id=issue_id,
                )
                return

            (
                external_organization,
                repository,
            ) = await get_external_organization_and_repo(
                session, issue.organization_id, issue.repository_id, allow_deleted=True
            )

            try:
                await github_issue.remove_polar_label(
                    session,
                    get_worker_redis(ctx),
                    organization=external_organization,
                    repository=repository,
                    issue=issue,
                )
            except httpx.HTTPError as e:
                raise Retry(compute_backoff(ctx["job_try"])) from e
