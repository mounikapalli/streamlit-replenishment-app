import polars as pl
import streamlit as st
from datetime import datetime, timedelta
from utils import normalize_store_name, detect_column

def clean_sales_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Clean sales data."""
    try:
        # Required columns
        store_col = detect_column(pl_df, ["Store Name", "store_code", "Channel", "EBO NAME", "STORE"])
        sku_col = detect_column(pl_df, ["SKU", "Sku", "ean", "Row Labels"])
        date_col = detect_column(pl_df, ["DATE", "Bill Date", "Sales Date"])
        qty_col = detect_column(pl_df, ["BILL_QUANTITY", "Bill Quantity", "Quantity"])

        if None in [store_col, sku_col, date_col, qty_col]:
            st.error("❌ Missing required columns in sales data")
            return pl.DataFrame()

        return pl_df.select([
            pl_df[store_col].cast(pl.Utf8).map_elements(normalize_store_name).alias("STORE"),
            pl_df[sku_col].cast(pl.Utf8).str.strip_chars().alias("SKU"),
            pl_df[date_col].cast(pl.Date).alias("DATE"),
            pl.when(pl_df[qty_col].cast(pl.Float64) < 0)
            .then(0)
            .otherwise(pl_df[qty_col].cast(pl.Float64))
            .fill_null(0)
            .alias("QTY")
        ])
    except Exception as e:
        st.error(f"❌ Error cleaning sales data: {str(e)}")
        return pl.DataFrame()

def clean_stock_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Clean store stock data."""
    try:
        store_col = detect_column(pl_df, ["Store Name", "store_code", "Channel", "EBO NAME", "STORE"])
        sku_col = detect_column(pl_df, ["Sku", "SKU", "ean", "Row Labels"])
        stock_col = detect_column(pl_df, ["quantity", "Stock", "Qty OH", "Available_Stock"])

        if None in [store_col, sku_col, stock_col]:
            st.error("❌ Missing required columns in stock data")
            return pl.DataFrame()

        return pl_df.select([
            pl_df[store_col].cast(pl.Utf8).map_elements(normalize_store_name).alias("STORE"),
            pl_df[sku_col].cast(pl.Utf8).str.strip_chars().alias("SKU"),
            pl.when(pl_df[stock_col].cast(pl.Float64) < 0)
            .then(0)
            .otherwise(pl_df[stock_col].cast(pl.Float64))
            .fill_null(0)
            .alias("STORE_STOCK")
        ])
    except Exception as e:
        st.error(f"❌ Error cleaning stock data: {str(e)}")
        return pl.DataFrame()

def clean_warehouse_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Clean warehouse stock data."""
    try:
        sku_col = detect_column(pl_df, ["Client SKU Id / EAN", "SKU", "Sku", "Row Labels"])
        qty_col = detect_column(pl_df, ["Total Available Quantity", "quantity", "Stock", "Available in EBO"])

        if None in [sku_col, qty_col]:
            st.error("❌ Missing required columns in warehouse data")
            return pl.DataFrame()

        return pl_df.select([
            pl_df[sku_col].cast(pl.Utf8).str.strip_chars().alias("SKU"),
            pl.when(pl_df[qty_col].cast(pl.Float64) < 0)
            .then(0)
            .otherwise(pl_df[qty_col].cast(pl.Float64))
            .fill_null(0)
            .alias("WAREHOUSE_STOCK")
        ])
    except Exception as e:
        st.error(f"❌ Error cleaning warehouse data: {str(e)}")
        return pl.DataFrame()

def clean_sku_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Clean SKU master data."""
    try:
        # Required column detection
        sku_col = detect_column(pl_df, ["SKU", "Sku", "ean", "Row Labels"])
        style_col = detect_column(pl_df, ["STYLE", "Style"])
        colour_col = detect_column(pl_df, ["Colour", "Color"])
        size_col = detect_column(pl_df, ["Size", "SIZE"])

        if None in [sku_col, style_col, colour_col, size_col]:
            st.error("❌ Missing required columns in SKU master")
            return pl.DataFrame()

        return pl_df.select([
            pl_df[sku_col].cast(pl.Utf8).str.strip_chars().alias("SKU"),
            pl_df[style_col].cast(pl.Utf8).alias("STYLE"),
            pl_df[colour_col].cast(pl.Utf8).alias("Colour"),
            pl_df[size_col].cast(pl.Utf8).alias("Size")
        ]).with_columns([
            # Add size categorization
            pl.col("Size").is_in(["S", "M", "L", "XL", "2XL"]).cast(pl.Int64).alias("IS_REGULAR_SIZE"),
            pl.col("Size").is_in(["3XL", "4XL", "5XL"]).cast(pl.Int64).alias("IS_PLUS_SIZE"),
            pl.col("Size").is_in(["08Y", "10Y", "12Y", "14Y"]).cast(pl.Int64).alias("IS_KIDS_SIZE")
        ])
    except Exception as e:
        st.error(f"❌ Error cleaning SKU master: {str(e)}")
        return pl.DataFrame()

