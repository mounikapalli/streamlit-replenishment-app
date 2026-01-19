import streamlit as st
import polars as pl
import pandas as pd
import numpy as np
from datetime import timedelta
from io import BytesIO

# ==============================
# Streamlit page config
# ==============================
st.set_page_config(page_title="EBO Replenishment & Allocation", layout="wide")

# ==============================
# Store mapping dictionary
# ==============================
STORE_MAPPING = {
    "TSPL-BESANTNGR-EBO": "TSPL BESANT NAGAR EBO",
    "TSPL-CHIKKA-EBO": "TSPL CHIKKAJALA EBO",
    "TSPL-DIVINITY-MALL": "TSPL DIVINITY MALL",
    "TSPL-EMALL-EBO": "TSPL ELEMENT MALL",
    "HSR-EBO": "TSPL HSR STORE",
    "HYD-EBO": "TSPL HYDERABAD",
    "INDORE-EBO": "TSPL INDORE STORE",
    "MYSORE": "TSPL MYSORE",
    "PONDY-EBO": "TSPL PONDICHERRY",
    "PUNE-KH-EBO": "TSPL PUNE KH",
    "PUNE-PIM-EBO": "TSPL PUNE PIMPLE",
    "TSPL-RS PURAM-EBO": "TSPL RS PURAM",
    "SALEM": "TSPL SALEM",
    "TSPL-TUP": "TSPL TIRUPPUR",
    "TSPL-VIJAYAWADA-EBO": "TSPL VIJAYAWADA EBO"
}

# ==============================
# Helper functions
# ==============================
def detect_column(pl_df: pl.DataFrame, candidates: list[str]):
    """Detect the first matching column from a list of candidates."""
    norm_map = {c.strip().lower(): c for c in pl_df.columns}
    for cand in candidates:
        if cand.strip().lower() in norm_map:
            return norm_map[cand.strip().lower()]
    return None


def read_polars(uploaded):
    """
    Read uploaded CSV or Excel file into Polars DataFrame with safe dtypes.
    - Forces string column names (avoids 'Expected bytes, got int' on headers)
    - Reads values as generic object then casts to str to avoid bytes/int issues
    """
    uploaded.seek(0)
    try:
        if uploaded.name.lower().endswith((".xls", ".xlsx")):
            pdf = pd.read_excel(uploaded, dtype=object)
        else:
            pdf = pd.read_csv(uploaded, dtype=object, low_memory=False)

        # Ensure all column headers are strings
        pdf.columns = pdf.columns.map(str)

        # Convert all cells to string to avoid mixed-object/bytes issues at ingestion
        pdf = pdf.astype(str)

        df = pl.from_pandas(pdf)
        st.write(f"{uploaded.name} read successfully. Type: {type(df)}")
        return df
    except Exception as e:
        st.error(f"Error reading {uploaded.name}: {e}")
        raise


def parse_date_multi_format(df: pl.DataFrame, col: str) -> pl.Expr:
    """
    Robust date parser:
      - Tries multiple common string formats (with/without time)
      - Falls back to Excel serial number dates (days since 1899-12-30)
      - Returns a Polars expression producing a Date column
    """
    s = pl.col(col)

    # Try as strings with multiple formats
    s_utf8 = s.cast(pl.Utf8).str.strip_chars()

    fmts = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%b-%Y",
        "%d-%b-%y",
        "%d %b %Y",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",           # ISO without timezone
        "%Y-%m-%dT%H:%M:%S%.f",        # ISO with fractional seconds
    ]
    parses = [s_utf8.str.strptime(pl.Date, fmt, strict=False, exact=False) for fmt in fmts]

    # Excel serial dates: if the string can be cast to int, treat as days since 1899-12-30
    serial = s_utf8.cast(pl.Int64, strict=False)
    excel_base = pl.lit(pd.Timestamp("1899-12-30"))
    excel_date = (excel_base + pl.duration(days=serial)).dt.date()

    # If the column was already a datetime string like '2024-06-01 00:00:00',
    # the formats above catch it. Coalesce across all attempts, then excel.
    return pl.coalesce(parses + [excel_date]).alias("DATE")

