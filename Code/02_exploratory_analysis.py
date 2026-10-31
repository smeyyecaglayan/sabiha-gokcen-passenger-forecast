import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# =========================
# 1. Load processed data
# =========================

project_folder = Path(__file__).resolve().parent.parent

processed_file = (
    project_folder
    / "Processed_Data"
    / "monthly_passenger_data.csv"
)

passenger_table = pd.read_csv(processed_file)

# =========================
# 2. Check required columns
# =========================

required_columns = [
    "period",
    "year",
    "month",
    "domestic_monthly",
    "international_monthly",
    "total_monthly"
]

missing_columns = [
    column
    for column in required_columns
    if column not in passenger_table.columns
]

if missing_columns:
    raise ValueError(
        f"Missing columns: {missing_columns}"
    )

passenger_table["year"] = (
    passenger_table["year"].astype(int)
)

passenger_table["month"] = (
    passenger_table["month"].astype(int)
)

passenger_table = (
    passenger_table
    .sort_values("period")
    .reset_index(drop=True)
)

series_columns = {
    "Domestic": "domestic_monthly",
    "International": "international_monthly",
    "Total": "total_monthly"
}

value_columns = list(series_columns.values())

year_month_counts = (
    passenger_table
    .groupby("year")["month"]
    .nunique()
)

complete_years = (
    year_month_counts[
        year_month_counts.eq(12)
    ]
    .index
    .tolist()
)

if len(complete_years) < 2:
    raise ValueError(
        "At least two complete years are required "
        "for monthly seasonality analysis."
    )

complete_year_table = passenger_table[
    passenger_table["year"].isin(complete_years)
].copy()

print(
    "\nComplete years used for monthly seasonality: "
    f"{complete_years}"
)

# =========================
# 3. Basic data checks
# =========================

if passenger_table["period"].duplicated().any():
    raise ValueError(
        "Duplicate periods were found."
    )

if passenger_table[value_columns].isna().any().any():
    raise ValueError(
        "Missing passenger values were found."
    )

if (passenger_table[value_columns] < 0).any().any():
    raise ValueError(
        "Negative passenger values were found."
    )

monthly_total_check = (
    passenger_table["domestic_monthly"]
    + passenger_table["international_monthly"]
    == passenger_table["total_monthly"]
)

if not monthly_total_check.all():
    raise ValueError(
        "Domestic plus international does not equal total."
    )

print("Data check completed successfully.")

print("\nFirst five rows:")
print(
    passenger_table
    .head()
    .to_string(index=False)
)

print("\nLast five rows:")
print(
    passenger_table
    .tail()
    .to_string(index=False)
)

# =========================
# 4. Daily passenger analysis
# =========================

passenger_table["days_in_month"] = (
    pd.PeriodIndex(
        passenger_table["period"],
        freq="M"
    ).days_in_month
)

for series_name, value_column in series_columns.items():

    daily_column = (
        f"{value_column}_per_day"
    )

    passenger_table[daily_column] = (
        passenger_table[value_column]
        / passenger_table["days_in_month"]
    )

complete_year_table = passenger_table[
    passenger_table["year"].isin(complete_years)
].copy()

daily_value_columns = [
    "domestic_monthly_per_day",
    "international_monthly_per_day",
    "total_monthly_per_day"
]

daily_average = (
    complete_year_table
    .groupby("month")[daily_value_columns]
    .mean()
    .reindex(range(1, 13))
    .round(0)
)

print("\nAverage Daily Passengers by Month")
print(
    daily_average
    .to_string()
)

february_january_daily_ratio_rows = []

for year, year_table in (
    complete_year_table.groupby("year")
):

    january_table = year_table[
        year_table["month"] == 1
    ]

    february_table = year_table[
        year_table["month"] == 2
    ]

    if january_table.empty or february_table.empty:
        continue

    ratio_row = {"year": year}

    for _, value_column in (
        series_columns.items()
    ):

        daily_column = (
            f"{value_column}_per_day"
        )

        january_value = (
            january_table[daily_column].iloc[0]
        )

        february_value = (
            february_table[daily_column].iloc[0]
        )

        ratio_row[
            f"{value_column}_february_vs_january_pct"
        ] = (
            february_value
            / january_value
            * 100
        )

    february_january_daily_ratio_rows.append(
        ratio_row
    )

february_january_daily_ratio = (
    pd.DataFrame(
        february_january_daily_ratio_rows
    )
    .round(1)
)

print(
    "\nFebruary Daily Passengers as a Percentage of January"
)
print(
    february_january_daily_ratio
    .to_string(index=False)
)

# =========================
# 5. Descriptive statistics
# =========================

statistics_table = (
    passenger_table[value_columns]
    .agg(
        [
            "count",
            "mean",
            "median",
            "std",
            "min",
            "max"
        ]
    )
    .T
    .round(0)
)

statistics_table = statistics_table.rename(
    index={
        "domestic_monthly": "Domestic",
        "international_monthly": "International",
        "total_monthly": "Total"
    }
)

print("\nDescriptive Statistics")
print(
    statistics_table
    .to_string()
)

# =========================
# 6. Yearly passenger totals
# =========================

yearly_summary = (
    passenger_table
    .groupby("year")[value_columns]
    .sum()
    .round(0)
)

print("\nYearly Passenger Totals")
print(
    yearly_summary
    .to_string()
)

# =========================
# 7. Average passengers by month
# =========================

