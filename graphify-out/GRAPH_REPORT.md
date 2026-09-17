# Graph Report - vericert  (2026-09-17)

## Corpus Check
- 15 files · ~5,682 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .css 2, .example 1)

## Summary
- 182 nodes · 425 edges · 9 communities
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 57 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `131f2dc4`
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
- issue_batch
- React + Vite

## God Nodes (most connected - your core abstractions)
1. `User` - 25 edges
2. `require_club_access()` - 16 edges
3. `TemplateVersion` - 15 edges
4. `issue_batch()` - 13 edges
5. `request()` - 12 edges
6. `Base` - 10 edges
7. `create_issuance()` - 10 edges
8. `issue_certificate()` - 10 edges
9. `Issuance` - 10 edges
10. `get_event_for_user()` - 9 edges

## Surprising Connections (you probably didn't know these)
- `create_token()` --uses--> `User`  [INFERRED]
  backend/auth.py → backend/models.py
- `get_current_user()` --uses--> `User`  [INFERRED]
  backend/auth.py → backend/models.py
- `validate_template()` --uses--> `TemplateVersion`  [INFERRED]
  backend/main.py → backend/models.py
- `get_event_for_user()` --uses--> `Club`  [INFERRED]
  backend/main.py → backend/models.py
- `get_event_for_user()` --uses--> `Event`  [INFERRED]
  backend/main.py → backend/models.py

## Import Cycles
- None detected.

## Communities (9 total, 0 thin omitted)

### Community 0 - "package.json"
Cohesion: 0.06
Nodes (33): dependencies, react, react-dom, devDependencies, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh (+25 more)

### Community 1 - "App.jsx"
Cohesion: 0.11
Nodes (21): App(), builtins, Events(), History(), getPdf(), Issue(), Login(), submit() (+13 more)

### Community 2 - "main.py"
Cohesion: 0.12
Nodes (25): create_token(), get_db(), hash_password(), verify_password(), generate_keys(), init_database(), ClubRequest, deliver() (+17 more)

### Community 3 - "User"
Cohesion: 0.28
Nodes (23): require_club_access(), add_member(), create_club(), create_event(), download_selected_certificate(), get_event_for_user(), list_clubs(), list_events() (+15 more)

### Community 4 - "auth.py"
Cohesion: 0.14
Nodes (19): get_current_user(), Session, Base, download_by_roll_number(), Return public certificate choices for a roll number., Club, DeliveryAttempt, Event (+11 more)

### Community 5 - "storage.py"
Cohesion: 0.13
Nodes (17): render_certificate(), _value_for(), UploadFile, save_template_artwork(), template_path(), fastapi, io, os (+9 more)

### Community 6 - "crypto.py"
Cohesion: 0.26
Nodes (12): create_credential(), calculate_hash(), canonical_json(), load_private_key(), load_public_key(), sign_data(), verify_signature(), verify_certificate() (+4 more)

### Community 7 - "issue_batch"
Cohesion: 0.43
Nodes (8): create_issuance(), issue_batch(), issue_certificate(), IssueRequest, UploadFile, smtp_enabled(), validate_template(), BackgroundTasks

### Community 8 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the ESLint configuration, React Compiler, React + Vite

## Knowledge Gaps
- **26 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 61 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `App.jsx` to `package.json`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `User` (e.g. with `create_token()` and `get_current_user()`) actually correct?**
  _`User` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `require_club_access()` (e.g. with `Membership` and `User`) actually correct?**
  _`require_club_access()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `TemplateVersion` (e.g. with `create_event()` and `deliver()`) actually correct?**
  _`TemplateVersion` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `issue_batch()` (e.g. with `deliver()` and `DeliveryAttempt`) actually correct?**
  _`issue_batch()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _26 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `package.json` be split into smaller, more focused modules?**
  _Cohesion score 0.06190476190476191 - nodes in this community are weakly interconnected._