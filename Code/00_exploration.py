import pandas as pd
from pathlib import Path

# =========================
# 1. Define project paths
# =========================

project_folder = (
    Path(__file__).resolve().parent.parent
)

data_folder = project_folder / "Data"

if not data_folder.exists():
    raise FileNotFoundError(
        "Data folder was not found."
    )

# =========================
# 2. Find Excel files
# =========================

excel_files = sorted(
    data_folder.glob("*.xlsx")
)

if not excel_files:
    raise FileNotFoundError(
        "No Excel files were found."
    )

print(
    f"Found {len(excel_files)} Excel files."
)

print(
    f"First file: {excel_files[0].name}"
)

print(
    f"Last file: {excel_files[-1].name}"
)

# =========================
# 3. Select two months
# =========================

sample_year = 2025

january_file = (
    data_folder
    / f"{sample_year}_01.xlsx"
)

february_file = (
    data_folder
    / f"{sample_year}_02.xlsx"
)

if not january_file.exists():
    raise FileNotFoundError(
        f"{january_file.name} was not found."
    )

if not february_file.exists():
    raise FileNotFoundError(
        f"{february_file.name} was not found."
    )

# =========================
# 4. Read Sabiha Gökçen data
# =========================

def load_sabiha_cumulative(file_path):

    excel_workbook = pd.ExcelFile(
        file_path
    )

    if "YOLCU" not in excel_workbook.sheet_names:
        raise ValueError(
            f"'YOLCU' sheet was not found in "
            f"{file_path.name}."
        )

    passenger_data = pd.read_excel(
        file_path,
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
            f"{file_path.name}, but found "
            f"{len(sabiha_data)} rows."
        )

    sabiha_row = sabiha_data.iloc[0]

    return pd.Series(
        {
            "domestic_cumulative": int(
                sabiha_row.iloc[4]
            ),
            "international_cumulative": int(
                sabiha_row.iloc[5]
            ),
            "total_cumulative": int(
                sabiha_row.iloc[6]
            )
        }
    )

january_cumulative = (
    load_sabiha_cumulative(january_file)
)

february_cumulative = (
    load_sabiha_cumulative(february_file)
)

# =========================
# 5. Convert cumulative data
# =========================

february_monthly_values = (
    february_cumulative
    - january_cumulative
)

if (
    february_monthly_values < 0
).any():
    raise ValueError(
        "February cumulative values are lower "
        "than January values."
    )

february_row = pd.DataFrame(
    {
        "period": [f"{sample_year}-02"],
        "domestic_monthly": [
            february_monthly_values[
                "domestic_cumulative"
            ]
        ],
        "international_monthly": [
            february_monthly_values[
                "international_cumulative"
            ]
        ],
        "total_monthly": [
            february_monthly_values[
                "total_cumulative"
            ]
        ]
    }
)

# =========================
# 6. Display result
# =========================

print(
    f"\nCumulative data comparison:"
)

print(
    pd.DataFrame(
        {
            "January": january_cumulative,
            "February": february_cumulative
        }
    )
    .to_string()
)

print(
    f"\nCalculated monthly value for "
    f"{sample_year}-02:"
)

print(
    february_row.to_string(index=False)
)