# Contributing to TaskSeal

Thank you for helping make agent work more trustworthy.

## Set up

```bash
git clone https://github.com/lexiewenchuan/TaskSeal.git
cd TaskSeal
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Run the checks:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m taskseal demo
check-jsonschema \
  --schemafile spec/work-item.schema.json \
  examples/software-change/work-item.json
```

## Before opening a pull request

1. Search existing issues and discussions.
2. Keep one pull request focused on one observable outcome.
3. Add a focused test for changed behavior.
4. Preserve the core authorization and acceptance invariants.
5. Do not include credentials, customer data, production traces, private
   repositories, or organization-specific information.
6. Distinguish implemented behavior from roadmap proposals.

## Design expectations

- Keep the Work Item as the top-level object.
- Keep core contracts independent of model providers.
- Route real side effects through a resource gateway.
- Bind evidence to resource revisions and acceptance criteria.
- Reject delegation that expands authority.
- Prefer deterministic checks where they are sufficient.
- Keep executors separate from independent acceptance.
- Avoid adding a new abstraction until a real adapter or test needs it.

## Pull request checklist

- [ ] The change has one clear purpose.
- [ ] New behavior has tests.
- [ ] `python -m unittest discover -s tests -v` passes.
- [ ] The CLI example still runs.
- [ ] Runtime Work Item output still validates against the public schema.
- [ ] Documentation matches the implemented behavior.
- [ ] Public files contain no sensitive or organization-specific data.
- [ ] Authorization, side effects, evidence and rollback were considered.

## Reporting issues

Use the issue templates for bugs, use cases, and architectural proposals.
Security issues must follow [SECURITY.md](./SECURITY.md) rather than the public
issue tracker.

By participating, you agree to follow the
[Code of Conduct](./CODE_OF_CONDUCT.md).
