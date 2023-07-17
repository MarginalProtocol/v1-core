# v1-core

[Marginal v1](./wp/v1.pdf) core smart contracts.

## Installation

The repo uses [ApeWorX](https://github.com/apeworx/ape) for development.

Set up a virtual environment

```sh
python -m venv .venv
source .venv/bin/activate
```

Install requirements and Ape plugins

```sh
pip install -r requirements.txt
ape plugins install .
```

## Tests

Tests without fuzzing, integration

```sh
ape test -s -m "not fuzzing and not integration"
```

Tests with fuzzing but not integration

```sh
ape test -s -m "fuzzing and not integration"
```

Tests for integrations

```sh
ape test -s -m "integration" --network ethereum:mainnet-fork:foundry
```