monthly_average = (
    complete_year_table
    .groupby("month")[value_columns]
    .mean()
    .reindex(range(1, 13))
    .round(0)
)

print("\nAverage Passengers by Month")
print(
    monthly_average
    .to_string()
)

# =========================
# 8. Total passenger table by year and month
# =========================

year_month_total = (
    passenger_table
    .pivot(
        index="year",
        columns="month",
        values="total_monthly"
    )
    .reindex(columns=range(1, 13))
)

print("\nTotal Passengers by Year and Month")
print(
    year_month_total
    .round(0)
    .to_string()
)

# =========================
# 9. Year-over-year monthly growth
# =========================

year_month_growth = (
    year_month_total
    .pct_change(
        axis=0,
        fill_method=None
    )
    .mul(100)
    .round(1)
)

print("\nYear-over-Year Monthly Growth (%)")
print(
    year_month_growth
    .to_string()
)

# =========================
# 10. Q1 comparison
# =========================

q1_table = passenger_table[
    passenger_table["month"].isin([1, 2, 3])
].copy()

q1_summary = (
    q1_table
    .groupby("year")[value_columns]
    .agg(["sum", "mean"])
    .round(0)
)

q1_summary.columns = [
    f"{column}_{metric}"
    for column, metric in q1_summary.columns
]

print("\nQ1 Summary by Year")
print(
    q1_summary
    .to_string()
)

# =========================
# 11. Domestic and international shares
# =========================

share_table = passenger_table[
    [
        "period",
        "domestic_monthly",
        "international_monthly",
        "total_monthly"
    ]
].copy()

share_table["domestic_share_pct"] = (
    share_table["domestic_monthly"]
    / share_table["total_monthly"]
    * 100
).round(2)

share_table["international_share_pct"] = (
    share_table["international_monthly"]
    / share_table["total_monthly"]
    * 100
).round(2)

print("\nPassenger Shares")
print(
    share_table
    .head(10)
    .to_string(index=False)
)

# =========================
# 12. Create output folders
# =========================

tables_folder = (
    project_folder
    / "Outputs"
    / "Tables"
)

figures_folder = (
    project_folder
    / "Outputs"
    / "Figures"
)

tables_folder.mkdir(
    parents=True,
    exist_ok=True
)

figures_folder.mkdir(
    parents=True,
    exist_ok=True
)

# =========================
# 13. Save analysis tables
# =========================

statistics_table.to_csv(
    tables_folder / "descriptive_statistics.csv"
)

yearly_summary.to_csv(
    tables_folder / "yearly_summary.csv"
)

monthly_average.to_csv(
    tables_folder / "monthly_average.csv"
)

daily_average.to_csv(
    tables_folder / "daily_average.csv"
)

february_january_daily_ratio.to_csv(
    tables_folder / "february_january_daily_ratio.csv",
    index=False
)

year_month_total.to_csv(
    tables_folder / "year_month_total.csv"
)

year_month_growth.to_csv(
    tables_folder / "year_month_growth.csv"
)

q1_summary.to_csv(
    tables_folder / "q1_summary.csv"
)

share_table.to_csv(
    tables_folder / "passenger_shares.csv",
    index=False
)

# =========================
# 14. Full monthly passenger graph
# =========================

figure, axis = plt.subplots(
    figsize=(14, 6)
)

for series_name, value_column in series_columns.items():

    axis.plot(
        passenger_table["period"],
        passenger_table[value_column],
        marker="o",
        linewidth=1.5,
        label=series_name
    )

axis.set_title(
    "Monthly Passenger Traffic"
)

axis.set_xlabel("Period")
axis.set_ylabel("Passengers")

axis.tick_params(
    axis="x",
    rotation=45
)

axis.grid(True)
axis.legend()

figure.tight_layout()

figure.savefig(
    figures_folder / "monthly_passenger_traffic.png",
    dpi=200
)

plt.show()
plt.close(figure)

# =========================
# 15. Average monthly seasonality graph
# =========================

figure, axes = plt.subplots(
    1,
    3,
    figsize=(18, 5),
    sharex=True
)

for axis, (series_name, value_column) in zip(
    axes,
    series_columns.items()
):

    axis.plot(
        monthly_average.index,
        monthly_average[value_column],
        marker="o"
    )

    axis.set_title(
        f"{series_name} Average by Month "
        "(Complete Years)"
    )

    axis.set_xlabel("Month")
    axis.set_ylabel("Passengers")

    axis.set_xticks(range(1, 13))
    axis.grid(True)

figure.tight_layout()

figure.savefig(
    figures_folder / "average_monthly_seasonality.png",
    dpi=200
)

plt.show()
plt.close(figure)

# =========================
# 16. Q1 total comparison graph
# =========================

q1_total = (
    q1_table
    .groupby("year")["total_monthly"]
    .sum()
)

figure, axis = plt.subplots(
    figsize=(9, 5)
)

axis.bar(
    q1_total.index.astype(str),
    q1_total.values
)

axis.set_title(
    "Q1 Total Passenger Comparison"
)

axis.set_xlabel("Year")
axis.set_ylabel("Total Q1 Passengers")

axis.grid(
    axis="y"
)

figure.tight_layout()

figure.savefig(
    figures_folder / "q1_total_comparison.png",
    dpi=200
)

plt.show()
plt.close(figure)

print(
    "\nAnalysis tables and figures were saved successfully."
)
