# Graph Report - vericert  (2026-09-19)

## Corpus Check
- 17 files · ~7,798 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 3, .css 3, .example 1)

## Summary
- 230 nodes · 509 edges · 10 communities (9 shown, 1 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 68 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d6925e63`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- package.json
- App.jsx
- main.py
- User
- auth.py
- storage.py
- crypto.py
- UploadFile
- React + Vite
- VeriCert

## God Nodes (most connected - your core abstractions)
1. `User` - 32 edges
2. `TemplateVersion` - 18 edges
3. `require_club_access()` - 17 edges
4. `request()` - 14 edges
5. `issue_batch()` - 13 edges
6. `Issuance` - 13 edges
7. `VeriCert` - 11 edges
8. `Event` - 11 edges
9. `StudentPrivacyTests` - 11 edges
10. `Base` - 10 edges

## Surprising Connections (you probably didn't know these)
- `Security Notes (Practical)` --references--> `require_club_access()`  [INFERRED]
  README.md → backend/auth.py
- `create_token()` --uses--> `User`  [INFERRED]
  backend/auth.py → backend/models.py
- `get_current_user()` --uses--> `User`  [INFERRED]
  backend/auth.py → backend/models.py
- `require_club_access()` --uses--> `Membership`  [INFERRED]
  backend/auth.py → backend/models.py
- `get_event_for_user()` --uses--> `Club`  [INFERRED]
  backend/main.py → backend/models.py

## Import Cycles
- None detected.

## Communities (10 total, 1 thin omitted)

### Community 0 - "package.json"
Cohesion: 0.06
Nodes (33): dependencies, react, react-dom, devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh (+25 more)

### Community 1 - "App.jsx"
Cohesion: 0.11
Nodes (22): App(), builtins, Events(), History(), getPdf(), Issue(), Login(), submit() (+14 more)

### Community 2 - "main.py"
Cohesion: 0.11
Nodes (29): create_token(), get_current_user(), hash_password(), Session, verify_password(), ClubRequest, EventRequest, GoogleStudentLoginRequest (+21 more)

### Community 3 - "User"
Cohesion: 0.18
Nodes (35): require_club_access(), add_member(), create_event(), create_issuance(), deliver(), download_by_roll_number(), download_selected_certificate(), get_event_for_user() (+27 more)

### Community 4 - "auth.py"
Cohesion: 0.11
Nodes (23): get_db(), generate_keys(), Base, init_database(), create_club(), list_clubs(), startup(), Club (+15 more)

### Community 5 - "storage.py"
Cohesion: 0.13
Nodes (17): render_certificate(), _value_for(), UploadFile, save_template_artwork(), template_path(), fastapi, io, os (+9 more)

### Community 6 - "crypto.py"
Cohesion: 0.25
Nodes (12): create_credential(), calculate_hash(), canonical_json(), load_private_key(), load_public_key(), sign_data(), verify_signature(), verify_certificate() (+4 more)

### Community 8 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the ESLint configuration, React Compiler, React + Vite

### Community 9 - "VeriCert"
Cohesion: 0.07
Nodes (27): 1) Clubs & Templates (Design-time), 1) Start the backend (FastAPI), 1) Template creation, 2) Events (Where templates are used), 2) Publish, 2) Start the frontend (React + Vite), 3) Issuance (Run-time), 3) Issuing (+19 more)

## Knowledge Gaps
- **46 isolated node(s):** `1) Clubs & Templates (Design-time)`, `2) Events (Where templates are used)`, `3) Issuance (Run-time)`, `4) Verification (Public)`, `Project Layout` (+41 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 90 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `require_club_access()` connect `User` to `VeriCert`, `main.py`, `auth.py`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Why does `Security Notes (Practical)` connect `VeriCert` to `User`?**
  _High betweenness centrality (0.135) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `User` (e.g. with `create_token()` and `get_current_user()`) actually correct?**
  _`User` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `TemplateVersion` (e.g. with `create_event()` and `deliver()`) actually correct?**
  _`TemplateVersion` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `require_club_access()` (e.g. with `Membership` and `User`) actually correct?**
  _`require_club_access()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `1) Clubs & Templates (Design-time)`, `2) Events (Where templates are used)`, `3) Issuance (Run-time)` to the rest of the system?**
  _46 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `package.json` be split into smaller, more focused modules?**
  _Cohesion score 0.06190476190476191 - nodes in this community are weakly interconnected._