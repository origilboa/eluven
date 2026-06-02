"""Shared constants for Eluven seed scripts."""

from __future__ import annotations

PLATFORM_ORG_SLUG = "eluven"
DEV_ORG_SLUG = "dev-org"
DEV_ORG_NAME = "Dev Org"

DEMO_ORG_B_SLUG = "demo-org-b"
DEMO_ORG_B_NAME = "Demo Org B"

DEV_USER_EMAIL = "dev@eluven.ai"
DEV_USER_PASSWORD = "devpassword123"
DEV_USER_NAME = "Dev User"

ORG_ADMIN_USER_EMAIL = "orgadmin@eluven.ai"
ORG_ADMIN_USER_PASSWORD = "orgadminpassword123"
ORG_ADMIN_USER_NAME = "Org Admin User"

REVIEWER_USER_EMAIL = "reviewer@eluven.ai"
REVIEWER_USER_PASSWORD = "reviewpassword123"
REVIEWER_USER_NAME = "Reviewer User"

DEMO_INVITEE_EMAIL = "invitee@eluven.ai"
DEMO_INVITEE_NAME = "Demo Invitee"
# Dev-only token for accept-invite smoke tests (documented in sample-data.md).
DEMO_INVITATION_TOKEN = "demo-invite-token-for-mvp-testing-only"

MVP_MODULE_EPR = "external_paper_review"
MVP_MODULE_SPR = "student_paper_review"

# Platform workflow templates (migration 006)
TEMPLATE_EPR_FULL_ID = "02000001-0001-4001-8001-000000000001"
TEMPLATE_SPR_FULL_ID = "02000002-0001-4001-8001-000000000001"

EMBEDDING_DIMENSION = 1536