# ==============================
# Cleaning functions
# ==============================
def clean_sales_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    store_col = detect_column(pl_df, ["EBO NAME", "STORE"])
    sku_col   = detect_column(pl_df, ["SKU"])
    date_col  = detect_column(pl_df, ["BILL_DATE", "DATE"])
    qty_col   = detect_column(pl_df, ["BILL_QUANTITY", "QTY"])

    if not all([store_col, sku_col, date_col, qty_col]):
        missing = [("STORE", store_col), ("SKU", sku_col), ("DATE", date_col), ("QTY", qty_col)]
        missing = [name for name, val in missing if val is None]
        raise ValueError(f"Missing required columns in sales file: {', '.join(missing)}")

    parsed_date = parse_date_multi_format(pl_df, date_col)

    qty_series = (
        pl.when(pl.col(qty_col).cast(pl.Float64) < 0)
        .then(0.0)
        .otherwise(pl.col(qty_col).cast(pl.Float64))
        .fill_null(0.0)
        .alias("QTY")
    )

    store_series = (
        pl.col(store_col)
        .cast(pl.Utf8)
        .map_elements(lambda x: STORE_MAPPING.get(str(x).strip(), str(x).strip()), return_dtype=pl.Utf8)
        .alias("STORE")
    )

    sku_series = pl.col(sku_col).cast(pl.Utf8).str.strip_chars().alias("SKU")

    out = pl_df.select([store_series, sku_series, parsed_date, qty_series])

    # Drop rows where DATE couldn't be parsed; warn if many dropped
    total_rows = out.height
    out = out.filter(pl.col("DATE").is_not_null())
    dropped = total_rows - out.height
    if out.height == 0:
        raise ValueError("All DATE values failed to parse. Please check your sales file date column.")
    if dropped > 0:
        st.warning(f"Sales: dropped {dropped} rows with unparseable dates out of {total_rows}.")

    return out


def clean_stock_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    store_col = detect_column(pl_df, ["Store Name", "STORE"])
    sku_col   = detect_column(pl_df, ["Sku", "SKU"])
    stock_col = detect_column(pl_df, ["quantity", "Stock", "Qty OH"])

    if not all([store_col, sku_col, stock_col]):
        missing = [("STORE", store_col), ("SKU", sku_col), ("STOCK", stock_col)]
        missing = [name for name, val in missing if val is None]
        raise ValueError(f"Missing required columns in stock file: {', '.join(missing)}")

    stock_series = (
        pl.when(pl.col(stock_col).cast(pl.Float64) < 0)
        .then(0.0)
        .otherwise(pl.col(stock_col).cast(pl.Float64))
        .fill_null(0.0)
        .alias("STORE_STOCK")
    )

    store_series = pl.col(store_col).cast(pl.Utf8).str.strip_chars().alias("STORE")
    sku_series = pl.col(sku_col).cast(pl.Utf8).str.strip_chars().alias("SKU")

    return pl_df.select([store_series, sku_series, stock_series])


def clean_warehouse_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    sku_col = detect_column(pl_df, ["Client SKU Id / EAN", "SKU", "Sku"])
    qty_col = detect_column(pl_df, ["Total Available Quantity", "quantity", "Stock"])

    if not all([sku_col, qty_col]):
        missing = [("SKU", sku_col), ("WAREHOUSE_QTY", qty_col)]
        missing = [name for name, val in missing if val is None]
        raise ValueError(f"Missing required columns in warehouse file: {', '.join(missing)}")

    stock_series = (
        pl.when(pl.col(qty_col).cast(pl.Float64) < 0)
        .then(0.0)
        .otherwise(pl.col(qty_col).cast(pl.Float64))
        .fill_null(0.0)
        .alias("WAREHOUSE_STOCK")
    )

    sku_series = pl.col(sku_col).cast(pl.Utf8).str.strip_chars().alias("SKU")

    return pl_df.select([sku_series, stock_series])


def clean_sku_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    sku_col = detect_column(pl_df, ["SKU", "Sku"])
    style_col = detect_column(pl_df, ["STYLE", "Style"])
    colour_col = detect_column(pl_df, ["Colour", "Color"])
    size_col = detect_column(pl_df, ["Size", "SIZE"])

    if not all([sku_col, style_col, colour_col, size_col]):
        missing = [("SKU", sku_col), ("STYLE", style_col), ("Colour", colour_col), ("Size", size_col)]
        missing = [name for name, val in missing if val is None]
        raise ValueError(f"Missing required columns in SKU master file: {', '.join(missing)}")

    return pl_df.select([
        pl.col(sku_col).cast(pl.Utf8).str.strip_chars().alias("SKU"),
        pl.col(style_col).cast(pl.Utf8).alias("STYLE"),
        pl.col(colour_col).cast(pl.Utf8).alias("Colour"),
        pl.col(size_col).cast(pl.Utf8).alias("Size")
    ])

