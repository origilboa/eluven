# Admin Panel v1

**Status:** Accepted  
**Date:** 2026-06-02  
**Scope:** Org, user, and invitation management. Budget/cost/usage deferred.

## Defaults (June 2026)

| Decision | Choice |
|----------|--------|
| Invite delivery | Copy-link only (no SES email) |
| Org admin invite roles | `user` and `org_admin` |
| User creation | Invite-only (no temp-password shortcut) |
| Platform org | Visible to `app_admin`; name/slug locked |

## Roles

| Capability | `app_admin` | `org_admin` | `user` |
|------------|-------------|-------------|--------|
| Admin nav + `/admin` | ✓ | ✓ | ✗ |
| Manage orgs | all | ✗ | ✗ |
| Manage users | all orgs | own org | ✗ |
| Invite users | any org | own org | ✗ |
| Assign `app_admin` | ✓ | ✗ | ✗ |
| Deactivate users | ✓ | own org (not self, not `app_admin`) | ✗ |

## Invite flow

1. Admin submits invite (email, name, role, org for `app_admin`).
2. API creates `user_invitations` row with hashed token; returns **one-time** invite URL.
3. Admin copies link and sends manually.
4. Invitee opens `/{locale}/accept-invite?token=…`, sets password.
5. `POST /api/v1/auth/accept-invite` creates user, marks invite accepted, returns auth tokens.

Token expires in 7 days (configurable via `INVITATION_EXPIRE_DAYS`).

## API (Section 10.9)

```
GET    /api/v1/admin/orgs
POST   /api/v1/admin/orgs
GET    /api/v1/admin/orgs/{org_id}
PATCH  /api/v1/admin/orgs/{org_id}

GET    /api/v1/admin/users
GET    /api/v1/admin/users/{user_id}
PATCH  /api/v1/admin/users/{user_id}

GET    /api/v1/admin/invitations
POST   /api/v1/admin/invitations
DELETE /api/v1/admin/invitations/{invitation_id}

GET    /api/v1/auth/invitations/preview?token=
POST   /api/v1/auth/accept-invite
```

## Platform org

- ID: `00000000-0000-0000-0000-000000000001`
- Slug: `eluven`
- `app_admin` may toggle `is_active` only; name and slug are read-only.

## Activity library (app_admin)

Platform thread types (ActivityLibrary) are managed under Admin → **Activity library**:

```
GET    /api/v1/admin/activity-library
GET    /api/v1/admin/activity-library/{entry_id}
POST   /api/v1/admin/activity-library
PATCH  /api/v1/admin/activity-library/{entry_id}
PUT    /api/v1/admin/activity-library/{entry_id}/prompts
```

Editable fields include `default_instruction_content` (copied to each new Thread on create), model routing, token budget, and activity prompts. `thread_type` slug is immutable after create.

Activity Type Studio (guided wizard + quick create with instruction and prompt assistants) is specified in [activity-type-studio-v1.md](activity-type-studio-v1.md).

## Out of scope

Budget, usage, storage quotas, SES email, self-registration, user deletion, audit log UI.
