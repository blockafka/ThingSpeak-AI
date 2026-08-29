# Fine-Grained DNA Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the six whole-style DNA templates with a static mock library of six fine-grained DNA dimensions, twenty fragments per dimension, and select one fragment per dimension from per-dimension Top 10 candidates.

**Architecture:** JSON files under `wuyan_ai/core/dnas/fragments/` are the only active DNA source. A fragment library loads and validates the six files, filters retired entries, and sorts by the precomputed mock `score`. Analyzer receives six Top-10 pools in one prompt and returns one selected fragment for each dimension; creator consumes those selected fragments. Extraction, staging-cache, publication tracking, and score updates remain out of scope.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, pytest, React 19, Vite.

## Global Constraints

- Keep the six required fragment types: `scene`, `valuePromise`, `hook`, `structure`, `tone`, `visualStyle`.
- Provide exactly 20 mock fragments for each type.
- Delete the old active whole-DNA JSON files under `wuyan_ai/core/dnas/data/`.
- Do not add extraction, cache, publication tracking, scheduled metric collection, or live score calculation.
- Do not place API keys in source files, tests, or committed environment files.
- Keep LLM failure fallback deterministic so the demo still produces a result.

### Task 1: Define the new fragment contract with failing tests

**Files:**
- Create: `tests/test_fine_grained_dna.py`
- Modify: `tests/test_wuyan_ai.py` (replace obsolete imports/tests with current contract tests)

- [x] Write tests for six files, twenty entries per file, valid IDs/types/scores, Top-10 ordering, grouped analyzer prompt, and one-selection-per-dimension validation.
- [x] Run `pytest tests/test_fine_grained_dna.py -q` and confirm failure because the new library and schemas did not exist before implementation.

### Task 2: Implement the fragment library and mock data

**Files:**
- Create: `wuyan_ai/core/dnas/fragments/scene.json`
- Create: `wuyan_ai/core/dnas/fragments/value_promise.json`
- Create: `wuyan_ai/core/dnas/fragments/hook.json`
- Create: `wuyan_ai/core/dnas/fragments/structure.json`
- Create: `wuyan_ai/core/dnas/fragments/tone.json`
- Create: `wuyan_ai/core/dnas/fragments/visual_style.json`
- Modify: `wuyan_ai/core/dnas/library.py`
- Modify: `wuyan_ai/core/dnas/__init__.py`
- Delete: `wuyan_ai/core/dnas/data/bestie_travel_share.json`
- Delete: `wuyan_ai/core/dnas/data/cultural_story.json`
- Delete: `wuyan_ai/core/dnas/data/gift_guide.json`
- Delete: `wuyan_ai/core/dnas/data/healthy_snack.json`
- Delete: `wuyan_ai/core/dnas/data/local_recommend.json`
- Delete: `wuyan_ai/core/dnas/data/weird_snack_review.json`

- [x] Add a loader with `list_fragments`, `get_fragment`, `get_top_fragments`, and `get_top_fragments_by_type`.
- [x] Sort by static `score` descending and exclude `retired`; keep score components as mock metadata for the future tracking phase.
- [x] Run the focused tests and confirm the library contract passes.

### Task 3: Refactor analyzer schemas, prompt, and fallback

**Files:**
- Modify: `wuyan_ai/core/schemas.py`
- Modify: `wuyan_ai/core/agents/analyzer/agent.py`
- Modify: `wuyan_ai/core/agents/analyzer/_prompts.py`
- Modify: `wuyan_ai/core/orchestrator.py`

- [x] Add `DnaFragmentSelection` and replace whole-DNA `dna_matches` in the internal brief/result with `selected_fragments`.
- [x] Build one grouped prompt containing six Top-10 pools; require one valid selection per type.
- [x] Keep one analyzer LLM call, validate IDs against the pools, and choose each dimension's Top-1 fragment in the deterministic fallback.
- [x] Run analyzer tests and the full backend test suite.

### Task 4: Refactor creator and frontend presentation

**Files:**
- Modify: `wuyan_ai/core/agents/creator/agent.py`
- Modify: `wuyan_ai/core/agents/creator/_prompts.py`
- Modify: `web/src/components/GeneratingView.jsx`
- Modify: `web/src/components/ResultView.jsx`
- Modify: `web/src/components/DnaDashboard.jsx`

- [x] Pass selected fragment definitions to creator and render the six dimensions instead of primary/supporting whole DNA weights.
- [x] Keep existing note/image output and rule fallback behavior.
- [x] Update the dashboard wording and counts to describe the 120-fragment mock library rather than obsolete whole DNA styles.
- [x] Run `npm run build` and backend tests.

### Task 5: Update documentation and verify the final diff

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`

- [x] Document the six-file fragment library, per-dimension Top-10 recall, one-call AI selection, and explicitly deferred tracking.
- [x] Run `pytest -q`, `npm run build`, and inspect `git diff --check`.
- [x] Confirm no API key or obsolete active DNA JSON remains in the diff.
