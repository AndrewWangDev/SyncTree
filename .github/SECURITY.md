# Security Policy

SyncTree takes software security seriously. As a Git graphical client managing local repositories and code assets, we are committed to maintaining a robust, secure, and transparent codebase for our users.

## Supported Versions

We provide active security support, vulnerability triage, and patches exclusively for the following versions:

| Version | Supported          | Status                      |
| ------- | ------------------ | --------------------------- |
| 2.0.0+  | :white_check_mark: | Currently Supported (Active)|
| < 2.0.0 | :x:                | End of Life (Unsupported)   |

> [!NOTE]
> Security patches are backported only to release versions **2.0.0 and above**. If you are running an earlier beta or 1.x version, please upgrade immediately.

## Reporting a Vulnerability

**Please DO NOT report security vulnerabilities via public GitHub Issues, Discussions, or public pull requests.**

If you discover a security vulnerability in SyncTree (e.g., Command Injection, Path Traversal, Insecure Executable Handling, Thread/Lock Racing):

1. **Preferred Method (GitHub Security Advisory)**:
   - Navigate to the [Security Tab](https://github.com/AndrewWangDev/SyncTree/security) of the SyncTree repository.
   - Click on **"Report a vulnerability"** to submit a private draft security advisory directly to the maintainers.
2. **Alternative Method (Direct Contact)**:
   - Email details directly to **`me@andrewwangdev.com`**.
   - Please include a detailed description, affected versions, step-by-step reproduction steps, and a Proof of Concept (PoC) if applicable.

## Vulnerability Handling

We appreciate the responsible disclosure of security issues. All valid vulnerability reports will be reviewed, verified, and remediated **as promptly as possible**. Once a patch is confirmed and deployed, we will publish a corresponding security advisory acknowledging and crediting the reporter.
