# VeriCert Authentication Implementation Plan

## Objective

Implement secure local email/password authentication for VeriCert students and administrators. Google Authentication is out of scope for this release. Replace PBKDF2 completely with Argon2id, support secure student account provisioning, and allow students to change and reset passwords.

**Core rules**
- Store password hashes, never plaintext passwords.
- Treat temporary credentials and reset links as secrets.
- Enforce authentication state and permissions on the backend for every protected request.
- Use shared infrastructure for security controls that must work across multiple application workers or instances.

## 1. Target Authentication Design

### Student authentication
- Students sign in with their registered email and password.
- The backend verifies the Argon2id password hash, account status, and student role.
- Newly provisioned students must change their temporary password before accessing normal student features.
- Students can later change their password after verifying their current password.
- Students can request a password reset through a verified recovery channel.
- Students can access only their own certificates and permitted student resources.

### Administrator authentication
- Administrators use local email/password authentication.
- Administrator permissions are checked by the backend on every protected operation.
- MFA is out of scope for this implementation, as decided.
- Use strong passwords, distributed rate limiting, secure sessions, and strict authorization.
- Do not use default production credentials or insecure fallback secrets.

### Authentication flow
1. User submits email and password.
2. FastAPI applies distributed rate limiting and validates the request.
3. Backend finds the account and verifies its Argon2id password hash.
4. Backend checks account status, role, and password-change restrictions.
5. Backend issues a secure session.
6. On every protected request, the backend checks current account/session state and permissions.
7. Frontend routes the user based on the role returned by the backend. The frontend is not the authority for permissions.

## 2. Phase 1 — Update the Database and Account Model

**Files:** `models.py`, `database.py`, and the project's migration system.

Add or confirm the following fields and records:

- `email`: unique login identifier.
- `password_hash`: Argon2id hash only.
- `is_active`: whether the account can authenticate and use the system.
- `must_change_password`: whether the user must change a temporary password before normal access.
- `password_changed_at`: timestamp of the most recent password change.
- `token_version`: integer incremented to revoke tokens issued under earlier account state, if using versioned bearer tokens.
- An explicit role/account type sufficient to distinguish students from platform administrators.
- Student identifiers such as roll number where applicable.

Also:
- Add appropriate unique constraints and indexes.
- Create proper migrations. Do not rely on `create_all()` alone to update existing tables.
- Add a password-reset-token table containing the account ID, SHA-256 token hash, expiry timestamp, used/revoked state, and creation timestamp. Add indexes and a uniqueness rule for token hashes.
- If using server-side sessions, add a session store/table or use a suitable shared session backend with expiry and revocation support.
- Remove Google-specific account assumptions and Google-derived password behavior.
- Never store plaintext passwords, temporary passwords, raw reset tokens, or session tokens in the database.

## 3. Phase 2 — Replace Password Hashing and Harden Authentication

**Files:** `auth.py` and authentication-related configuration.

### Password hashing
- Remove PBKDF2 completely. Use Argon2id for all password hashing and verification: account provisioning, password changes, password resets, and administrator bootstrap.
- Use a maintained library with Argon2 support, such as `pwdlib` with its Argon2 extra.
- Choose and document Argon2id parameters, then benchmark them on the deployment environment. Use the library's supported secure defaults as a baseline and tune for the expected workload.
- Do not invent a custom password-hashing scheme or silently fall back to another algorithm.
- Add a repository check or test that fails if PBKDF2 password-hashing code remains.

### Sessions and token revocation

Prefer **stateful server-side sessions** for the browser application when practical:
- Give the browser a high-entropy opaque session ID in a `Secure`, `HttpOnly`, appropriately `SameSite` cookie.
- Store session state in a shared server-side store with expiry and revocation support.
- On each protected request, load the current session and account state, and reject expired, revoked, or invalid sessions.
- Enforce `must_change_password` using the current database/account state on every protected request, not a stale claim copied into a login token.
- When `must_change_password` is true, permit only the minimum routes needed to change the password, sign out, and use any necessary account-recovery flow. Enforce this restriction in a central backend dependency/middleware so it cannot be bypassed by calling APIs directly.
- After a successful password change or reset, set `must_change_password = false` when appropriate, update `password_changed_at`, revoke all existing sessions for the account, and require a fresh login or issue a newly created session under the new state.
- Account deactivation must also invalidate active sessions.

If stateless bearer tokens are required instead:
- Include an account `token_version` in each token and compare it against the current database value on every protected request. Increment it on password change, password reset, and account deactivation.
- Also read the current `must_change_password` state from the database on every protected request; do not trust a stale token claim for this decision.
- If the application does not check current account state or token version on each request, it cannot guarantee immediate revocation. Do not describe such tokens as immediately revocable.

### Secrets and deployment
- Remove hardcoded fallback token secrets.
- Require strong secrets from environment configuration or a secret manager and fail startup in production if required secrets are missing.
- Use HTTPS in deployed environments.
- If using cookies, implement CSRF protection for state-changing requests where applicable.
- Never log passwords, hashes, session IDs, reset tokens, or authorization headers.

