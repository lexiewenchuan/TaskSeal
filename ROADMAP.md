# TaskSeal Roadmap

TaskSeal follows a design-first path: stabilize the boundaries that protect
real work, then build the smallest reference runtime that proves them.

## v0.1 — Design preview

- [x] Task-first architecture
- [x] Work Item ontology and JSON Schema
- [x] Authorization, evidence, acceptance, and growth boundaries
- [x] Architecture diagrams and design narrative
- [x] Public contribution and security policies

## v0.2 — Local reference kernel

- [ ] Event-backed Work Item state machine
- [ ] Policy evaluator for subject, resource, action, condition, and expiry
- [ ] Local filesystem resource gateway
- [ ] Evidence records bound to acceptance criteria and resource revisions
- [ ] Deterministic acceptance checks
- [ ] Command-line task inspection and replay

## v0.3 — One trustworthy workflow

- [ ] End-to-end software-change demo
- [ ] One agent-runtime adapter
- [ ] Independent verifier process
- [ ] Conflict detection for concurrent resource writes
- [ ] Pause, resume, repair, and rollback paths
- [ ] Trace viewer for decisions, actions, evidence, and acceptance

## v0.4 — Runtime and domain ecosystem

- [ ] Adapter contract and compatibility suite
- [ ] Additional agent-runtime adapters
- [ ] Document and data workflow examples
- [ ] Capability registry and reuse decisions
- [ ] Evaluation datasets and regression gates

## v0.5 — Controlled capability growth

- [ ] Trace-to-case curation
- [ ] Candidate capability packaging
- [ ] Isolated evaluation and risk review
- [ ] Canary promotion and rollback
- [ ] Capability lineage and version history

## Non-goals

TaskSeal does not aim to:

- build another foundation model;
- replace existing agent loops or workflow engines;
- make unsupervised production changes by default;
- treat model confidence as acceptance evidence;
- allow a running agent to promote its own capabilities.

Milestones may change as contracts are tested against real, sanitized use cases.
Open a design proposal if a missing boundary blocks your use case.
