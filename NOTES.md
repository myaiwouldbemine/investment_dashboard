# Notes

A short overview of how the dashboard fits into this learning project.

## Overview

The dashboard exposes a FastAPI layer and runs under `systemd` in WSL.

## What It Shows

- Data staging from a workbook.
- Dashboard mart construction.
- FastAPI service design.
- Structured investment endpoints.
- Simple operational runbooks.

## Endpoints

```text
/health
/api/v1/investments/summary?query=overview
/api/v1/investments/bonds
/api/v1/investments/stocks
/api/v1/investments/deposits
```