import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# =========================
# 1. Project paths
# =========================

project_folder = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

processed_file = (
    project_folder
    / "Processed_Data"
    / "monthly_passenger_data.csv"
)

outputs_folder = project_folder / "Outputs"
figures_folder = outputs_folder / "Figures"
tables_folder = outputs_folder / "Tables"

figures_folder.mkdir(
    parents=True,
    exist_ok=True
)

tables_folder.mkdir(
    parents=True,
    exist_ok=True
)

# =========================
# 2. Load processed data
# =========================

if not processed_file.exists():
    raise FileNotFoundError(
        f"Processed data file was not found:\n"
        f"{processed_file}"
    )

passenger_table = pd.read_csv(
    processed_file
)

# =========================
# 3. Prepare forecast table
# =========================

series_columns = {
    "Domestic": "domestic_monthly",
    "International": "international_monthly",
    "Total": "total_monthly"
}

value_columns = list(
    series_columns.values()
)

required_columns = [
    "period",
    *value_columns
]

missing_columns = [
    column
    for column in required_columns
    if column not in passenger_table.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: "
        f"{missing_columns}"
    )

forecast_table = passenger_table[
    required_columns
].copy()

forecast_table["period"] = (
    forecast_table["period"]
    .astype(str)
)

forecast_table = (
    forecast_table
    .sort_values("period")
    .reset_index(drop=True)
)

# =========================
# 4. Data validation checks
# =========================

parsed_periods = pd.to_datetime(
    forecast_table["period"],
    format="%Y-%m",
    errors="coerce"
)

if parsed_periods.isna().any():
    invalid_periods = (
        forecast_table
        .loc[
            parsed_periods.isna(),
            "period"
        ]
        .tolist()
    )

    raise ValueError(
        "Invalid period values found: "
        f"{invalid_periods}"
    )

if forecast_table["period"].duplicated().any():
    duplicate_periods = (
        forecast_table
        .loc[
            forecast_table["period"].duplicated(),
            "period"
        ]
        .tolist()
    )

    raise ValueError(
        "Duplicate period values found: "
        f"{duplicate_periods}"
    )

missing_value_rows = forecast_table.loc[
    forecast_table[value_columns]
    .isna()
    .any(axis=1),
    required_columns
]

if not missing_value_rows.empty:
    raise ValueError(
        "Missing passenger values found:\n"
        f"{missing_value_rows.to_string(index=False)}"
    )

negative_value_rows = forecast_table.loc[
    (forecast_table[value_columns] < 0)
    .any(axis=1),
    required_columns
]

if not negative_value_rows.empty:
    raise ValueError(
        "Negative passenger values found:\n"
        f"{negative_value_rows.to_string(index=False)}"
    )

total_difference = (
    forecast_table["domestic_monthly"]
    + forecast_table["international_monthly"]
    - forecast_table["total_monthly"]
)

inconsistent_total_rows = forecast_table.loc[
    total_difference.abs() > 0.01,
    required_columns
]

if not inconsistent_total_rows.empty:
    raise ValueError(
        "Domestic + international does not equal total:\n"
        f"{inconsistent_total_rows.to_string(index=False)}"
    )

expected_periods = (
    pd.period_range(
        start=parsed_periods.min().to_period("M"),
        end=parsed_periods.max().to_period("M"),
        freq="M"
    )
    .astype(str)
    .tolist()
)

actual_periods = (
    forecast_table["period"]
    .tolist()
)

if actual_periods != expected_periods:
    raise ValueError(
        "There is a missing or incorrectly ordered month "
        "in the period sequence."
    )

print(
    "Forecast input validation completed successfully."
)

print(
    f"Number of periods: "
    f"{len(forecast_table)}"
)

print(
    f"First period: "
    f"{forecast_table['period'].iloc[0]}"
)

print(
    f"Last period: "
    f"{forecast_table['period'].iloc[-1]}"
)

# =========================
# 5. Helper functions
# =========================

