# Package Root

This package is the future product source for the Semantic Control Kernel.

The build plan intentionally separates implementation into stable layers:

- `surface`
- `types`
- `validation`
- `policy`
- `domain`
- `workflow`
- `repository`
- `adapter`
- `debug`

Do not add broad catch-all modules. Each new file should have one dominant
responsibility and should be introduced by the matching build phase.

