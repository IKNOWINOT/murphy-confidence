# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes    |

## Reporting a vulnerability

**Please do not file a public GitHub issue for security vulnerabilities.**

Email **contact@inoni.com** with the subject line:
`[SECURITY] murphy-confidence — <brief description>`

Include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive an acknowledgement within **48 hours** and a resolution
timeline within **7 business days**.

## Disclosure policy

We follow responsible disclosure:

1. You report privately to contact@inoni.com
2. We triage and confirm the issue
3. We develop and test a fix
4. We release a patched version
5. We publish a GitHub Security Advisory
6. You receive credit in the advisory (if desired)

## Scope

This policy covers the `murphy-confidence` Python package published on PyPI
and the source code at https://github.com/IKNOWINOT/murphy-confidence.

## Out of scope

- Vulnerabilities in downstream applications that use `murphy-confidence`
- Denial-of-service via intentionally malformed inputs (the library has
  no network surface; callers control all inputs)
