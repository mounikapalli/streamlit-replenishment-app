import streamlit as st
import polars as pl
from datetime import timedelta
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder
import pyarrow as pa
import pandas as pd

# Cache the data loading functions
@st.cache_data
def read_to_pd(uploaded, force_csv=False):
    if uploaded is None:
        return pl.DataFrame()
    uploaded.seek(0)
    if force_csv or uploaded.name.lower().endswith(".csv"):
        return pl.read_csv(uploaded)
    else:
        return pl.read_excel(uploaded)

# Cache the store mapping
STORE_MAPPING = {
    "TSPL-BESANTNGR-EBO": "TSPL BESANT NAGAR EBO",
    "BESANT NAGAR": "TSPL BESANT NAGAR EBO",
    "BESANTNGR": "TSPL BESANT NAGAR EBO",
    "TSPL-CHIKKA-EBO": "TSPL CHIKKAJALA EBO", 
    "CHIKKAJALA": "TSPL CHIKKAJALA EBO",
    "CHIKKA": "TSPL CHIKKAJALA EBO",
    # ... [rest of the mapping]
}

@st.cache_data
def normalize_store_name(store_name: str) -> str:
    """Normalize store names with caching"""
    if not store_name or store_name.strip() == "":
        return "UNKNOWN_STORE"
    cleaned = store_name.strip().upper()
    cleaned = cleaned.replace("TSPL-", "").replace("-EBO", "").replace("EBO-", "")
    return STORE_MAPPING.get(cleaned, STORE_MAPPING.get(store_name.strip(), f"TSPL {cleaned}"))

