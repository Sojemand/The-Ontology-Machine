# Release Assets Drop Zone

This folder is a local drop zone for large release assets that are intentionally
not tracked in Git.

For developer hydration, download the runtime bundle release asset here:

```text
OntologyMachine-RuntimeBundle-v1.0.0.zip
```

Then run from the repository root:

```powershell
powershell.exe -ExecutionPolicy Bypass -File tools\hydrate.ps1
```

The ZIP files in this folder stay ignored by Git.
