import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from statsmodels.tsa.holtwinters import ExponentialSmoothing

project_folder = Path(__file__).resolve().parent.parent

processed_file = (
    project_folder
    / "Processed_Data"
    / "monthly_passenger_data.csv"
)

passenger_table = pd.read_csv(processed_file)

forecast_table = passenger_table[
    [
        "period",
        "domestic_monthly",
        "international_monthly",
        "total_monthly"
    ]
].copy()

forecast_table = (
    forecast_table
    .sort_values("period")
    .reset_index(drop=True)
)

print(forecast_table.head())
print(forecast_table.tail())

general_test_table = forecast_table.copy()

general_test_table["seasonal_naive_forecast"] = (
    general_test_table["total_monthly"]
    .shift(12)
)

general_test_table = general_test_table.dropna(
    subset=["seasonal_naive_forecast"]
).copy()

general_test_table["error"] = (
    general_test_table["total_monthly"]
    - general_test_table["seasonal_naive_forecast"]
)

general_test_table["absolute_error"] = (
    general_test_table["error"].abs()
)

general_test_table["absolute_percentage_error"] = (
    general_test_table["absolute_error"]
    / general_test_table["total_monthly"]
    * 100
)

print(
    general_test_table[
        [
            "period",
            "total_monthly",
            "seasonal_naive_forecast",
            "error",
            "absolute_error",
            "absolute_percentage_error"
        ]
    ]
    .head(10)
    .to_string(index=False)
)

mae = general_test_table["absolute_error"].mean()
mape = general_test_table["absolute_percentage_error"].mean()

print(f"\nGeneral MAE: {mae:,.0f} passengers")
print(f"General MAPE: {mape:.2f}%")

q1_test_table = general_test_table[
    general_test_table["period"]
    .str[-2:]
    .isin(["01", "02", "03"])
].copy()

print(q1_test_table.to_string(index=False))

q1_mae = q1_test_table["absolute_error"].mean()
q1_mape = (q1_test_table["absolute_percentage_error"].mean())

print(f"\nQ1 MAE: {q1_mae:,.0f} passengers")
print(f"Q1 MAPE: {q1_mape:.2f}%")

#Growth-adjusted seasonal naive

year_month_total = passenger_table.pivot(
    index="year",
    columns="month",
    values="total_monthly"
)

print(year_month_total.to_string())

year_month_growth = (
    year_month_total
    .pct_change(axis=0, fill_method=None)
    .mul(100)
    .round(1)
)

print(year_month_growth.to_string())

growth_test_table = passenger_table[
    [
        "period",
        "year",
        "month",
        "total_monthly"
    ]
].copy()

growth_test_table["observed_growth"] = (
    growth_test_table["total_monthly"]
    .pct_change(periods=12, fill_method=None)
    .mul(100)
    .round(1)
)

growth_test_table["expected_growth"] = (
    growth_test_table["observed_growth"]
    .shift(12)
)

growth_test_table["growth_adjusted_forecast"] = (
    growth_test_table["total_monthly"].shift(12)
    * (1 + growth_test_table["expected_growth"] / 100)
)

print(
    growth_test_table
    .to_string(index=False)
)

growth_test_table = (
    growth_test_table
    .dropna(subset=["growth_adjusted_forecast"])
    .copy()
)

growth_test_table["error"] = (
    growth_test_table["total_monthly"]
    - growth_test_table["growth_adjusted_forecast"]
)

growth_test_table["absolute_error"] = (
    growth_test_table["error"].abs()
)

growth_test_table["absolute_percentage_error"] = (
    growth_test_table["absolute_error"]
    / growth_test_table["total_monthly"]
    * 100
)

growth_mae = (
    growth_test_table["absolute_error"].mean()
)

growth_mape = (
    growth_test_table["absolute_percentage_error"].mean()
)

print(
    growth_test_table[
        [
            "period",
            "total_monthly",
            "growth_adjusted_forecast",
            "error",
            "absolute_error",
            "absolute_percentage_error"
        ]
    ]
    .to_string(index=False)
)