def add_error_columns(
    evaluation_table,
    value_column,
    forecast_column
):
    evaluation_table = (
        evaluation_table
        .copy()
    )

    if value_column not in evaluation_table.columns:
        raise ValueError(
            f"Value column not found: "
            f"{value_column}"
        )

    if forecast_column not in evaluation_table.columns:
        raise ValueError(
            f"Forecast column not found: "
            f"{forecast_column}"
        )

    if (
        evaluation_table[value_column]
        <= 0
    ).any():
        raise ValueError(
            "MAPE cannot be calculated because "
            "actual passenger values must be positive."
        )

    evaluation_table["error"] = (
        evaluation_table[value_column]
        - evaluation_table[forecast_column]
    )

    evaluation_table["absolute_error"] = (
        evaluation_table["error"]
        .abs()
    )

    evaluation_table[
        "absolute_percentage_error"
    ] = (
        evaluation_table["absolute_error"]
        / evaluation_table[value_column]
        * 100
    )

    return evaluation_table

def save_table(
    table,
    file_name
):
    output_path = (
        tables_folder
        / file_name
    )

    table.to_csv(
        output_path,
        index=False
    )

    return output_path

# =========================
# 6. Create Seasonal Naive tables
# =========================

seasonal_naive_tables = {}

for series_name, value_column in (
    series_columns.items()
):

    seasonal_table = forecast_table[
        [
            "period",
            value_column
        ]
    ].copy()

    seasonal_table[
        "seasonal_naive_forecast"
    ] = (
        seasonal_table[value_column]
        .shift(12)
    )

    seasonal_table = (
        seasonal_table
        .dropna(
            subset=[
                "seasonal_naive_forecast"
            ]
        )
        .copy()
    )

    seasonal_naive_tables[
        series_name
    ] = seasonal_table

# =========================
# 7. Calculate Seasonal Naive errors
# =========================

for series_name, seasonal_table in (
    seasonal_naive_tables.items()
):

    value_column = (
        series_columns[series_name]
    )

    seasonal_naive_tables[
        series_name
    ] = add_error_columns(
        seasonal_table,
        value_column,
        "seasonal_naive_forecast"
    )

# =========================
# 8. Seasonal Naive performance
# =========================

seasonal_naive_summary_rows = []

for series_name, test_table in (
    seasonal_naive_tables.items()
):

    mae = (
        test_table["absolute_error"]
        .mean()
    )

    mape = (
        test_table[
            "absolute_percentage_error"
        ]
        .mean()
    )

    mean_error = (
        test_table["error"]
        .mean()
    )

    seasonal_naive_summary_rows.append(
        {
            "model": "Seasonal Naive",
            "series": series_name,
            "MAE": mae,
            "MAPE": mape,
            "mean_error": mean_error
        }
    )

seasonal_naive_summary = (
    pd.DataFrame(
        seasonal_naive_summary_rows
    )
)

seasonal_naive_summary = (
    seasonal_naive_summary
    .round(
        {
            "MAE": 0,
            "MAPE": 2,
            "mean_error": 0
        }
    )
)

print(
    "\nSeasonal Naive Performance by Series"
)

print(
    seasonal_naive_summary
    .to_string(index=False)
)

save_table(
    seasonal_naive_summary,
    "seasonal_naive_summary.csv"
)

# =========================
# 9. Create Growth-adjusted tables
# =========================

growth_adjusted_tables = {}

for series_name, value_column in (
    series_columns.items()
):

    growth_table = passenger_table[
        [
            "period",
            "year",
            "month",
            value_column
        ]
    ].copy()

    growth_table["observed_growth"] = (
        growth_table[value_column]
        .pct_change(
            periods=12,
            fill_method=None
        )
        .mul(100)
    )

    growth_table["expected_growth"] = (
        growth_table["observed_growth"]
        .shift(12)
    )

    growth_table[
        "growth_adjusted_forecast"
    ] = (
        growth_table[value_column]
        .shift(12)
        * (
            1
            + growth_table["expected_growth"]
            / 100
        )
    )

    growth_table = (
        growth_table
        .dropna(
            subset=[
                "growth_adjusted_forecast"
            ]
        )
        .copy()
    )

    growth_adjusted_tables[
        series_name
    ] = growth_table

# =========================
# 10. Calculate Growth-adjusted errors
# =========================

for series_name, growth_table in (
    growth_adjusted_tables.items()
):

    value_column = (
        series_columns[series_name]
    )

    growth_adjusted_tables[
        series_name
    ] = add_error_columns(
        growth_table,
        value_column,
        "growth_adjusted_forecast"
    )

