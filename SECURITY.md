# Security policy

## Reporting a vulnerability

Please do not open a public issue for security reports. Email the maintainer
via the address on the [GitHub profile](https://github.com/G10hdz), or use
GitHub private vulnerability reporting if enabled on this repository.

Include: affected version or commit, reproduction steps, and impact. Expect
an acknowledgement within a week; fixes land on `main` before disclosure.

## Scope notes

- The public site (https://rosetta-coda.vercel.app) is static: immutable
  JSON artifacts and HTML/CSS/JS. There is no server-side endpoint, no
  authentication surface, and no live model calls.
- The FastAPI surface (`api/`) is intended for local use only and is not
  part of the deployment. Do not expose it publicly; it has no auth.
- The LLM stage reads provider keys from environment variables. Keys must
  never appear in artifacts, logs, committed files, or frontend code —
  report any leak of this kind immediately as a vulnerability.