@st.cache_data
def clean_sales_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Optimized sales data cleaning with caching"""
    # Quick validation of required columns
    required_cols = {
        "STORE": ["EBO NAME", "STORE", "store_code", "Channel", "EBO"],
        "SKU": ["SKU", "ean", "EAN", "Product_Code"],
        "DATE": ["BILL_DATE", "DATE", "day", "Date"],
        "QTY": ["BILL_QUANTITY", "QTY", "quantity", "Quantity"]
    }
    
    found_cols = {}
    for key, alternatives in required_cols.items():
        found = None
        for alt in alternatives:
            if alt in pl_df.columns:
                found = alt
                break
        if not found:
            st.error(f"Missing required column: {key}")
            return pl.DataFrame()
        found_cols[key] = found

    # Process data in a single pass
    return (pl_df
            .select([
                pl.col(found_cols["STORE"]).map_elements(normalize_store_name).alias("STORE"),
                pl.col(found_cols["SKU"]).cast(pl.Utf8).str.strip_chars().alias("SKU"),
                pl.col(found_cols["DATE"]).cast(pl.Date).alias("DATE"),
                pl.when(pl.col(found_cols["QTY"]).cast(pl.Float64) < 0)
                .then(0)
                .otherwise(pl.col(found_cols["QTY"]).cast(pl.Float64))
                .alias("QTY")
            ])
            .filter(
                (pl.col("SKU").is_not_null()) & 
                (pl.col("SKU") != "") & 
                (pl.col("QTY") > 0)
            ))

@st.cache_data
def compute_replenishment(sales_pl, stock_pl, warehouse_pl, sku_master_pl, coverage_weeks, safety_weeks, weeks_back):
    """Optimized replenishment calculation with caching"""
    if sales_pl.is_empty() or stock_pl.is_empty() or warehouse_pl.is_empty() or sku_master_pl.is_empty():
        return pl.DataFrame()

    # Process sales data
    latest_date = sales_pl["DATE"].max()
    cutoff = latest_date - timedelta(weeks=weeks_back)
    
    # Compute sales metrics in a single pass
    sales_metrics = (sales_pl
        .filter(pl.col("DATE") >= cutoff)
        .group_by(["STORE", "SKU"])
        .agg([
            pl.col("QTY").sum().alias("TOTAL_SALES"),
            (pl.col("QTY").sum() / weeks_back).alias("WEEKLY_AVG"),
            pl.col("QTY").count().alias("TRANSACTION_COUNT")
        ]))

    # Process store performance in parallel with sales metrics
    store_performance = (sales_pl
        .filter(pl.col("DATE") >= cutoff)
        .group_by("STORE")
        .agg([
            pl.col("QTY").sum().alias("STORE_TOTAL_SALES"),
            pl.col("SKU").n_unique().alias("ACTIVE_SKUS")
        ])
        .with_columns([
            (pl.col("STORE_TOTAL_SALES") / pl.col("ACTIVE_SKUS")).alias("SALES_PER_SKU")
        ]))

    # Join all data in an optimized way
    result = (sales_metrics
        .join(stock_pl.select(["STORE", "SKU", "STORE_STOCK"]), on=["STORE", "SKU"], how="left")
        .with_columns(pl.col("STORE_STOCK").fill_null(0))
        .join(warehouse_pl.select(["SKU", "WAREHOUSE_STOCK"]), on="SKU", how="left")
        .with_columns(pl.col("WAREHOUSE_STOCK").fill_null(0))
        .join(store_performance.select(["STORE", "SALES_PER_SKU"]), on="STORE", how="left"))

    # Compute final metrics efficiently
    result = result.with_columns([
        # Target stock calculation
        ((pl.col("WEEKLY_AVG") * (coverage_weeks + safety_weeks)).ceil()).alias("TARGET_STOCK"),
        
        # Stock weeks
        (pl.col("STORE_STOCK") / pl.col("WEEKLY_AVG")).round(1).alias("WEEKS_OF_STOCK"),
        
        # Demand calculation
        pl.when(pl.col("TARGET_STOCK") - pl.col("STORE_STOCK") < 0)
        .then(0)
        .otherwise(pl.col("TARGET_STOCK") - pl.col("STORE_STOCK"))
        .alias("DEMAND_STOCK"),
        
        # Store performance classification
        pl.when(pl.col("SALES_PER_SKU") >= pl.col("SALES_PER_SKU").quantile(0.8))
        .then("High Velocity")
        .when(pl.col("SALES_PER_SKU") >= pl.col("SALES_PER_SKU").quantile(0.4))
        .then("Medium Velocity")
        .otherwise("Low Velocity")
        .alias("STORE_PERFORMANCE")
    ])

    # Final replenishment calculation
    result = result.with_columns([
        pl.when(
            (pl.col("WEEKS_OF_STOCK") < coverage_weeks) & 
            (pl.col("WAREHOUSE_STOCK") > 0) & 
            (pl.col("WEEKLY_AVG") > 0)
        )
        .then(pl.min_horizontal([
            pl.col("DEMAND_STOCK"),
            pl.col("WAREHOUSE_STOCK")
        ]))
        .otherwise(0)
        .alias("REPLENISHMENT_STOCK")
    ])

    return result

# Streamlit UI with optimized rendering
st.set_page_config(page_title="Replenishment System", layout="wide")

st.title("Optimized Replenishment System")

# File uploads in sidebar for better space utilization
with st.sidebar:
    st.header("Data Upload")
    sales_file = st.file_uploader("Sales Data", type=["csv", "xlsx"])
    stock_file = st.file_uploader("Stock Data", type=["csv", "xlsx"])
    warehouse_file = st.file_uploader("Warehouse Data", type=["csv", "xlsx"])
    sku_master_file = st.file_uploader("SKU Master", type=["csv", "xlsx"])
    
    st.header("Parameters")
    coverage_weeks = st.number_input("Coverage Weeks", 1, 12, 2)
    safety_weeks = st.number_input("Safety Weeks", 0, 12, 1)
    weeks_back = st.number_input("Analysis Weeks", 4, 52, 12)

# Main content area
if all([sales_file, stock_file, warehouse_file, sku_master_file]):
    with st.spinner("Processing data..."):
        # Load data with caching
        sales_pl = read_to_pd(sales_file)
        stock_pl = read_to_pd(stock_file)
        warehouse_pl = read_to_pd(warehouse_file)
        sku_master_pl = read_to_pd(sku_master_file)
        
        # Compute replenishment with caching
        result = compute_replenishment(
            sales_pl, stock_pl, warehouse_pl, sku_master_pl,
            coverage_weeks, safety_weeks, weeks_back
        )
        
        if not result.is_empty():
            st.success("Replenishment plan generated!")
            
            # Show summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                total_replenishment = result["REPLENISHMENT_STOCK"].sum()
                st.metric("Total Replenishment", f"{total_replenishment:,.0f}")
            with col2:
                stores_covered = result.filter(pl.col("REPLENISHMENT_STOCK") > 0)["STORE"].n_unique()
                st.metric("Stores Covered", stores_covered)
            with col3:
                skus_allocated = result.filter(pl.col("REPLENISHMENT_STOCK") > 0)["SKU"].n_unique()
                st.metric("SKUs Allocated", skus_allocated)
            
            # Show results in an efficient grid
            gb = GridOptionsBuilder.from_dataframe(result.to_pandas())
            gb.configure_default_column(groupable=True, sorteable=True)
            grid_options = gb.build()
            
            AgGrid(
                result.to_pandas(),
                gridOptions=grid_options,
                enable_enterprise_modules=True,
                height=400
            )
            
else:
    st.info("Please upload all required files to begin.")