# =========================
# 11. Growth-adjusted performance
# =========================

growth_adjusted_summary_rows = []

for series_name, growth_table in (
    growth_adjusted_tables.items()
):

    mae = (
        growth_table["absolute_error"]
        .mean()
    )

    mape = (
        growth_table[
            "absolute_percentage_error"
        ]
        .mean()
    )

    mean_error = (
        growth_table["error"]
        .mean()
    )

    growth_adjusted_summary_rows.append(
        {
            "model": "Growth-adjusted",
            "series": series_name,
            "MAE": mae,
            "MAPE": mape,
            "mean_error": mean_error
        }
    )

growth_adjusted_summary = (
    pd.DataFrame(
        growth_adjusted_summary_rows
    )
)

growth_adjusted_summary = (
    growth_adjusted_summary
    .round(
        {
            "MAE": 0,
            "MAPE": 2,
            "mean_error": 0
        }
    )
)

print(
    "\nGrowth-adjusted Performance by Series"
)

print(
    growth_adjusted_summary
    .to_string(index=False)
)

save_table(
    growth_adjusted_summary,
    "growth_adjusted_summary.csv"
)

# =========================
# 12. Holt-Winters model
#     evaluation for 2025 and 2026
# =========================

holt_winters_tables = {
    series_name: []
    for series_name in series_columns
}

for target_year in [2025, 2026]:

    train_end = f"{target_year - 1}-12"

    test_start = f"{target_year}-01"
    test_end = f"{target_year}-12"

    for series_name, value_column in (
        series_columns.items()
    ):

        train_series = forecast_table.loc[
            forecast_table["period"] <= train_end,
            value_column
        ]

        test_table = (
            forecast_table[
                forecast_table["period"].between(
                    test_start,
                    test_end
                )
            ][
                [
                    "period",
                    value_column
                ]
            ]
            .copy()
        )

        if train_series.empty:
            raise ValueError(
                f"Training data is empty for "
                f"{series_name} and {target_year}."
            )

        if test_table.empty:
            raise ValueError(
                f"Test data is empty for "
                f"{series_name} and {target_year}."
            )

        holt_winters_model = (
            ExponentialSmoothing(
                train_series,
                trend="add",
                seasonal="add",
                seasonal_periods=12
            )
        )

        holt_winters_fit = (
            holt_winters_model
            .fit(optimized=True)
        )

        holt_winters_forecast = (
            holt_winters_fit
            .forecast(len(test_table))
        )

        if len(holt_winters_forecast) != len(
            test_table
        ):
            raise ValueError(
                "Forecast length does not match "
                "test table length."
            )

        test_table[
            "holt_winters_forecast"
        ] = (
            holt_winters_forecast
            .to_numpy()
        )

        holt_winters_tables[
            series_name
        ].append(test_table)

# =========================
# 13. Combine Holt-Winters tables
# =========================

combined_holt_winters_tables = {}

for series_name, table_list in (
    holt_winters_tables.items()
):

    combined_table = (
        pd.concat(
            table_list,
            ignore_index=True
        )
        .sort_values("period")
        .reset_index(drop=True)
    )

    combined_holt_winters_tables[
        series_name
    ] = combined_table

holt_winters_tables = (
    combined_holt_winters_tables
)

# =========================
# 14. Calculate Holt-Winters errors
# =========================

for series_name, holt_table in (
    holt_winters_tables.items()
):

    value_column = (
        series_columns[series_name]
    )

    holt_winters_tables[
        series_name
    ] = add_error_columns(
        holt_table,
        value_column,
        "holt_winters_forecast"
    )


# =========================
# 15. Holt-Winters performance
# =========================

holt_winters_summary_rows = []

for series_name, holt_table in (
    holt_winters_tables.items()
):

    mae = (
        holt_table["absolute_error"]
        .mean()
    )

    mape = (
        holt_table[
            "absolute_percentage_error"
        ]
        .mean()
    )

    mean_error = (
        holt_table["error"]
        .mean()
    )

    holt_winters_summary_rows.append(
        {
            "model": "Holt-Winters",
            "series": series_name,
            "MAE": mae,
            "MAPE": mape,
            "mean_error": mean_error
        }
    )