print(f"\nGrowth-adjusted MAE: {growth_mae:,.0f} passengers")
print(f"Growth-adjusted MAPE: {growth_mape:.2f}%")

common_periods = growth_test_table["period"]

seasonal_naive_common = general_test_table[
    general_test_table["period"].isin(common_periods)
].copy()

seasonal_naive_common_mae = (
    seasonal_naive_common["absolute_error"].mean()
)

seasonal_naive_common_mape = (
    seasonal_naive_common["absolute_percentage_error"].mean()
)

print(
    f"\nSeasonal naive MAE "
    f"(same period): {seasonal_naive_common_mae:,.0f} passengers"
)

print(
    f"Seasonal naive MAPE "
    f"(same period): {seasonal_naive_common_mape:.2f}%"
)

# Holt-Winters model

train_table = forecast_table[
    forecast_table["period"] <= "2025-12"
].copy()

test_table = forecast_table[
    forecast_table["period"] >= "2026-01"
].copy()

train_series = train_table["total_monthly"]

test_series = test_table["total_monthly"]

holt_winters_model = ExponentialSmoothing(
    train_series,
    trend="add",
    seasonal="add",
    seasonal_periods=12
)

holt_winters_fit = (
    holt_winters_model
    .fit(optimized=True)
)

print(
    "Smoothing level:",
    holt_winters_fit.params["smoothing_level"]
)

print(
    "Smoothing trend:",
    holt_winters_fit.params["smoothing_trend"]
)

print(
    "Smoothing seasonal:",
    holt_winters_fit.params["smoothing_seasonal"]
)

holt_winters_forecast = (
    holt_winters_fit
    .forecast(len(test_series))
)

holt_winters_test_table = test_table.copy()

holt_winters_test_table["holt_winters_forecast"] = (
    holt_winters_forecast.to_numpy()
)

print(
    holt_winters_test_table[
        [
            "period",
            "total_monthly",
            "holt_winters_forecast"
        ]
    ]
    .to_string(index=False)
)

holt_winters_test_table["error"] = (
    holt_winters_test_table["total_monthly"]
    - holt_winters_test_table["holt_winters_forecast"]
)

holt_winters_test_table["absolute_error"] = (
    holt_winters_test_table["error"].abs()
)

holt_winters_test_table["absolute_percentage_error"] = (
    holt_winters_test_table["absolute_error"]
    / holt_winters_test_table["total_monthly"]
    * 100
)

print(
    holt_winters_test_table[
        [
            "period",
            "total_monthly",
            "holt_winters_forecast",
            "error",
            "absolute_error",
            "absolute_percentage_error"
        ]
    ]
    .to_string(index=False)
)

holt_winters_mae = (
    holt_winters_test_table["absolute_error"].mean()
)

holt_winters_mape = (
    holt_winters_test_table["absolute_percentage_error"].mean()
)

print(
    f"\nHolt-Winters MAE: "
    f"{holt_winters_mae:,.0f} passengers"
)

print(
    f"Holt-Winters MAPE: "
    f"{holt_winters_mape:.2f}%"
)

holt_winters_mean_error = (
    holt_winters_test_table["error"].mean()
)

overforecast_count = (
    holt_winters_test_table["error"] < 0
).sum()

underforecast_count = (
    holt_winters_test_table["error"] > 0
).sum()

print(
    f"\nHolt-Winters mean error: "
    f"{holt_winters_mean_error:,.0f} passengers"
)

print(
    f"Overforecast months: {overforecast_count}"
)

print(
    f"Underforecast months: {underforecast_count}"
)

# Compare all models on the same test period

comparison_periods = (
    holt_winters_test_table["period"]
)

seasonal_naive_2026 = general_test_table[
    general_test_table["period"].isin(comparison_periods)
].copy()

growth_adjusted_2026 = growth_test_table[
    growth_test_table["period"].isin(comparison_periods)
].copy()

