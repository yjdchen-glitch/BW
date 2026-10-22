"""Transparent per-product demand forecasts for the BakeWise MVP."""
from __future__ import annotations

from datetime import date
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FEATURES = ["weekday", "holiday", "temperature_f", "rain", "day_index"]


def validate_sales(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "product", "produced", "leftover", "temperature_f", "rain"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    df = frame.copy()
    df["date"] = pd.to_datetime(df["date"], errors="raise").dt.normalize()
    df["product"] = df["product"].astype(str).str.strip()
    if df["product"].eq("").any():
        raise ValueError("Product names cannot be empty.")
    for field in ("produced", "leftover", "temperature_f", "rain"):
        df[field] = pd.to_numeric(df[field], errors="raise")
    for field in ("produced", "leftover"):
        if (df[field] < 0).any() or (df[field] % 1 != 0).any():
            raise ValueError(f"{field} must be a nonnegative whole number.")
    if (df.leftover > df.produced).any():
        raise ValueError("Leftover cannot exceed produced.")
    if (~df.rain.isin([0, 1])).any():
        raise ValueError("Rain must be 0 or 1.")
    if df.duplicated(["date", "product"]).any():
        raise ValueError("Only one record per product per day is allowed.")
    df["sold"] = df["produced"] - df["leftover"]
    if "sold_out_early" not in df:
        df["sold_out_early"] = False
    df["sold_out_early"] = df["sold_out_early"].fillna(False).astype(bool)
    return df.sort_values(["product", "date"]).reset_index(drop=True)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    from pandas.tseries.holiday import USFederalHolidayCalendar
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    start = df.date.min() - pd.Timedelta(days=10)
    end = df.date.max() + pd.Timedelta(days=10)
    us_holidays = set(USFederalHolidayCalendar().holidays(start=start, end=end).date)
    df["weekday"] = df.date.dt.dayofweek.astype(str)
    df["holiday"] = df.date.dt.date.map(lambda d: int(d in us_holidays))
    df["day_index"] = (df.date - pd.Timestamp("2020-01-01")).dt.days.astype(float)
    return df


def _model() -> Pipeline:
    processor = ColumnTransformer([
        ("weekday", OneHotEncoder(handle_unknown="ignore"), ["weekday"]),
        ("other", StandardScaler(), ["holiday", "temperature_f", "rain", "day_index"]),
    ])
    return Pipeline([("features", processor), ("regression", Ridge(alpha=25.0))])


def _forecast_one(history: pd.DataFrame, future: pd.DataFrame) -> tuple[float, str, float | None]:
    # Early stockouts censor actual demand; exclude them when there are enough uncensored records.
    eligible = history.loc[~history.sold_out_early].copy()
    if len(eligible) < 21:
        eligible = history.copy()
    if eligible.empty:
        return 0.0, "No history", None
    if len(eligible) < 28 or eligible.date.nunique() < 28:
        same_day = eligible[eligible.date.dt.dayofweek == future.date.dt.dayofweek.iloc[0]]
        sample = same_day if len(same_day) >= 3 else eligible
        return float(sample.sold.tail(8).mean()), "Recent weekday average", None

    data = add_features(eligible)
    target = add_features(future)
    # Time ordered test split: the final 20% of observations are held out.
    split = max(21, int(len(data) * .8))
    split = min(split, len(data) - 1)
    train, test = data.iloc[:split], data.iloc[split:]
    probe = _model().fit(train[FEATURES], train.sold)
    mae = float(np.mean(np.abs(probe.predict(test[FEATURES]) - test.sold)))
    fitted = _model().fit(data[FEATURES], data.sold)
    prediction = float(fitted.predict(target[FEATURES])[0])
    return max(0.0, prediction), "Ridge regression", mae


def make_forecast(sales: pd.DataFrame, target_date: date, temperature_f: float,
                  rain: bool, strategy: str = "Balanced") -> pd.DataFrame:
    if strategy not in ("Lean", "Balanced", "Safe Buffer"):
        raise ValueError("Unknown strategy")
    history = validate_sales(sales)
    cutoff = pd.Timestamp(target_date)
    history = history.loc[history.date < cutoff]
    if history.empty:
        raise ValueError("No records before the forecast date.")
    adjustment = {"Lean": -0.5, "Balanced": 0.0, "Safe Buffer": 0.75}[strategy]
    output = []
    for product, group in history.groupby("product", sort=True):
        future = pd.DataFrame([{
            "date": pd.Timestamp(target_date), "temperature_f": temperature_f,
            "rain": int(rain)
        }])
        estimate, method, mae = _forecast_one(group.sort_values("date"), future)
        # Risk adjustments are illustrative, scaled by out-of-sample MAE where available.
        # They are NOT proven cost-optimal quantities or statistical confidence bounds.
        uncertainty = mae if mae is not None else max(1.0, estimate * .12)
        qty = max(0, int(np.ceil(estimate + adjustment * uncertainty)))
        output.append({"Product": product, "Expected sales": round(estimate, 1),
                       "Recommended": qty, "Method": method,
                       "Holdout MAE": round(mae, 1) if mae is not None else np.nan})
    return pd.DataFrame(output)