holt_winters_summary = (
    pd.DataFrame(
        holt_winters_summary_rows
    )
)

holt_winters_summary = (
    holt_winters_summary
    .round(
        {
            "MAE": 0,
            "MAPE": 2,
            "mean_error": 0
        }
    )
)

print(
    "\nHolt-Winters Performance by Series"
)

print(
    holt_winters_summary
    .to_string(index=False)
)

save_table(
    holt_winters_summary,
    "holt_winters_summary.csv"
)

# =========================
# 16. Common-period comparison
# =========================

common_periods = (
    forecast_table.loc[
        forecast_table["period"].between(
            "2025-01",
            "2026-09"
        ),
        "period"
    ]
)

comparison_models = {
    "Seasonal Naive": seasonal_naive_tables,
    "Growth-adjusted": growth_adjusted_tables,
    "Holt-Winters": holt_winters_tables
}

comparison_rows = []

for model_name, model_tables in (
    comparison_models.items()
):

    for series_name, model_table in (
        model_tables.items()
    ):

        common_table = (
            model_table[
                model_table["period"]
                .isin(common_periods)
            ]
            .copy()
        )

        if common_table.empty:
            raise ValueError(
                f"No common periods found for "
                f"{model_name} - {series_name}."
            )

        comparison_rows.append(
            {
                "model": model_name,
                "series": series_name,
                "MAE": (
                    common_table[
                        "absolute_error"
                    ]
                    .mean()
                ),
                "MAPE": (
                    common_table[
                        "absolute_percentage_error"
                    ]
                    .mean()
                ),
                "mean_error": (
                    common_table["error"]
                    .mean()
                )
            }
        )

common_model_comparison = (
    pd.DataFrame(comparison_rows)
)

common_model_comparison = (
    common_model_comparison
    .round(
        {
            "MAE": 0,
            "MAPE": 2,
            "mean_error": 0
        }
    )
    .sort_values(
        [
            "series",
            "MAPE"
        ]
    )
)

print(
    "\nCommon-period Model Comparison "
    "(2025-01 to 2026-09)"
)

print(
    common_model_comparison
    .to_string(index=False)
)

save_table(
    common_model_comparison,
    "common_model_comparison.csv"
)


# =========================
# 17. Q1 model comparison
# =========================

q1_evaluation_periods = [
    "2025-01",
    "2025-02",
    "2025-03",
    "2026-01",
    "2026-02",
    "2026-03"
]

q1_comparison_rows = []

for model_name, model_tables in (
    comparison_models.items()
):

    for series_name, model_table in (
        model_tables.items()
    ):

        q1_table = (
            model_table[
                model_table["period"]
                .isin(q1_evaluation_periods)
            ]
            .copy()
        )

        if q1_table.empty:
            raise ValueError(
                f"No Q1 periods found for "
                f"{model_name} - {series_name}."
            )

        q1_comparison_rows.append(
            {
                "model": model_name,
                "series": series_name,
                "MAE": (
                    q1_table[
                        "absolute_error"
                    ]
                    .mean()
                ),
                "MAPE": (
                    q1_table[
                        "absolute_percentage_error"
                    ]
                    .mean()
                ),
                "mean_error": (
                    q1_table["error"]
                    .mean()
                )
            }
        )

q1_model_comparison = (
    pd.DataFrame(q1_comparison_rows)
)

q1_model_comparison = (
    q1_model_comparison
    .round(
        {
            "MAE": 0,
            "MAPE": 2,
            "mean_error": 0
        }
    )
    .sort_values(
        [
            "series",
            "MAPE"
        ]
    )
)

print(
    "\nQ1 Model Comparison "
    "(2025-2026)"
)

print(
    q1_model_comparison
    .to_string(index=False)
)

save_table(
    q1_model_comparison,
    "q1_model_comparison.csv"
)

# =========================
# 18. Bottom-up Q1 consistency check
# =========================

domestic_q1 = (
    holt_winters_tables["Domestic"]
    .loc[
        lambda table: (
            table["period"]
            .isin(q1_evaluation_periods)
        ),
        [
            "period",
            "holt_winters_forecast"
        ]
    ]
    .rename(
        columns={
            "holt_winters_forecast":
                "domestic_forecast"
        }
    )
)