## 4. Phase 3 — Distributed Rate Limiting

**Requirement:** Rate limits must be shared across Uvicorn workers and application instances. Do not use an in-memory Python dictionary as the authoritative production limiter.

- Use a shared Redis instance or another atomic, shared rate-limit backend.
- Integrate a maintained FastAPI-compatible limiter, such as `fastapi-limiter` or an equivalent library, configured to use Redis. Confirm the selected library's current maintenance status and API before implementation.
- Configure limits for login, forgot-password, reset-password, and other sensitive authentication endpoints.
- Apply limits by a combination of client IP and normalized account identifier where appropriate. Avoid allowing an attacker to lock out a victim indefinitely through an account-only counter.
- Use atomic counters/expiry operations or the limiter's supported atomic implementation to prevent race conditions.
- Return HTTP `429 Too Many Requests` when limits are exceeded, with appropriate retry information.
- Fail safely if the shared rate-limit service is unavailable: do not silently switch to an unbounded in-memory limiter. Define and document the availability policy for authentication endpoints.
- Protect the Redis service with network isolation and authentication; do not expose it publicly.
- Test limits with multiple workers or instances to verify that requests share the same counters.

If Redis is not available in local development, a development-only fallback may be used with a clear warning. It must not be enabled in production.

## 5. Phase 4 — Secure Administrator Bootstrap

- Remove the default admin email/password fallback.
- Provide a controlled one-time administrator initialization process, or require bootstrap credentials through secure environment configuration.
- Use Argon2id for the initial admin password.
- Do not place bootstrap credentials in source code, version control, logs, or deployment artifacts.
- Prevent bootstrap initialization from being reused after completion unless an explicit protected recovery procedure is followed.
- Assign administrator privileges only through a trusted backend process and audit the event.

## 6. Phase 5 — Student Account Provisioning

**Files:** `main.py` and an account-management service/module if appropriate.

- Only an authorized administrator can create or import student accounts.
- Validate student email addresses and identifiers; reject duplicates.
- Generate a unique, cryptographically random temporary password for each student, or preferably create a one-time activation flow.
- Store only the Argon2id hash of a temporary password.
- Set `must_change_password = true` for accounts provisioned with temporary passwords.
- Record account creation and export actions in the audit log without recording secrets.
- Ensure temporary credentials never appear in application logs, error messages, analytics, or general admin listings.

### Credentials export safeguards

If a CSV export is implemented, it will contain plaintext temporary passwords and must be treated as highly sensitive.

- Restrict export access to explicitly authorized administrators.
- Generate the file only on demand and avoid retaining it longer than necessary.
- Protect it during storage and transfer, and distribute it through a restricted channel.
- Never include password hashes, reset tokens, or session tokens.
- Never export permanent passwords.
- Require a password change at first login.
- Prefer one-time activation links as the safer long-term option.

## 7. Phase 6 — Password Change and Recovery

Implement endpoints following the existing API conventions:

| Endpoint | Purpose |
|---|---|
| `POST /auth/login` | Authenticate and return the verified role and current password-change status. |
| `POST /auth/change-password` | Verify the current password, validate the new password, and save a new Argon2id hash. |
| `POST /auth/forgot-password` | Start account recovery without revealing whether an email is registered. |
| `POST /auth/reset-password` | Set a new password using a valid, single-use, expiring reset token. |

### Password change
- Require the current password for an authenticated password change.
- Enforce a documented password policy.
- Set `must_change_password = false` after a successful initial password change.
- Update `password_changed_at`.
- Revoke all existing sessions or increment `token_version` and validate it on every request.
- Require a fresh login after revocation, unless a new session is deliberately issued after the password update.

### Password-reset token generation, storage, and validation
- Generate a cryptographically random token with at least 256 bits of entropy, using a secure system random generator.
- Encode it for safe transport in a URL or form.
- Hash the complete token string with SHA-256 before storing it. A high-entropy random token does not need a slow password hash; SHA-256 is appropriate for lookup and comparison.
- When a reset request arrives, hash the submitted token with the same SHA-256 procedure and look up the matching record. Compare hashes safely and validate the account, expiry, and unused/unrevoked status.
- Store only the token hash, never the raw token.
- Set a short, documented expiry and mark the token consumed atomically during a successful reset.
- On a new reset request for an account, invalidate all prior unused reset tokens for that account before creating a new one. Only the newest reset token should remain valid.
- Make token validation and consumption race-safe with a database transaction and row locking or an equivalent atomic operation, so two simultaneous submissions cannot both succeed.
- Rate-limit reset requests and submissions. Use generic responses to reduce account enumeration.
- After a successful reset, update the password hash and `password_changed_at`, clear `must_change_password` when appropriate, invalidate active sessions, and revoke all outstanding reset tokens for the account.
- Send the raw token only through the verified recovery channel; never log it or include it in analytics.

## 8. Phase 7 — Remove Google Authentication and PBKDF2

**Files:** `main.py`, request schemas, authentication modules, configuration, dependencies, and frontend login components.