model_comparison = pd.DataFrame({
    "model": [
        "Seasonal naive",
        "Growth-adjusted seasonal naive",
        "Holt-Winters"
    ],
    "MAE": [
        seasonal_naive_2026["absolute_error"].mean(),
        growth_adjusted_2026["absolute_error"].mean(),
        holt_winters_test_table["absolute_error"].mean()
    ],
    "MAPE": [
        seasonal_naive_2026[
            "absolute_percentage_error"
        ].mean(),

        growth_adjusted_2026[
            "absolute_percentage_error"
        ].mean(),

        holt_winters_test_table[
            "absolute_percentage_error"
        ].mean()
    ],
    "mean_error": [
        seasonal_naive_2026["error"].mean(),
        growth_adjusted_2026["error"].mean(),
        holt_winters_test_table["error"].mean()
    ]
})

model_comparison["MAE"] = (
    model_comparison["MAE"]
    .round(0)
    .astype(int)
)

model_comparison["MAPE"] = (
    model_comparison["MAPE"]
    .round(2)
)

model_comparison["mean_error"] = (
    model_comparison["mean_error"]
    .round(0)
    .astype(int)
)

print(model_comparison.to_string(index=False))

# Select the 2026 Q1 test period

q1_periods_2026 = [
    "2026-01",
    "2026-02",
    "2026-03"
]

seasonal_naive_q1 = seasonal_naive_2026[
    seasonal_naive_2026["period"].isin(q1_periods_2026)
].copy()

growth_adjusted_q1 = growth_adjusted_2026[
    growth_adjusted_2026["period"].isin(q1_periods_2026)
].copy()

holt_winters_q1 = holt_winters_test_table[
    holt_winters_test_table["period"].isin(q1_periods_2026)
].copy()

q1_model_comparison = pd.DataFrame({
    "model": [
        "Seasonal naive",
        "Growth-adjusted seasonal naive",
        "Holt-Winters"
    ],
    "MAE": [
        seasonal_naive_q1["absolute_error"].mean(),
        growth_adjusted_q1["absolute_error"].mean(),
        holt_winters_q1["absolute_error"].mean()
    ],
    "MAPE": [
        seasonal_naive_q1["absolute_percentage_error"].mean(),
        growth_adjusted_q1["absolute_percentage_error"].mean(),
        holt_winters_q1["absolute_percentage_error"].mean()
    ],
    "mean_error": [
        seasonal_naive_q1["error"].mean(),
        growth_adjusted_q1["error"].mean(),
        holt_winters_q1["error"].mean()
    ]
})

q1_model_comparison = q1_model_comparison.round({
    "MAE": 0,
    "MAPE": 2,
    "mean_error": 0
})

print("\n2026 Q1 Model Comparison")
print(q1_model_comparison.to_string(index=False))


# Check Q1 performance of the seasonal naive model by year

q1_history_table = general_test_table[
    general_test_table["period"]
    .str[-2:]
    .isin(["01", "02", "03"])
].copy()

q1_history_table["year"] = (
    q1_history_table["period"]
    .str[:4]
    .astype(int)
)

seasonal_naive_q1_by_year = (
    q1_history_table
    .groupby("year")
    .agg(
        MAE=("absolute_error", "mean"),
        MAPE=("absolute_percentage_error", "mean"),
        mean_error=("error", "mean")
    )
    .round({
        "MAE": 0,
        "MAPE": 2,
        "mean_error": 0
    })
)

print("\nSeasonal Naive Q1 Performance by Year")
print(seasonal_naive_q1_by_year)

# Check Growth-adjusted Q1 performance by year

growth_q1_history_table = growth_test_table[
    growth_test_table["period"]
    .str[-2:]
    .isin(["01", "02", "03"])
    & growth_test_table["growth_adjusted_forecast"].notna()
].copy()

growth_q1_history_table["year"] = (
    growth_q1_history_table["period"]
    .str[:4]
    .astype(int)
)

