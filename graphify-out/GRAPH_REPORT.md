# Graph Report - vericert  (2026-10-17)

## Corpus Check
- 29 files · ~13,822 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: (none) 3, .css 2, .example 1)

## Summary
- 367 nodes · 801 edges · 13 communities (10 shown, 3 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 85 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c337ecd3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- package.json
- request
- urllib
- main.py
- models.py
- storage.py
- auth.py
- VeriCert Authentication Implementation Plan
- React + Vite
- VeriCert
- rate_limit.py
- on_event
- UploadFile

## God Nodes (most connected - your core abstractions)
1. `User` - 42 edges
2. `request()` - 29 edges
3. `TemplateVersion` - 18 edges
4. `require_club_access()` - 17 edges
5. `StudentPrivacyTests` - 17 edges
6. `Base` - 15 edges
7. `VeriCert Authentication Implementation Plan` - 14 edges
8. `issue_batch()` - 13 edges
9. `Issuance` - 13 edges
10. `hash_password()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Security Notes (Practical)` --references--> `require_club_access()`  [INFERRED]
  README.md → backend/auth.py
- `reset_admin_password()` --uses--> `User`  [INFERRED]
  backend/admin_cli.py → backend/models.py
- `provision_student()` --indirect_call--> `hash_password()`  [INFERRED]
  backend/main.py → backend/auth.py
- `reset_password()` --indirect_call--> `hash_password()`  [INFERRED]
  backend/main.py → backend/auth.py
- `create_token()` --uses--> `User`  [INFERRED]
  backend/auth.py → backend/models.py

## Import Cycles
- None detected.

## Communities (13 total, 3 thin omitted)

### Community 0 - "package.json"
Cohesion: 0.06
Nodes (33): dependencies, react, react-dom, devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh (+25 more)

### Community 1 - "request"
Cohesion: 0.07
Nodes (42): API, formatDetail(), request(), saveBlob(), AdminPasswordChange(), submit(), App(), builtins (+34 more)

### Community 3 - "main.py"
Cohesion: 0.09
Nodes (70): get_db(), require_club_access(), verify_password(), add_member(), audit_security_event(), change_password(), ChangePasswordRequest, ClubRequest (+62 more)

### Community 4 - "models.py"
Cohesion: 0.07
Nodes (38): alembic, alembic_config, argon2, argparse, backend, bootstrap_admin(), main(), normalized_email() (+30 more)

### Community 5 - "storage.py"
Cohesion: 0.17
Nodes (14): render_certificate(), _value_for(), UploadFile, save_template_artwork(), template_path(), _validate_file_signature(), io, Path (+6 more)

### Community 6 - "auth.py"
Cohesion: 0.09
Nodes (31): argon2_exceptions, create_token(), _decode_urlsafe(), _encode_urlsafe(), get_authenticated_user(), get_current_user(), get_platform_admin(), get_token_secret() (+23 more)

### Community 7 - "VeriCert Authentication Implementation Plan"
Cohesion: 0.07
Nodes (28): 10. Phase 9 — Security and Concurrency Testing, 11. Definition of Done, 1. Target Authentication Design, 2. Phase 1 — Update the Database and Account Model, 3. Phase 2 — Replace Password Hashing and Harden Authentication, 4. Phase 3 — Distributed Rate Limiting, 5. Phase 4 — Secure Administrator Bootstrap, 6. Phase 5 — Student Account Provisioning (+20 more)

### Community 8 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the ESLint configuration, React Compiler, React + Vite

### Community 9 - "VeriCert"
Cohesion: 0.07
Nodes (28): 1) Clubs & Templates (Design-time), 1) Start the backend (FastAPI), 1) Template creation, 2) Events (Where templates are used), 2) Publish, 2) Start the frontend (React + Vite), 3) Issuance (Run-time), 3) Issuing (+20 more)

### Community 10 - "rate_limit.py"
Cohesion: 0.10
Nodes (16): asyncio, AuthRateLimiter, Request, RateLimitTests, consume(), SharedCounter, test_request(), hashlib (+8 more)

## Knowledge Gaps
- **69 isolated node(s):** `Objective`, `Student authentication`, `Administrator authentication`, `Authentication flow`, `2. Phase 1 — Update the Database and Account Model` (+64 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 142 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `require_club_access()` connect `main.py` to `VeriCert`, `auth.py`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `Security Notes (Practical)` connect `VeriCert` to `main.py`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Are the 34 inferred relationships involving `User` (e.g. with `reset_admin_password()` and `create_token()`) actually correct?**
  _`User` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `TemplateVersion` (e.g. with `create_event()` and `deliver()`) actually correct?**
  _`TemplateVersion` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `require_club_access()` (e.g. with `Membership` and `User`) actually correct?**
  _`require_club_access()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Objective`, `Student authentication`, `Administrator authentication` to the rest of the system?**
  _69 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `package.json` be split into smaller, more focused modules?**
  _Cohesion score 0.06190476190476191 - nodes in this community are weakly interconnected._