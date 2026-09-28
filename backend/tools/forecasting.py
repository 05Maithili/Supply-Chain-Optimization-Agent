"""
Demand Forecasting Tool — XGBoost-based time-series forecasting.
All numerical operations handled here, NOT by the LLM.
"""
import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import Optional
import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Sale, Product
import math

logger = logging.getLogger(__name__)


def _create_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer time-series features for XGBoost."""
    df = df.copy()
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["year"] = df["date"].dt.year
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # Lag features
    for lag in [1, 7, 14, 30]:
        df[f"lag_{lag}"] = df["demand"].shift(lag)

    # Rolling statistics
    for window in [7, 14, 30]:
        df[f"rolling_mean_{window}"] = df["demand"].shift(1).rolling(window).mean()
        df[f"rolling_std_{window}"] = df["demand"].shift(1).rolling(window).std()

    # Expanding mean (overall trend)
    df["expanding_mean"] = df["demand"].shift(1).expanding().mean()

    df = df.dropna()
    return df


async def get_product_sales_df(
    session: AsyncSession,
    product_id: str,
    warehouse_id: Optional[str] = None,
) -> pd.DataFrame:
    """Fetch historical sales and aggregate by date."""
    query = select(
        Sale.sale_date,
        Sale.quantity_sold,
        Sale.warehouse_id,
    ).where(Sale.product_id == product_id)

    if warehouse_id:
        query = query.where(Sale.warehouse_id == warehouse_id)

    result = await session.execute(query)
    rows = result.fetchall()

    if not rows:
        return pd.DataFrame(columns=["date", "demand"])

    df = pd.DataFrame(rows, columns=["date", "demand", "warehouse_id"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.groupby("date")["demand"].sum().reset_index()
    df = df.sort_values("date").reset_index(drop=True)
    return df


def train_and_forecast(
    df: pd.DataFrame,
    horizon: int = 30,
) -> dict:
    """
    Train XGBoost model on historical data and forecast `horizon` days ahead.
    Returns structured forecast results with evaluation metrics.
    """
    from xgboost import XGBRegressor
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    if len(df) < 30:
        # Fallback to simple moving average for insufficient data
        avg = df["demand"].mean() if len(df) > 0 else 0
        std = df["demand"].std() if len(df) > 1 else 0
        future_dates = [
            (df["date"].max() + timedelta(days=i + 1)).strftime("%Y-%m-%d")
            if len(df) > 0
            else (date.today() + timedelta(days=i + 1)).strftime("%Y-%m-%d")
            for i in range(horizon)
        ]
        forecast_values = [max(0, int(avg + np.random.normal(0, std * 0.1))) for _ in range(horizon)]
        return {
            "model": "Moving Average (insufficient data)",
            "historical": df[["date", "demand"]].assign(
                date=lambda x: x["date"].dt.strftime("%Y-%m-%d")
            ).rename(columns={"date": "date", "demand": "actual"}).to_dict("records"),
            "forecast": [{"date": d, "predicted": v, "lower": max(0, v - int(std)), "upper": v + int(std)}
                         for d, v in zip(future_dates, forecast_values)],
            "metrics": {"MAE": None, "RMSE": None, "MAPE": None},
            "total_forecast": sum(forecast_values),
            "avg_daily_forecast": round(avg, 2),
        }

    feat_df = _create_features(df.copy())
    feature_cols = [c for c in feat_df.columns if c not in ["date", "demand"]]

    X = feat_df[feature_cols].values
    y = feat_df["demand"].values

    # Time-series CV for evaluation
    tscv = TimeSeriesSplit(n_splits=3)
    mae_scores, rmse_scores, mape_scores = [], [], []

    model = XGBRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=0,
    )

    for train_idx, val_idx in tscv.split(X):
        if len(train_idx) < 10:
            continue
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        m = XGBRegressor(n_estimators=200, learning_rate=0.05, max_depth=5,
                         random_state=42, verbosity=0)
        m.fit(X_train, y_train)
        preds = m.predict(X_val)
        mae_scores.append(mean_absolute_error(y_val, preds))
        rmse_scores.append(math.sqrt(mean_squared_error(y_val, preds)))
        nonzero = y_val != 0
        if nonzero.any():
            mape_scores.append(
                np.mean(np.abs((y_val[nonzero] - preds[nonzero]) / y_val[nonzero])) * 100
            )

    # Retrain on full data
    model.fit(X, y)

    # Generate future forecast
    forecast_rows = []
    ext_df = df.copy()
    last_date = ext_df["date"].max()

    for i in range(horizon):
        next_date = last_date + timedelta(days=i + 1)
        tmp = ext_df.copy()
        tmp_feat = _create_features(tmp)
        if tmp_feat.empty:
            forecast_rows.append((next_date, max(0, int(df["demand"].mean()))))
            continue
        last_feat = tmp_feat[feature_cols].iloc[-1:].values
        pred = float(model.predict(last_feat)[0])
        pred = max(0, pred)
        forecast_rows.append((next_date, round(pred, 2)))
        # Append prediction to history for next step
        ext_df = pd.concat([
            ext_df,
            pd.DataFrame({"date": [next_date], "demand": [pred]})
        ], ignore_index=True)

    # Confidence interval via std of residuals
    residual_std = float(np.std(y - model.predict(X)))

    historical_data = df[["date", "demand"]].copy()
    historical_data["date"] = historical_data["date"].dt.strftime("%Y-%m-%d")
    historical_data = historical_data.rename(columns={"demand": "actual"})

    forecast_data = [
        {
            "date": str(d.strftime("%Y-%m-%d")),
            "predicted": round(v, 1),
            "lower": max(0, round(v - 1.96 * residual_std, 1)),
            "upper": round(v + 1.96 * residual_std, 1),
        }
        for d, v in forecast_rows
    ]

    total_forecast = sum(f["predicted"] for f in forecast_data)
    avg_daily = total_forecast / horizon if horizon > 0 else 0

    return {
        "model": "XGBoost Gradient Boosting",
        "historical": historical_data.to_dict("records"),
        "forecast": forecast_data,
        "metrics": {
            "MAE": round(float(np.mean(mae_scores)), 2) if mae_scores else None,
            "RMSE": round(float(np.mean(rmse_scores)), 2) if rmse_scores else None,
            "MAPE": round(float(np.mean(mape_scores)), 2) if mape_scores else None,
        },
        "total_forecast": round(total_forecast, 1),
        "avg_daily_forecast": round(avg_daily, 2),
    }


async def forecast_demand(
    session: AsyncSession,
    product_id: str,
    horizon: int = 30,
    warehouse_id: Optional[str] = None,
) -> dict:
    """
    Main forecasting function called by the Demand Agent.
    """
    df = await get_product_sales_df(session, product_id, warehouse_id)
    if df.empty:
        return {
            "error": f"No historical sales data found for product {product_id}",
            "product_id": product_id,
            "horizon": horizon,
        }

    result = train_and_forecast(df, horizon=horizon)
    result["product_id"] = product_id
    result["horizon_days"] = horizon
    result["warehouse_id"] = warehouse_id
    return result