international_q1 = (
    holt_winters_tables["International"]
    .loc[
        lambda table: (
            table["period"]
            .isin(q1_evaluation_periods)
        ),
        [
            "period",
            "holt_winters_forecast"
        ]
    ]
    .rename(
        columns={
            "holt_winters_forecast":
                "international_forecast"
        }
    )
)

total_actual_q1 = (
    forecast_table[
        forecast_table["period"]
        .isin(q1_evaluation_periods)
    ][
        [
            "period",
            "total_monthly"
        ]
    ]
)

bottom_up_q1_table = (
    total_actual_q1
    .merge(
        domestic_q1,
        on="period",
        how="inner"
    )
    .merge(
        international_q1,
        on="period",
        how="inner"
    )
)

bottom_up_q1_table[
    "bottom_up_forecast"
] = (
    bottom_up_q1_table[
        "domestic_forecast"
    ]
    + bottom_up_q1_table[
        "international_forecast"
    ]
)

bottom_up_q1_table = add_error_columns(
    bottom_up_q1_table,
    "total_monthly",
    "bottom_up_forecast"
)

print(
    "\nBottom-up Q1 Forecast Table"
)

print(
    bottom_up_q1_table
    .round(0)
    .to_string(index=False)
)

save_table(
    bottom_up_q1_table.round(0),
    "bottom_up_q1_table.csv"
)

# =========================
# 19. Bottom-up Q1 performance
# =========================

bottom_up_mae = (
    bottom_up_q1_table[
        "absolute_error"
    ]
    .mean()
)

bottom_up_mape = (
    bottom_up_q1_table[
        "absolute_percentage_error"
    ]
    .mean()
)

bottom_up_mean_error = (
    bottom_up_q1_table["error"]
    .mean()
)

bottom_up_summary = pd.DataFrame(
    [
        {
            "model": "Bottom-up Holt-Winters",
            "series": "Total",
            "MAE": bottom_up_mae,
            "MAPE": bottom_up_mape,
            "mean_error": bottom_up_mean_error
        }
    ]
)

bottom_up_summary = (
    bottom_up_summary
    .round(
        {
            "MAE": 0,
            "MAPE": 2,
            "mean_error": 0
        }
    )
)

print(
    "\nBottom-up Q1 Performance"
)

print(
    bottom_up_summary
    .to_string(index=False)
)

save_table(
    bottom_up_summary,
    "bottom_up_q1_summary.csv"
)

# =========================
# 20. Final Holt-Winters forecast
# =========================

final_periods = (
    pd.period_range(
        start="2026-10",
        end="2027-03",
        freq="M"
    )
    .astype(str)
    .tolist()
)

final_q1_periods = [
    "2027-01",
    "2027-02",
    "2027-03"
]

final_forecast_columns = {
    "Domestic": "domestic_forecast",
    "International": "international_forecast",
    "Total": "total_holt_winters_forecast"
}

final_holt_forecast_tables = {}

for series_name, value_column in (
    series_columns.items()
):

    forecast_column = (
        final_forecast_columns[series_name]
    )

    full_series = (
        forecast_table[value_column]
        .dropna()
    )

    if full_series.empty:
        raise ValueError(
            f"Full series is empty for "
            f"{series_name}."
        )

    final_model = (
        ExponentialSmoothing(
            full_series,
            trend="add",
            seasonal="add",
            seasonal_periods=12
        )
    )

    final_fit = (
        final_model
        .fit(optimized=True)
    )

    final_forecast = (
        final_fit
        .forecast(len(final_periods))
    )

    if final_forecast.isna().any():
        raise ValueError(
            f"NaN forecast values found for "
            f"{series_name}."
        )

    if (final_forecast < 0).any():
        raise ValueError(
            f"Negative forecast values found for "
            f"{series_name}."
        )

    final_holt_forecast_tables[
        series_name
    ] = pd.DataFrame(
        {
            "period": final_periods,
            forecast_column: (
                final_forecast
                .to_numpy()
            )
        }
    )

# =========================
# 21. Combine final forecasts
# =========================

