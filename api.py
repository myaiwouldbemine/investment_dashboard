from __future__ import annotations

from fastapi import FastAPI, Query

from src.services.investment_summary_service import (
    build_bond_charts_payload,
    build_bond_summary,
    build_fcn_charts_payload,
    build_fcn_summary,
    build_overview_summary,
    build_stock_charts_payload,
    build_stock_summary,
    query_summary,
)

app = FastAPI(title='Investment Dashboard API', version='1.0.0')


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/v1/investments/summary')
def investment_summary(query: str = Query(default='')) -> dict[str, object]:
    return query_summary(query)


@app.get('/api/v1/investments/bonds')
def investment_bonds() -> dict[str, object]:
    return build_bond_summary()


@app.get('/api/v1/investments/stocks')
def investment_stocks() -> dict[str, object]:
    return build_stock_summary()


@app.get('/api/v1/investments/fcn')
def investment_fcn() -> dict[str, object]:
    return build_fcn_summary()


@app.get('/api/v1/investments/overview')
def investment_overview() -> dict[str, object]:
    return build_overview_summary()


@app.get('/api/v1/investments/charts/bonds')
def investment_bond_charts() -> dict[str, object]:
    return build_bond_charts_payload()


@app.get('/api/v1/investments/charts/stocks')
def investment_stock_charts() -> dict[str, object]:
    return build_stock_charts_payload()


@app.get('/api/v1/investments/charts/fcn')
def investment_fcn_charts() -> dict[str, object]:
    return build_fcn_charts_payload()