growth_adjusted_q1_by_year = (
    growth_q1_history_table
    .groupby("year")
    .agg(
        MAE=("absolute_error", "mean"),
        MAPE=("absolute_percentage_error", "mean"),
        mean_error=("error", "mean")
    )
    .round({
        "MAE": 0,
        "MAPE": 2,
        "mean_error": 0
    })
)

print("\nGrowth-adjusted Q1 Performance by Year")
print(growth_adjusted_q1_by_year)

# Holt-Winters backtest for 2025 Q1

holt_2025_train_table = forecast_table[
    forecast_table["period"] <= "2024-12"
].copy()

holt_2025_test_table = forecast_table[
    forecast_table["period"].isin([
        "2025-01",
        "2025-02",
        "2025-03"
    ])
].copy()

holt_2025_train_series = (
    holt_2025_train_table["total_monthly"]
)

holt_2025_test_series = (
    holt_2025_test_table["total_monthly"]
)

print("\nHolt-Winters 2025 Q1 training data:")
print(holt_2025_train_table.tail())

print("\nHolt-Winters 2025 Q1 test data:")
print(holt_2025_test_table)

# Fit Holt-Winters using data available before 2025 Q1

holt_2025_model = ExponentialSmoothing(
    holt_2025_train_series,
    trend="add",
    seasonal="add",
    seasonal_periods=12
)

holt_2025_fit = (
    holt_2025_model
    .fit(optimized=True)
)

holt_2025_forecast = (
    holt_2025_fit
    .forecast(len(holt_2025_test_series))
)

holt_2025_test_table["holt_winters_forecast"] = (
    holt_2025_forecast.to_numpy()
)

print("\nHolt-Winters 2025 Q1 forecasts:")
print(
    holt_2025_test_table[
        [
            "period",
            "total_monthly",
            "holt_winters_forecast"
        ]
    ].to_string(index=False)
)

# Calculate Holt-Winters errors for 2025 Q1

holt_2025_test_table["error"] = (
    holt_2025_test_table["total_monthly"]
    - holt_2025_test_table["holt_winters_forecast"]
)

holt_2025_test_table["absolute_error"] = (
    holt_2025_test_table["error"].abs()
)

holt_2025_test_table["absolute_percentage_error"] = (
    holt_2025_test_table["absolute_error"]
    / holt_2025_test_table["total_monthly"]
    * 100
)

print("\nHolt-Winters 2025 Q1 error analysis:")
print(
    holt_2025_test_table[
        [
            "period",
            "total_monthly",
            "holt_winters_forecast",
            "error",
            "absolute_error",
            "absolute_percentage_error"
        ]
    ].to_string(index=False)
)

holt_2025_mae = (
    holt_2025_test_table["absolute_error"].mean()
)

holt_2025_mape = (
    holt_2025_test_table["absolute_percentage_error"].mean()
)

holt_2025_mean_error = (
    holt_2025_test_table["error"].mean()
)

print(f"\nHolt-Winters 2025 Q1 MAE: {holt_2025_mae:,.0f} passengers")
print(f"Holt-Winters 2025 Q1 MAPE: {holt_2025_mape:.2f}%")
print(
    f"Holt-Winters 2025 Q1 mean error: "
    f"{holt_2025_mean_error:,.0f} passengers"
)

holt_2026_q1 = holt_winters_test_table[
    holt_winters_test_table["period"]
    .str[-2:]
    .isin(["01", "02", "03"])
].copy()

print("\nHolt-Winters 2026 Q1:")
print(
    holt_2026_q1[
        [
            "period",
            "total_monthly",
            "holt_winters_forecast",
            "error",
            "absolute_percentage_error"
        ]
    ].to_string(index=False)
)

# Combine Holt-Winters Q1 results from 2025 and 2026

holt_q1_backtest_table = pd.concat(
    [
        holt_2025_test_table,
        holt_2026_q1
    ],
    ignore_index=True
)

