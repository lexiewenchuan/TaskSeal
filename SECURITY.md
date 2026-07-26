# Security Policy

TaskSeal is currently a design preview. Do not use it as the sole authorization
or safety boundary for production systems.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability.

Use GitHub's **Report a vulnerability** / private security advisory flow for
this repository. If that option is unavailable, contact the repository owner
privately through the maintainer's GitHub profile.

Include:

- the affected contract, document, or future runtime component;
- the authorization or trust boundary involved;
- a minimal reproduction or abuse scenario;
- expected impact;
- any suggested mitigation.

Do not include real credentials, customer data, production traces, or private
repository contents.

## Security model

The project treats the following as security boundaries:

- authority cannot expand through delegation;
- side effects require policy checks at the resource gateway;
- evidence must bind to the relevant resource revision;
- task completion requires acceptance, not executor self-reporting;
- capability promotion must be isolated, evaluated, reversible, and explicit.

These are design invariants, not a claim that the current preview provides a
production security implementation.
