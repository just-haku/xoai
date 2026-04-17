# XOAI Local Development

## Python Environment

Use the repo-root virtualenv for local Python work:

```bash
./run_xoai.sh venv
source .venv/bin/activate
```

This installs the backend in editable mode from `./backend`.

## Local Backend Commands

Start the backend without Docker:

```bash
./run_xoai.sh backend
```

Run project scripts through the same environment:

```bash
./run_xoai.sh drop-db
./run_xoai.sh add admin <user> <pwd> <name>
```

## Docker Stack

Bring up the full app stack:

```bash
./run_xoai.sh up
```