holt_q1_summary = pd.DataFrame({
    "period": ["2025-2026 Q1"],
    "MAE": [
        holt_q1_backtest_table["absolute_error"].mean()
    ],
    "MAPE": [
        holt_q1_backtest_table[
            "absolute_percentage_error"
        ].mean()
    ],
    "mean_error": [
        holt_q1_backtest_table["error"].mean()
    ]
}).round({
    "MAE": 0,
    "MAPE": 2,
    "mean_error": 0
})

print("\nHolt-Winters Combined Q1 Performance")
print(holt_q1_summary.to_string(index=False))

# Compare all models on the common 2025-2026 Q1 period

common_q1_periods = [
    "2025-01",
    "2025-02",
    "2025-03",
    "2026-01",
    "2026-02",
    "2026-03"
]

seasonal_naive_common_q1 = general_test_table[
    general_test_table["period"].isin(common_q1_periods)
].copy()

growth_adjusted_common_q1 = growth_test_table[
    growth_test_table["period"].isin(common_q1_periods)
].copy()

holt_winters_common_q1 = holt_q1_backtest_table.copy()

common_q1_model_comparison = pd.DataFrame({
    "model": [
        "Seasonal naive",
        "Growth-adjusted seasonal naive",
        "Holt-Winters"
    ],
    "MAE": [
        seasonal_naive_common_q1["absolute_error"].mean(),
        growth_adjusted_common_q1["absolute_error"].mean(),
        holt_winters_common_q1["absolute_error"].mean()
    ],
    "MAPE": [
        seasonal_naive_common_q1[
            "absolute_percentage_error"
        ].mean(),
        growth_adjusted_common_q1[
            "absolute_percentage_error"
        ].mean(),
        holt_winters_common_q1[
            "absolute_percentage_error"
        ].mean()
    ],
    "mean_error": [
        seasonal_naive_common_q1["error"].mean(),
        growth_adjusted_common_q1["error"].mean(),
        holt_winters_common_q1["error"].mean()
    ]
}).round({
    "MAE": 0,
    "MAPE": 2,
    "mean_error": 0
})

print("\nCommon 2025-2026 Q1 Model Comparison")
print(common_q1_model_comparison.to_string(index=False))

# Final Holt-Winters forecast for 2027 Q1

final_series = forecast_table["total_monthly"]

final_model = ExponentialSmoothing(
    final_series,
    trend="add",
    seasonal="add",
    seasonal_periods=12
)

final_fit = (
    final_model
    .fit(optimized=True)
)

final_forecast = (
    final_fit
    .forecast(6)
)

future_periods = (
    pd.period_range(
        start="2026-10",
        periods=6,
        freq="M"
    )
    .astype(str)
)

final_forecast_table = pd.DataFrame({
    "period": future_periods,
    "forecast_total_passengers": final_forecast.to_numpy()
})

final_q1_forecast = final_forecast_table[
    final_forecast_table["period"].isin([
        "2027-01",
        "2027-02",
        "2027-03"
    ])
].copy()

final_q1_forecast["forecast_total_passengers"] = (
    final_q1_forecast["forecast_total_passengers"]
    .round(0)
    .astype(int)
)

print("\nFinal Holt-Winters Forecast for 2027 Q1")
print(final_q1_forecast.to_string(index=False))

# Plot historical data and final Holt-Winters forecast

plt.figure(figsize=(14, 6))

plt.plot(
    forecast_table["period"],
    forecast_table["total_monthly"],
    label="Actual monthly passengers"
)

plt.plot(
    final_forecast_table["period"],
    final_forecast_table["forecast_total_passengers"],
    linestyle="--",
    marker="o",
    label="Holt-Winters forecast"
)

plt.axvline(
    "2027-01",
    color="red",
    linestyle=":",
    label="2027 Q1 begins"
)

plt.title("Actual Passenger Traffic and 2027 Q1 Forecast")
plt.xlabel("Period")
plt.ylabel("Passengers")
plt.xticks(rotation=45)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()