import pandas as pd
from pathlib import Path

# =========================
# 1. Project and data paths
# =========================

project_folder = Path(__file__).resolve().parent.parent

data_folder = project_folder / "Data"
processed_folder = project_folder / "Processed_Data"

processed_folder.mkdir(
    parents=True,
    exist_ok=True
)

# =========================
# 2. Find and sort Excel files
# =========================

excel_files = sorted(
    data_folder.glob("*.xlsx"),
    key=lambda file_path: (
        int(file_path.stem.split("_")[0]),
        int(file_path.stem.split("_")[1])
    )
)

if not excel_files:
    raise FileNotFoundError(
        f"No Excel files found in {data_folder}"
    )

print(f"Found {len(excel_files)} Excel files")

# =========================
# 3. Read Sabiha Gökçen data
# =========================

records = []

for excel_file in excel_files:

    year_text, month_text = excel_file.stem.split("_")

    year = int(year_text)
    month = int(month_text)

    passenger_data = pd.read_excel(
        excel_file,
        sheet_name="YOLCU",
        header=None
    )

    sabiha_data = passenger_data[
        passenger_data[0]
        .astype(str)
        .str.startswith(
            "İstanbul Sabiha Gökçen",
            na=False
        )
    ]

    if len(sabiha_data) != 1:
        raise ValueError(
            f"Expected one Sabiha Gökçen row in "
            f"{excel_file.name}, but found "
            f"{len(sabiha_data)} rows."
        )

    sabiha_row = sabiha_data.iloc[0]

    records.append(
        {
            "year": year,
            "month": month,
            "domestic_cumulative": int(
                pd.to_numeric(sabiha_row.iloc[4])
            ),
            "international_cumulative": int(
                pd.to_numeric(sabiha_row.iloc[5])
            ),
            "total_cumulative": int(
                pd.to_numeric(sabiha_row.iloc[6])
            )
        }
    )

passenger_table = pd.DataFrame(records)

passenger_table = (
    passenger_table
    .sort_values(["year", "month"])
    .reset_index(drop=True)
)

if not passenger_table["month"].between(1, 12).all():
    raise ValueError(
        "Month values must be between 1 and 12."
    )

first_month_by_year = (
    passenger_table
    .groupby("year")["month"]
    .min()
)

if not first_month_by_year.eq(1).all():
    missing_january_years = (
        first_month_by_year[
            ~first_month_by_year.eq(1)
        ]
        .index
        .tolist()
    )

    raise ValueError(
        "The first available month must be January. "
        f"Check these years: {missing_january_years}"
    )

# =========================
# 4. Create period column
# =========================

passenger_table["period"] = (
    passenger_table["year"].astype(str)
    + "-"
    + passenger_table["month"]
    .astype(str)
    .str.zfill(2)
)

expected_periods = (
    pd.period_range(
        start=passenger_table["period"].iloc[0],
        end=passenger_table["period"].iloc[-1],
        freq="M"
    )
    .astype(str)
    .tolist()
)

actual_periods = passenger_table["period"].tolist()

if actual_periods != expected_periods:
    raise ValueError(
        "The input files do not form a complete monthly sequence. "
        "Check for a missing or duplicated month."
    )

# =========================
# 5. Validate cumulative data
# =========================

cumulative_columns = [
    "domestic_cumulative",
    "international_cumulative",
    "total_cumulative"
]

if passenger_table[cumulative_columns].isna().any().any():
    raise ValueError(
        "Cumulative data contains missing values."
    )

if (
    passenger_table[cumulative_columns] < 0
).any().any():
    raise ValueError(
        "Cumulative data contains negative values."
    )

cumulative_total_check = (
    passenger_table["domestic_cumulative"]
    + passenger_table["international_cumulative"]
    == passenger_table["total_cumulative"]
)

if not cumulative_total_check.all():
    raise ValueError(
        "Domestic plus international cumulative values "
        "do not equal total cumulative values."
    )

# =========================
# 6. Calculate monthly values
# =========================

monthly_column_pairs = {
    "domestic_cumulative": "domestic_monthly",
    "international_cumulative": "international_monthly",
    "total_cumulative": "total_monthly"
}

for cumulative_column, monthly_column in (
    monthly_column_pairs.items()
):

    passenger_table[monthly_column] = (
        passenger_table
        .groupby("year")[cumulative_column]
        .diff()
    )

    first_month_of_year = (
        passenger_table
        .groupby("year")
        .cumcount()
        .eq(0)
    )

    passenger_table.loc[
        first_month_of_year,
        monthly_column
    ] = passenger_table.loc[
        first_month_of_year,
        cumulative_column
    ]

# =========================
# 7. Validate monthly data
# =========================

monthly_columns = [
    "domestic_monthly",
    "international_monthly",
    "total_monthly"
]

if (
    passenger_table[monthly_columns] < 0
).any().any():
    raise ValueError(
        "Monthly data contains negative values."
    )

monthly_total_check = (
    passenger_table["domestic_monthly"]
    + passenger_table["international_monthly"]
    == passenger_table["total_monthly"]
)

if not monthly_total_check.all():
    raise ValueError(
        "Domestic plus international monthly values "
        "do not equal total monthly values."
    )

# =========================
# 8. Create final processed table
# =========================

monthly_passenger_table = passenger_table[
    [
        "period",
        "year",
        "month",
        "domestic_monthly",
        "international_monthly",
        "total_monthly"
    ]
].copy()

# =========================
# 9. Save processed data
# =========================

processed_file = (
    processed_folder
    / "monthly_passenger_data.csv"
)

monthly_passenger_table.to_csv(
    processed_file,
    index=False
)

# =========================
# 10. Print results
# =========================

print("\nFirst five rows:")
print(
    monthly_passenger_table
    .head()
    .to_string(index=False)
)

print("\nLast five rows:")
print(
    monthly_passenger_table
    .tail()
    .to_string(index=False)
)

print(
    f"\nProcessed data saved to:\n{processed_file}"
)

print(
    f"\nNumber of processed months: "
    f"{len(monthly_passenger_table)}"
)