def compute_replenishment(sales_pl, stock_pl, warehouse_pl, sku_master_pl, coverage_weeks, safety_weeks, weeks_back, style_master_pl=None, store_master_pl=None):
    """Compute replenishment recommendations."""
    try:
        # Clean and validate all input data first
        sales = clean_sales_pl(sales_pl)
        if sales.is_empty():
            st.error("❌ No valid sales data after cleaning")
            return pl.DataFrame()

        stock = clean_stock_pl(stock_pl)
        if stock.is_empty():
            st.error("❌ No valid stock data after cleaning")
            return pl.DataFrame()

        warehouse = clean_warehouse_pl(warehouse_pl)
        if warehouse.is_empty():
            st.error("❌ No valid warehouse data after cleaning")
            return pl.DataFrame()

        sku_master = clean_sku_master_pl(sku_master_pl)
        if sku_master.is_empty():
            st.error("❌ No valid SKU master data after cleaning")
            return pl.DataFrame()

        # Calculate date ranges
        latest_date = sales["DATE"].max()
        cutoff_date = latest_date - timedelta(weeks=weeks_back)

        # Calculate weekly averages
        demand = (
            sales.filter(pl.col("DATE") >= cutoff_date)
            .group_by(["STORE", "SKU"])
            .agg([
                pl.col("QTY").sum().alias("TOTAL_SALES"),
                (pl.col("QTY").sum() / weeks_back).alias("WEEKLY_AVG")
            ])
        )

        # Join with current stock levels
        df = (
            demand.join(stock, on=["STORE", "SKU"], how="outer")
            .join(warehouse, on="SKU", how="left")
            .join(sku_master, on="SKU", how="left")
            .with_columns([
                pl.col("STORE_STOCK").fill_null(0),
                pl.col("WAREHOUSE_STOCK").fill_null(0),
                pl.col("WEEKLY_AVG").fill_null(0)
            ])
        )

        # Calculate replenishment quantities
        df = df.with_columns([
            # Basic demand calculation
            (pl.col("WEEKLY_AVG") * (coverage_weeks + safety_weeks)).alias("DEMAND_STOCK"),
            
            # Current weeks of stock
            pl.when(pl.col("WEEKLY_AVG") > 0)
            .then(pl.col("STORE_STOCK") / pl.col("WEEKLY_AVG"))
            .otherwise(99)
            .alias("WEEKS_OF_STOCK"),
            
            # Stock fill rate percentage
            (100 * pl.col("STORE_STOCK") / 
             pl.when(pl.col("WEEKLY_AVG") * coverage_weeks > 0)
             .then(pl.col("WEEKLY_AVG") * coverage_weeks)
             .otherwise(1))
            .clip(0, 100)
            .alias("STOCK_FILL_RATE_PCT")
        ])

        # Calculate final replenishment quantities
        df = df.with_columns([
            pl.when(
                (pl.col("STORE_STOCK") < pl.col("DEMAND_STOCK")) &
                (pl.col("WAREHOUSE_STOCK") > 0)
            )
            .then(
                pl.element().clip(
                    0,
                    pl.col("DEMAND_STOCK") - pl.col("STORE_STOCK")
                )
            )
            .otherwise(0)
            .alias("REPLENISHMENT_STOCK")
        ])

        # Sort by store and SKU
        df = df.sort(["STORE", "SKU"])

        return df

    except Exception as e:
        st.error(f"❌ Error computing replenishment: {str(e)}")
        return pl.DataFrame()