# ==============================
# Compute Replenishment
# ==============================
def compute_replenishment(sales_pl, stock_pl, warehouse_pl, sku_master_pl, coverage_weeks, safety_weeks, weeks_back):
    # --- Clean data ---
    sales = clean_sales_pl(sales_pl)
    stock = clean_stock_pl(stock_pl)
    warehouse = clean_warehouse_pl(warehouse_pl)
    sku_master = clean_sku_master_pl(sku_master_pl)

    if sales.is_empty():
        raise ValueError("No valid sales rows after date parsing.")

    # latest_date (python date) and cutoff
    latest_date = sales["DATE"].max()
    cutoff = latest_date - timedelta(weeks=weeks_back)
    recent_sales = sales.filter(pl.col("DATE") >= cutoff)

    if recent_sales.is_empty():
        st.warning("No recent sales in the selected lookback window; using all available sales.")
        recent_sales = sales

    # --- Demand metrics ---
    demand = (
        recent_sales.group_by(["STORE", "SKU"])
        .agg([
            pl.col("QTY").sum().alias("TOTAL_SALES"),
            pl.col("QTY").mean().alias("DAILY_AVG"),
            pl.col("QTY").max().alias("Best_DRR")
        ])
        .with_columns((pl.col("TOTAL_SALES") / pl.lit(float(weeks_back))).alias("WEEKLY_AVG"))
    )

    # --- Weekly trend ---
    weekly_sales = (
        recent_sales.with_columns(pl.col("DATE").dt.week().alias("WEEK"))
        .group_by(["STORE", "SKU", "WEEK"])
        .agg(pl.col("QTY").sum().alias("WEEKLY_SALES"))
        .sort(["STORE","SKU","WEEK"])
        .with_columns(pl.arange(0, pl.len(), 1).over(["STORE","SKU"]).alias("IDX"))
    )

    trend_df = (
        weekly_sales.group_by(["STORE","SKU"])
        .agg([
            (pl.sum(pl.col("IDX") * pl.col("WEEKLY_SALES"))).alias("XY_SUM"),
            (pl.sum(pl.col("IDX")**2)).alias("XX_SUM"),
            (pl.sum(pl.col("WEEKLY_SALES"))).alias("Y_SUM"),
            pl.len("IDX").alias("N"),
            pl.sum("IDX").alias("X_SUM")
        ])
        .with_columns(
            ((pl.col("N")*pl.col("XY_SUM") - pl.col("X_SUM")*pl.col("Y_SUM")) /
             (pl.col("N")*pl.col("XX_SUM") - pl.col("X_SUM")**2)).alias("Slope")
        )
        .with_columns(
            pl.when(pl.col("Slope") > 0.05).then("Uptrend")
             .when(pl.col("Slope") < -0.05).then("Downtrend")
             .otherwise("Stable")
             .alias("Trend")
        )
        .select(["STORE","SKU","Slope","Trend"])
    )

    # --- Merge all data ---
    merged = demand.join(stock, on=["STORE","SKU"], how="left").with_columns(pl.col("STORE_STOCK").fill_null(0.0))
    merged = merged.join(sku_master, on="SKU", how="left")
    merged = merged.join(trend_df, on=["STORE","SKU"], how="left").with_columns(
        pl.col("Slope").fill_null(0.0),
        pl.col("Trend").fill_null("Stable")
    )

    # --- Target stock ---
    merged = merged.with_columns(
        ((float(coverage_weeks) + float(safety_weeks)) * pl.col("WEEKLY_AVG")).ceil().alias("TARGET_STOCK_RAW")
    )

    merged = merged.with_columns(
        pl.when(pl.col("Slope") > 0)
          .then((pl.col("TARGET_STOCK_RAW") * (1 + pl.col("Slope").clip(0.05,0.3))).ceil())
          .otherwise(
              pl.when(pl.col("Slope") < 0)
                .then((pl.col("TARGET_STOCK_RAW") * (1 - pl.col("Slope").abs().clip(0.05,0.3))).ceil())
                .otherwise(pl.col("TARGET_STOCK_RAW"))
          )
          .alias("TARGET_STOCK")
    )

    merged = merged.with_columns(
        (pl.col("TARGET_STOCK") - pl.col("STORE_STOCK")).clip_min(0).alias("DEMAND_STOCK")
    )

    # --- Replenishment from warehouse ---
    merged = merged.join(warehouse, on="SKU", how="left").with_columns(pl.col("WAREHOUSE_STOCK").fill_null(0.0))
    merged = merged.with_columns(
        pl.min_horizontal([pl.col("DEMAND_STOCK"), pl.col("WAREHOUSE_STOCK")]).alias("REPLENISHMENT_STOCK")
    )

    # --- Dynamic Size_Pct mapping (safe) ---
    size_map = {
        "M": 0.25, "L": 0.25, "XL": 0.25, "2XL": 0.25,
        "8Y": 0.25, "10Y": 0.25, "12Y": 0.25, "14Y": 0.25,
        "3XL": 0.33, "4XL": 0.33, "5XL": 0.33,
        "S": 1.0, "FSE": 1.0
    }

    merged = merged.with_columns(
        pl.col("Size").cast(pl.Utf8).map_elements(lambda x: size_map.get(x, 0.0), return_dtype=pl.Float64).alias("Size_Pct")
    )

    # --- Pivot calculations ---
    pivot_before = (
        merged.with_columns(((pl.col("STORE_STOCK") > 0).cast(pl.Float64) * pl.col("Size_Pct")).alias("Pivot_B"))
        .group_by(["STORE","STYLE","Colour"])
        .agg(pl.sum("Pivot_B").alias("Pivot_Avl_Before"))
        .with_columns(pl.col("Pivot_Avl_Before").clip_max(1.0))
    )

    pivot_after = (
        merged.with_columns((((pl.col("STORE_STOCK") + pl.col("REPLENISHMENT_STOCK") > 0).cast(pl.Float64) * pl.col("Size_Pct")).alias("Pivot_A")))
        .group_by(["STORE","STYLE","Colour"])
        .agg(pl.sum("Pivot_A").alias("Pivot_Avl_After"))
        .with_columns(pl.col("Pivot_Avl_After").clip_max(1.0))
    )

    final = merged.join(pivot_before, on=["STORE","STYLE","Colour"], how="left")
    final = final.join(pivot_after, on=["STORE","STYLE","Colour"], how="left")

    # --- Select ordered columns ---
    ordered_cols = [
        "STORE","SKU","STYLE","Colour","Size",
        "TOTAL_SALES","DAILY_AVG","Best_DRR","WEEKLY_AVG",
        "STORE_STOCK","TARGET_STOCK","DEMAND_STOCK","WAREHOUSE_STOCK",
        "REPLENISHMENT_STOCK","Pivot_Avl_Before","Pivot_Avl_After","Trend"
    ]

    # Some columns may be missing if merges didn't match; fill with defaults before select
    for c in ordered_cols:
        if c not in final.columns:
            if c in ("STYLE","Colour","Size","Trend"):
                final = final.with_columns(pl.lit(None).cast(pl.Utf8).alias(c))
            else:
                final = final.with_columns(pl.lit(0.0).cast(pl.Float64).alias(c))

    return final.select(ordered_cols).to_pandas()

