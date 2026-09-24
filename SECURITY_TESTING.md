# Security Testing

This file records reproducible security testing for Guardian Core. Do not publish detection or false-positive percentages until they are measured on a documented corpus.

## Required measurements

| Test set | Samples | Detected | Missed | False positives | Notes |
|---|---:|---:|---:|---:|---|
| Known suspicious test corpus | TBD | TBD | TBD | N/A | Add corpus version and date |
| Clean Windows files | TBD | N/A | N/A | TBD | Include common executables and libraries |
| Regression fixtures | TBD | TBD | TBD | TBD | Record YARA rules and scanner version |

## Scope

Guardian Core performs local static triage: SHA-256, file metadata, heuristic signals, and YARA matches. It does not claim to stop kernel rootkits, zero-day exploits, or every malicious file. A clean result is not proof that a file is safe.

## Reproduction

1. Record the commit SHA and scanner version.
2. Record the sample corpus hash and license/provenance.
3. Run the scanner against every sample.
4. Review results manually and record false positives.
5. Publish only aggregate results; never include malware binaries in this repository.
