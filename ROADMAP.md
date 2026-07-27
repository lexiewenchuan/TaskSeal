# TaskSeal Roadmap

TaskSeal grows by proving one trustworthy boundary at a time.

## v0.1 — Local reference kernel

- [x] Durable Work Item model
- [x] Legal lifecycle state machine
- [x] Resource- and action-scoped authorization
- [x] Non-expanding delegation
- [x] Local filesystem resource gateway
- [x] Path-escape protection
- [x] Revision-bound artifact and evidence records
- [x] Independent evidence acceptance
- [x] SQLite snapshots, optimistic revisions and event trail
- [x] CLI demo and end-to-end tests

## v0.1.1 — Trust boundary hardening

- [x] One canonical contract for runtime, storage, examples and JSON Schema
- [x] Domain validation before persistence and after loading
- [x] Explicit trusted authorizers and grant provenance
- [x] Authorization revocation and audit event
- [x] Fail-closed unsupported authorization conditions
- [x] Trusted verifier registry
- [x] External file re-verification before acceptance
- [x] Executable repairing-to-planning loop
- [x] Python 3.9–3.13 CI compatibility matrix

## v0.2 — Runtime adapter contract

- [ ] Define a runtime-neutral executor protocol
- [ ] Add one production-quality agent runtime adapter
- [ ] Add executor leases and cancellation
- [ ] Capture structured tool-call observations
- [ ] Add resumable execution checkpoints
- [ ] Publish adapter compatibility tests

## v0.3 — More resource gateways

- [ ] Git repository gateway
- [ ] HTTP API gateway with idempotency keys
- [ ] Document gateway
- [ ] Database read gateway
- [ ] Resource conflict and stale-revision checks
- [ ] Rollback contracts for reversible actions

## v0.4 — Distributed control plane

- [ ] Shared database implementation
- [ ] Concurrent worker claims and leases
- [ ] Policy decision audit records
- [ ] Human approval checkpoints
- [ ] Web task and evidence viewer
- [ ] OpenTelemetry traces and operational metrics

## v0.5 — Controlled capability growth

- [ ] Curate accepted traces into sanitized cases
- [ ] Package candidate capabilities
- [ ] Run isolated evaluation and regression gates
- [ ] Canary capability promotion
- [ ] Capability lineage, versioning and rollback

## Non-goals

TaskSeal does not aim to:

- replace model runtimes or workflow engines;
- treat model confidence as acceptance evidence;
- allow executors to expand their own authority;
- enable unsupervised production changes by default;
- promote a capability because it succeeded once.
