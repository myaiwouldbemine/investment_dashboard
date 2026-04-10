from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from api import app
from src.services.investment_summary_service import query_summary


class InvestmentApiTests(unittest.TestCase):
    @patch('src.services.investment_summary_service.load_snapshot')
    def test_query_summary_returns_stock_summary(self, mock_snapshot) -> None:
        mock_snapshot.return_value = type('Snapshot', (), {
            'bond_df': pd.DataFrame(),
            'stock_df': pd.DataFrame([{'total_cost_jpy': 2000,'market_value_jpy': 2400,'unrealized_pnl_jpy': 400,'unrealized_return': 0.2,'security_name_zh': 'Toyota',}]),
            'fcn_df': pd.DataFrame(),
            'fcn_summary_df': pd.DataFrame(),
            'bond_as_of': None,
            'stock_as_of': '2026-04-08 13:30:00',
            'fcn_as_of': None,
        })()
        reply = query_summary('stocks')
        self.assertEqual(reply['title'], '【股票摘要】')
        self.assertEqual(reply['as_of'], '2026-04-08 13:30:00')
        self.assertNotIn('更新時間', reply['text'])
        self.assertIn('投資金額：2,000 JPY', reply['text'])

    @patch('src.services.investment_summary_service.load_snapshot')
    def test_query_summary_returns_stock_detail(self, mock_snapshot) -> None:
        mock_snapshot.return_value = type('Snapshot', (), {
            'bond_df': pd.DataFrame(),
            'stock_df': pd.DataFrame([
                {'total_cost_jpy': 2000,'market_value_jpy': 2400,'unrealized_pnl_jpy': 400,'unrealized_return': 0.2,'security_name_zh': 'Toyota','ticker': '7203'},
                {'total_cost_jpy': 3000,'market_value_jpy': 3100,'unrealized_pnl_jpy': 100,'unrealized_return': 0.0333,'security_name_zh': 'Sony','ticker': '6758'},
            ]),
            'fcn_df': pd.DataFrame(),
            'fcn_summary_df': pd.DataFrame(),
            'bond_as_of': None,
            'stock_as_of': '2026-04-08 13:30:00',
            'fcn_as_of': None,
        })()
        reply = query_summary('stocks Toyota')
        self.assertEqual(reply['title'], '【股票明細】')
        self.assertIn('查詢條件：Toyota', reply['text'])
        self.assertIn('標的：Toyota', reply['text'])
        self.assertIn('總投入成本：2,000 JPY', reply['text'])
        self.assertNotIn('Sony', reply['text'])

    @patch('src.services.investment_summary_service.load_snapshot')
    def test_query_summary_returns_bond_detail(self, mock_snapshot) -> None:
        mock_snapshot.return_value = type('Snapshot', (), {
            'bond_df': pd.DataFrame([
                {'face_amount': 1000,'ytm': 0.05,'duration_years': 3.0,'counterparty': 'Morgan Stanley','currency': 'USD'},
                {'face_amount': 500,'ytm': 0.04,'duration_years': 2.0,'counterparty': 'Bank A','currency': 'USD'},
            ]),
            'stock_df': pd.DataFrame(),
            'fcn_df': pd.DataFrame(),
            'fcn_summary_df': pd.DataFrame(),
            'bond_as_of': '2026-04-08 13:31:00',
            'stock_as_of': None,
            'fcn_as_of': None,
        })()
        reply = query_summary('bonds Morgan Stanley')
        self.assertEqual(reply['title'], '【債券明細】')
        self.assertIn('查詢條件：Morgan Stanley', reply['text'])
        self.assertIn('投資金額：1,000', reply['text'])
        self.assertIn('主要交易對象：Morgan Stanley', reply['text'])
        self.assertNotIn('Bank A', reply['text'])

    @patch('src.services.investment_summary_service.load_snapshot')
    def test_query_summary_returns_fcn_summary(self, mock_snapshot) -> None:
        mock_snapshot.return_value = type('Snapshot', (), {
            'bond_df': pd.DataFrame(),
            'stock_df': pd.DataFrame(),
            'fcn_df': pd.DataFrame([
                {'company_code': 'WTC', 'underlying': 'COMBO', 'investment_amount_jpy': 1000, 'coupon_income_jpy': 100, 'status_group': '未到期'},
                {'company_code': 'HSB', 'underlying': '700 JP', 'investment_amount_jpy': 500, 'coupon_income_jpy': 50, 'status_group': '已到期'},
            ]),
            'fcn_summary_df': pd.DataFrame([{'total_investment_jpy': 1500, 'total_coupon_jpy': 150, 'outstanding_jpy': 1000}]),
            'bond_as_of': None,
            'stock_as_of': None,
            'fcn_as_of': '2026-04-09 10:00:00',
        })()
        reply = query_summary('fcn')
        self.assertEqual(reply['title'], '【FCN 摘要】')
        self.assertIn('總投資額：1,500 JPY', reply['text'])
        self.assertIn('未到期利息：100 JPY', reply['text'])

    @patch('src.services.investment_summary_service.load_snapshot')
    def test_api_bonds_endpoint_returns_payload(self, mock_snapshot) -> None:
        mock_snapshot.return_value = type('Snapshot', (), {
            'bond_df': pd.DataFrame([{'face_amount': 1000,'ytm': 0.05,'duration_years': 3.0,'counterparty': 'Bank A','currency': 'USD',}]),
            'stock_df': pd.DataFrame(),
            'fcn_df': pd.DataFrame(),
            'fcn_summary_df': pd.DataFrame(),
            'bond_as_of': '2026-04-08 13:31:00',
            'stock_as_of': None,
            'fcn_as_of': None,
        })()
        client = TestClient(app)
        response = client.get('/api/v1/investments/bonds')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['title'], '【債券摘要】')
        self.assertEqual(body['as_of'], '2026-04-08 13:31:00')
        self.assertNotIn('更新時間', body['text'])
        self.assertIn('投資金額：1,000', body['text'])


if __name__ == '__main__':
    unittest.main()
