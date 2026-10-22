import unittest
from pathlib import Path
import pandas as pd
from forecast import validate_sales, make_forecast

class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(Path(__file__).resolve().parents[1] / "data" / "historical_sales.csv")

    def test_sales_math(self):
        df = validate_sales(self.df)
        self.assertTrue((df.sold == df.produced - df.leftover).all())

    def test_invalid_leftover(self):
        df = self.df.copy()
        df.loc[0, "leftover"] = df.loc[0, "produced"] + 1
        with self.assertRaises(ValueError):
            validate_sales(df)

    def test_forecast_all_products(self):
        forecast = make_forecast(self.df, pd.Timestamp(self.df.date.max()).date() + pd.Timedelta(days=1), 70, False)
        self.assertEqual(len(forecast), 10)
        self.assertTrue((forecast["Recommended"] >= 0).all())

    def test_strategy_order(self):
        d = pd.Timestamp(self.df.date.max()).date() + pd.Timedelta(days=1)
        lean = make_forecast(self.df, d, 70, False, "Lean")
        bal = make_forecast(self.df, d, 70, False, "Balanced")
        safe = make_forecast(self.df, d, 70, False, "Safe Buffer")
        self.assertTrue((lean["Recommended"] <= bal["Recommended"]).all())
        self.assertTrue((bal["Recommended"] <= safe["Recommended"]).all())

if __name__ == "__main__":
    unittest.main()