# ==============================
# Streamlit UI
# ==============================
st.title("EBO Replenishment & Allocation")

with st.sidebar:
    sales_file = st.file_uploader("Upload Sales File", type=["csv","xlsx","xls"], key="sales")
    stock_file = st.file_uploader("Upload Stock File", type=["csv","xlsx","xls"], key="stock")
    warehouse_file = st.file_uploader("Upload Warehouse Stock File", type=["csv","xlsx","xls"], key="warehouse")
    sku_master_file = st.file_uploader("Upload SKU Master File", type=["csv","xlsx","xls"], key="sku_master")
    st.divider()
    coverage_weeks = st.number_input("Coverage weeks", 1, 12, 2)
    safety_weeks = st.number_input("Safety weeks", 0, 12, 1)
    weeks_back = st.number_input("Weeks lookback", 4, 52, 12)
    run = st.button("Run Replenishment")

if run:
    if not all([sales_file, stock_file, warehouse_file, sku_master_file]):
        st.error("Please upload all 4 files.")
    else:
        try:
            sales_pl = read_polars(sales_file)
            stock_pl = read_polars(stock_file)
            warehouse_pl = read_polars(warehouse_file)
            sku_master_pl = read_polars(sku_master_file)

            df_result = compute_replenishment(
                sales_pl, stock_pl, warehouse_pl, sku_master_pl,
                int(coverage_weeks), int(safety_weeks), int(weeks_back)
            )

            st.success("Replenishment calculated.")
            st.dataframe(df_result, use_container_width=True)

            # Export to Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df_result.to_excel(writer, index=False, sheet_name="Replenishment Plan")
            st.download_button(
                label="📥 Download Replenishment Plan (Excel)",
                data=output.getvalue(),
                file_name="replenishment_plan.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Error during compute: {e}")