final_forecast_table = (
    final_holt_forecast_tables["Domestic"]
    .merge(
        final_holt_forecast_tables[
            "International"
        ],
        on="period",
        how="inner"
    )
    .merge(
        final_holt_forecast_tables["Total"],
        on="period",
        how="inner"
    )
)

final_forecast_table[
    "bottom_up_total_forecast"
] = (
    final_forecast_table[
        "domestic_forecast"
    ]
    + final_forecast_table[
        "international_forecast"
    ]
)

final_forecast_table[
    "direct_minus_bottom_up"
] = (
    final_forecast_table[
        "total_holt_winters_forecast"
    ]
    - final_forecast_table[
        "bottom_up_total_forecast"
    ]
)

final_forecast_table[
    "direct_vs_bottom_up_pct"
] = (
    final_forecast_table[
        "direct_minus_bottom_up"
    ]
    / final_forecast_table[
        "bottom_up_total_forecast"
    ]
    * 100
)

print(
    "\nForecast from 2026-10 to 2027-03"
)

print(
    final_forecast_table
    .round(0)
    .to_string(index=False)
)

save_table(
    final_forecast_table.round(0),
    "final_forecast_2026-10_to_2027-03.csv"
)

final_q1_forecast_table = (
    final_forecast_table[
        final_forecast_table["period"]
        .isin(final_q1_periods)
    ]
    .copy()
)

print(
    "\nFinal Forecast for 2027 Q1"
)

print(
    final_q1_forecast_table
    .round(0)
    .to_string(index=False)
)

save_table(
    final_q1_forecast_table.round(0),
    "final_forecast_2027_Q1.csv"
)

# =========================
# 22. Q1 forecast growth check
# =========================

q1_2026_actual = (
    forecast_table[
        forecast_table["period"]
        .isin(
            [
                "2026-01",
                "2026-02",
                "2026-03"
            ]
        )
    ][
        [
            "period",
            "domestic_monthly",
            "international_monthly",
            "total_monthly"
        ]
    ]
    .rename(
        columns={
            "period": "comparison_period",
            "domestic_monthly":
                "domestic_actual_2026",
            "international_monthly":
                "international_actual_2026",
            "total_monthly":
                "total_actual_2026"
        }
    )
)

q1_growth_check = (
    final_q1_forecast_table
    .copy()
)

q1_growth_check[
    "comparison_period"
] = (
    q1_growth_check["period"]
    .str.replace(
        "2027",
        "2026",
        regex=False
    )
)

q1_growth_check = (
    q1_growth_check
    .merge(
        q1_2026_actual,
        on="comparison_period",
        how="left"
    )
)

q1_growth_columns = [
    (
        "domestic_forecast",
        "domestic_actual_2026",
        "domestic_growth_vs_2026_pct"
    ),
    (
        "international_forecast",
        "international_actual_2026",
        "international_growth_vs_2026_pct"
    ),
    (
        "total_holt_winters_forecast",
        "total_actual_2026",
        "total_growth_vs_2026_pct"
    )
]

for forecast_column, actual_column, growth_column in (
    q1_growth_columns
):

    q1_growth_check[growth_column] = (
        q1_growth_check[forecast_column]
        / q1_growth_check[actual_column]
        - 1
    ) * 100

print(
    "\n2027 Q1 Forecast Growth Compared "
    "with 2026 Q1"
)

print(
    q1_growth_check[
        [
            "period",
            "domestic_growth_vs_2026_pct",
            "international_growth_vs_2026_pct",
            "total_growth_vs_2026_pct"
        ]
    ]
    .round(1)
    .to_string(index=False)
)

save_table(
    q1_growth_check.round(1),
    "final_q1_growth_vs_2026.csv"
)

# =========================
# 23. Forecast level reference check
# =========================

total_series = (
    forecast_table
    .set_index("period")["total_monthly"]
    .sort_index()
)

total_yoy_growth = (
    total_series
    .pct_change(
        periods=12,
        fill_method=None
    )
    .mul(100)
)

recent_yoy_growth = (
    total_yoy_growth
    .loc["2026-04":"2026-09"]
    .dropna()
)

recent_yoy_growth_table = (
    recent_yoy_growth
    .rename("total_yoy_growth_pct")
    .reset_index()
    .round(1)
)

