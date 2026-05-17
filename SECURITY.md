# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please do **not** open a public issue.

Send a private report via [GitHub Security Advisories](../../security/advisories/new).

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

You will receive a response within 72 hours.

## Credential Rotation Schedule

| Credential | Rotation |
|---|---|
| WordPress Application Password | Every 90 days |
| Gemini API Key | Every 180 days |
| Turso Auth Token | Every 180 days |

## Compromised Credential Procedure

1. Revoke the credential immediately on the provider's dashboard
2. Generate a new credential
3. Update the GitHub Secret
4. Audit recent logs for unauthorized usage