- Remove Google login endpoints, Google-specific request models, token verification, and Google account-creation logic.
- Remove Google-only configuration and dependencies that are no longer needed.
- Remove predictable `google:{email}` password behavior completely.
- Remove PBKDF2 hashing and verification code, imports, dependencies used only by it, and tests tied to it.
- Search the repository for remaining Google Auth and PBKDF2 references. Remove obsolete code without deleting unrelated functionality.
- Ensure local email/password is the only supported login method for this release.
- Keep authentication modules structured so Google Auth can be added later without bypassing account provisioning or authorization.

## 9. Phase 8 — Frontend Updates

**Frontend:** React/Vite.

- Provide a clear email/password login screen.
- Route users using the role returned by the backend.
- Add a first-login password-change screen.
- Add password-change controls in student account settings.
- Add forgot-password and reset-password screens if recovery is enabled.
- Add administrator student-management and credentials-export controls.
- Display clear, non-sensitive errors for invalid credentials, inactive accounts, expired sessions, and password-policy failures.
- Handle expired and revoked sessions cleanly.
- Never store passwords in browser storage or include them in URLs, analytics, or client logs.
- Treat frontend route guards as usability features only; all access restrictions must also be enforced by the backend.

## 10. Phase 9 — Security and Concurrency Testing

### Accounts and authorization
- [ ] Administrator bootstrap does not use default production credentials.
- [ ] Only authorized administrators can create, import, disable, or export student accounts.
- [ ] Duplicate student accounts are rejected.
- [ ] Inactive accounts cannot sign in or continue using existing sessions.
- [ ] Students cannot access administrator endpoints through direct API requests.
- [ ] Students can access only their own certificates and permitted resources.

### Temporary-password state machine
- [ ] Login for a temporary-password account sets `must_change_password = true` in current account state.
- [ ] While the flag is true, normal protected endpoints are rejected by backend middleware/dependencies.
- [ ] Password-change and sign-out endpoints remain available in the restricted state.
- [ ] A successful change sets `must_change_password = false` and updates `password_changed_at`.
- [ ] Old sessions are rejected after the password change.
- [ ] A token issued before the change cannot bypass the restricted state or regain access.
- [ ] A fresh login has normal access only after the backend confirms the updated account state.

### Password reset
- [ ] Reset tokens are generated with a cryptographically secure random generator and at least 256 bits of entropy.
- [ ] Only SHA-256 token hashes are stored; raw reset tokens are not persisted.
- [ ] Expired, used, revoked, or unknown tokens are rejected.
- [ ] A new reset request invalidates earlier unused reset tokens for that account.
- [ ] Two simultaneous submissions of the same token cannot both succeed.
- [ ] Successful reset revokes outstanding reset tokens and existing sessions.
- [ ] Recovery responses do not reveal whether an account exists.

### Rate limiting
- [ ] Login and recovery limits use shared Redis-backed state in production.
- [ ] Limits are consistent across multiple Uvicorn workers and application instances.
- [ ] Concurrent requests cannot bypass limits through race conditions.
- [ ] Exceeding a limit returns HTTP `429`.
- [ ] Loss of Redis does not silently disable production rate limiting.
- [ ] Redis is not publicly accessible.

### Passwords and operations
- [ ] Only Argon2id is used; no PBKDF2 password-hashing path remains.
- [ ] Passwords and tokens never appear in logs or API responses.
- [ ] Secrets are securely configured and missing required production secrets prevent startup.
- [ ] HTTPS, cookie security, and CSRF protections are configured where applicable.
- [ ] Credentials exports are restricted, audited, and handled as sensitive files.
- [ ] Audit logs record security-relevant events without secrets.
- [ ] Direct API authorization tests pass independently of frontend behavior.

## 11. Definition of Done

The implementation is complete when:

1. Local email/password authentication works for students and administrators.
2. Password hashing and verification use Argon2id exclusively.
3. Google Authentication and predictable Google-derived passwords are removed.
4. Student accounts can be provisioned securely with temporary credentials or activation links.
5. Students must change temporary passwords and can later change or reset their passwords.
6. Backend checks the current `must_change_password` and account status on every protected request.
7. Password changes, resets, and deactivation revoke sessions reliably.
8. Reset-token generation, hashing, expiry, single-use consumption, and replacement are implemented atomically.
9. Production rate limiting is shared across workers and instances.
10. Role and account-status checks are enforced server-side.
11. Database changes are managed through migrations.
12. No default production credentials, hardcoded fallback secrets, PBKDF2 code, or secret values in logs remain.
13. The security and concurrency test checklists pass.

## Recommended Implementation Order

1. Database models, reset-token table, and migrations.
2. Argon2id and session/revocation architecture.
3. Central backend enforcement of account status and `must_change_password`.
4. Shared Redis-backed rate limiting.
5. Secure administrator bootstrap and role enforcement.
6. Student provisioning and temporary-credentials/activation flow.
7. Password change and reset endpoints with atomic token consumption.
8. Remove Google Auth and all PBKDF2 code.
9. Frontend login, first-login password change, and account settings.
10. Security, concurrency, and multi-worker tests.
11. Production configuration and deployment review.