q1_2025_total = (
    total_series
    .loc["2025-01":"2025-03"]
    .sum()
)

q1_2026_total = (
    total_series
    .loc["2026-01":"2026-03"]
    .sum()
)

q1_2026_growth_vs_2025 = (
    q1_2026_total
    / q1_2025_total
    - 1
) * 100

recent_average_growth = (
    recent_yoy_growth.mean()
)

reference_q1_total = (
    q1_2026_total
    * (
        1
        + recent_average_growth
        / 100
    )
)

direct_q1_total = (
    final_q1_forecast_table[
        "total_holt_winters_forecast"
    ]
    .sum()
)

q1_reference_summary = pd.DataFrame(
    [
        {
            "reference_period": "2026-04 to 2026-09",
            "average_yoy_growth_pct": (
                recent_average_growth
            ),
            "q1_2025_actual_total": q1_2025_total,
            "q1_2026_actual_total": q1_2026_total,
            "q1_2026_growth_vs_2025_pct": (
                q1_2026_growth_vs_2025
            ),
            "reference_q1_total": reference_q1_total,
            "direct_holt_winters_q1_total": (
                direct_q1_total
            ),
            "direct_minus_reference": (
                direct_q1_total
                - reference_q1_total
            )
        }
    ]
)

reference_rounding = {
    "average_yoy_growth_pct": 1,
    "q1_2025_actual_total": 0,
    "q1_2026_actual_total": 0,
    "q1_2026_growth_vs_2025_pct": 1,
    "reference_q1_total": 0,
    "direct_holt_winters_q1_total": 0,
    "direct_minus_reference": 0
}

print(
    "\nForecast Level Reference Check"
)
print(
    q1_reference_summary
    .round(reference_rounding)
    .to_string(index=False)
)

save_table(
    recent_yoy_growth_table,
    "recent_total_yoy_growth.csv"
)

save_table(
    q1_reference_summary.round(reference_rounding),
    "q1_reference_growth_check.csv"
)

# =========================
# 24. Save final forecast plots
# =========================

plot_definitions = [
    (
        "Domestic Passengers",
        "domestic_monthly",
        "domestic_forecast",
        "domestic_forecast.png"
    ),
    (
        "International Passengers",
        "international_monthly",
        "international_forecast",
        "international_forecast.png"
    ),
    (
        "Total Passengers: Direct Holt-Winters",
        "total_monthly",
        "total_holt_winters_forecast",
        "total_direct_holt_winters.png"
    ),
    (
        "Total Passengers: Bottom-up Holt-Winters",
        "total_monthly",
        "bottom_up_total_forecast",
        "total_bottom_up.png"
    )
]

for (
    title,
    actual_column,
    forecast_column,
    file_name
) in plot_definitions:

    figure, axis = plt.subplots(
        figsize=(14, 6)
    )

    axis.plot(
        forecast_table["period"],
        forecast_table[actual_column],
        label="Actual monthly passengers"
    )

    last_actual_period = (
        forecast_table["period"].iloc[-1]
    )

    last_actual_value = (
        forecast_table[actual_column].iloc[-1]
    )

    plot_periods = (
        [last_actual_period]
        + final_forecast_table[
            "period"
        ].tolist()
    )

    plot_values = (
        [last_actual_value]
        + final_forecast_table[
            forecast_column
        ].tolist()
    )

    axis.plot(
        plot_periods,
        plot_values,
        linestyle="--",
        marker="o",
        label="Forecast "
              "(Oct 2026 - Mar 2027)"
    )

    axis.axvline(
        "2027-01",
        color="red",
        linestyle=":",
        label="2027 Q1 begins"
    )

    axis.set_title(title)
    axis.set_xlabel("Period")
    axis.set_ylabel("Passengers")

    axis.tick_params(
        axis="x",
        rotation=45
    )

    axis.grid(True)
    axis.legend()

    figure.tight_layout()

    figure_path = (
        figures_folder
        / file_name
    )

    figure.savefig(
        figure_path,
        dpi=200,
        bbox_inches="tight"
    )

    print(
        f"Figure saved to: {figure_path}"
    )

    plt.show()
    plt.close(figure)

print(
    "\nForecast tables and figures "
    "were saved successfully."
)
