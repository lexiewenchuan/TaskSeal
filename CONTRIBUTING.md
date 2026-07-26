# Contributing to TaskSeal

Thank you for helping make agent work more trustworthy.

TaskSeal is currently design-first. The most valuable contributions are small,
testable improvements to contracts, invariants, examples, evaluations, and the
reference architecture.

## Before opening a pull request

1. Search existing issues and discussions.
2. For a new subsystem or changed invariant, open a **Design proposal** first.
3. Keep one pull request focused on one observable outcome.
4. Do not include private repositories, production data, credentials, customer
   information, or unsanitized agent traces.
5. State what is designed, specified, prototyped, and verified. Do not describe
   planned behavior as implemented behavior.

## Good first contributions

- Add a sanitized Work Item example for a new domain.
- Find ambiguity in the JSON Schema or design vocabulary.
- Propose an acceptance or evidence pattern.
- Improve a diagram or explanation without adding new concepts.
- Add an evaluation case for a failure mode.
- Review the architecture from a security or operations perspective.

## Design proposal checklist

A proposal should explain:

- the real task or failure mode;
- why an existing TaskSeal concept does not cover it;
- the smallest contract or invariant change that would;
- authorization and side-effect implications;
- what evidence would prove the design works;
- compatibility and rollback considerations.

## Pull request checklist

- [ ] The change has one clear purpose.
- [ ] Public examples contain no sensitive or organization-specific data.
- [ ] Contracts and examples remain consistent.
- [ ] Documentation links resolve.
- [ ] New claims are supported by a check, example, or clearly marked rationale.
- [ ] The README and roadmap remain honest about implementation status.

## Style

- Prefer plain language before specialized terms.
- Keep the Work Item as the top-level object.
- Separate execution output, artifacts, evidence, and accepted facts.
- Use deterministic checks where they are sufficient.
- Avoid provider-specific fields in core contracts.
- Put domain-specific extensions under a namespaced extension object.

## Community

By participating, you agree to follow the
[Code of Conduct](./CODE_OF_CONDUCT.md). Security issues should follow
[SECURITY.md](./SECURITY.md), not the public issue tracker.
