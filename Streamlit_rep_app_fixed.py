import streamlit as st
import polars as pl
from datetime import timedelta, datetime
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder
import pyarrow as pa
import pandas as pd
from pathlib import Path
import numpy as np
import calendar
import io

# ================================= #
#         Utility Functions         #
# ================================= #

def detect_column(pl_df: pl.DataFrame, candidates: list[str]) -> str:
    """Find matching column from candidates
    
    Args:
        pl_df: Polars DataFrame
        candidates: List of possible column names
        
    Returns:
        str: Matched column name or None if no match found
    """
    norm_map = {}
    for col in pl_df.columns:
        normalized = col.strip().lower().replace('_', ' ').replace('-', ' ')
        norm_map[normalized] = col
    
    for candidate in candidates:
        norm_candidate = candidate.strip().lower().replace('_', ' ').replace('-', ' ')
        if norm_candidate in norm_map:
            return norm_map[norm_candidate]
    
    return None

def normalize_store_name(store_name: str) -> str:
    """Normalize store names using mapping"""
    if not store_name or store_name.strip() == "":
        return "UNKNOWN_STORE"
    cleaned = store_name.strip().upper()
    cleaned = cleaned.replace("TSPL-", "").replace("-EBO", "").replace("EBO-", "")
    if cleaned in STORE_MAPPING:
        return STORE_MAPPING[cleaned]
    if store_name.strip() in STORE_MAPPING:
        return STORE_MAPPING[store_name.strip()]
    return f"TSPL {cleaned}"

def robust_parse_dates(series_pl: pl.Series) -> pl.Series:
    """Parse dates with error handling"""
    if series_pl.dtype == pl.Date:
        return series_pl
    s = series_pl.cast(pl.Utf8)
    parsed_pd = pd.to_datetime(s.to_list(), errors="coerce")
    return pl.Series(parsed_pd).cast(pl.Date)

# ================================= #
#       Store Mapping               #
# ================================= #

STORE_MAPPING = {
    # Sales file variations
    "TSPL-BESANTNGR-EBO": "TSPL BESANT NAGAR EBO",
    "BESANT NAGAR": "TSPL BESANT NAGAR EBO",
    "BESANTNGR": "TSPL BESANT NAGAR EBO",
    
    "TSPL-CHIKKA-EBO": "TSPL CHIKKAJALA EBO", 
    "CHIKKAJALA": "TSPL CHIKKAJALA EBO",
    "CHIKKA": "TSPL CHIKKAJALA EBO",
    
    "TSPL-DIVINITY-MALL": "TSPL DIVINITY MALL",
    "DIVINITY": "TSPL DIVINITY MALL",
    "DIVINITY MALL": "TSPL DIVINITY MALL",
    
    "TSPL-EMALL-EBO": "TSPL ELEMENT MALL",
    "E MALL": "TSPL ELEMENT MALL",
    "ELEMENT MALL": "TSPL ELEMENT MALL",
    "EMALL": "TSPL ELEMENT MALL",
    "TSPL-ELEMENT-MALL": "TSPL ELEMENT MALL",
    
    "HSR-EBO": "TSPL HSR STORE",
    "HSR": "TSPL HSR STORE",
    "HSR STORE": "TSPL HSR STORE",
    
    "HYD-EBO": "TSPL HYDERABAD",
    "HYDERABAD": "TSPL HYDERABAD", 
    "HYD": "TSPL HYDERABAD",
    
    "INDORE-EBO": "TSPL INDORE STORE",
    "INDORE": "TSPL INDORE STORE",
    
    "MYSORE": "TSPL MYSORE",
    "MYSORE-EBO": "TSPL MYSORE",
    
    "PONDY-EBO": "TSPL PONDICHERRY",
    "PONDICHERRY": "TSPL PONDICHERRY",
    "PONDY": "TSPL PONDICHERRY",
    
    "PUNE-KH-EBO": "TSPL PUNE KH",
    "PUNE KH": "TSPL PUNE KH",
    "PUNE": "TSPL PUNE KH",
    "PUNE-PIM-EBO": "TSPL PUNE PIMPLE",
    "TSPL-RS PURAM-EBO": "TSPL RS PURAM",
    "SALEM": "TSPL SALEM",
    "TSPL-TUP": "TSPL TIRUPPUR",
    "TSPL-VIJAYAWADA-EBO": "TSPL VIJAYAWADA EBO"
}

# ================================= #
#       Data Cleaning Functions     #
# ================================= #

@st.cache_data(ttl=3600)
def clean_sales_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Clean sales data"""
    store_col = detect_column(pl_df, ["EBO NAME", "STORE", "store_code", "Channel", "EBO"])
    sku_col = detect_column(pl_df, ["SKU", "ean", "EAN", "Product_Code"])
    date_col = detect_column(pl_df, ["BILL_DATE", "DATE", "day", "Date"])
    qty_col = detect_column(pl_df, ["BILL_QUANTITY", "QTY", "quantity"])
    
    if None in [store_col, sku_col, date_col, qty_col]:
        st.error("❌ Missing required columns in sales data")
        return pl.DataFrame()
    
    try:
        return pl_df.select([
            pl.col(store_col).cast(pl.Utf8).map_elements(normalize_store_name).alias("STORE"),
            pl.col(sku_col).cast(pl.Utf8).str.strip_chars().alias("SKU"),
            robust_parse_dates(pl_df[date_col]).alias("DATE"),
            pl.col(qty_col).cast(pl.Float64).fill_null(0).alias("QTY")
        ])
    except Exception as e:
        st.error(f"❌ Error cleaning sales data: {str(e)}")
        return pl.DataFrame()

@st.cache_data(ttl=3600)
def clean_stock_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Clean stock data"""
    store_col = detect_column(pl_df, ["Store Name", "store_code", "Channel", "EBO NAME", "STORE", "EBO"])
    sku_col = detect_column(pl_df, ["SKU", "ean", "EAN", "Product_Code"])
    stock_col = detect_column(pl_df, ["quantity", "Stock", "Qty OH", "Available_Stock"])
    
    if None in [store_col, sku_col, stock_col]:
        st.error("❌ Missing required columns in stock data")
        return pl.DataFrame()
    
    try:
        return pl_df.select([
            pl.col(store_col).cast(pl.Utf8).map_elements(normalize_store_name).alias("STORE"),
            pl.col(sku_col).cast(pl.Utf8).str.strip_chars().alias("SKU"),
            pl.col(stock_col).cast(pl.Float64).fill_null(0).alias("STORE_STOCK")
        ])
    except Exception as e:
        st.error(f"❌ Error cleaning stock data: {str(e)}")
        return pl.DataFrame()

@st.cache_data(ttl=3600)
def clean_warehouse_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Clean warehouse data"""
    sku_col = detect_column(pl_df, ["Client SKU Id / EAN", "SKU", "Sku", "Row Labels"])
    qty_col = detect_column(pl_df, ["Total Available Quantity", "quantity", "Stock", "Available in EBO"])
    
    if None in [sku_col, qty_col]:
        st.error("❌ Missing required columns in warehouse data")
        return pl.DataFrame()
    
    try:
        return pl_df.select([
            pl.col(sku_col).cast(pl.Utf8).str.strip_chars().alias("SKU"),
            pl.col(qty_col).cast(pl.Float64).fill_null(0).alias("WAREHOUSE_STOCK")
        ])
    except Exception as e:
        st.error(f"❌ Error cleaning warehouse data: {str(e)}")
        return pl.DataFrame()

@st.cache_data(ttl=3600)
def clean_sku_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Clean SKU master data"""
    sku_col = detect_column(pl_df, ["SKU", "Sku", "ean", "Row Labels"])
    style_col = detect_column(pl_df, ["STYLE", "Style"])
    colour_col = detect_column(pl_df, ["Colour", "Color"])
    size_col = detect_column(pl_df, ["Size", "SIZE"])
    
    if None in [sku_col, style_col, colour_col, size_col]:
        st.error("❌ Missing required columns in SKU master data")
        return pl.DataFrame()
    
    try:
        df = pl_df.select([
            pl.col(sku_col).cast(pl.Utf8).str.strip_chars().alias("SKU"),
            pl.col(style_col).cast(pl.Utf8).alias("STYLE"),
            pl.col(colour_col).cast(pl.Utf8).alias("Colour"),
            pl.col(size_col).cast(pl.Utf8).alias("Size")
        ])
        
        return df.with_columns([
            pl.col("Size").is_in(["S", "M", "L", "XL", "2XL"]).cast(pl.Int64).alias("IS_REGULAR_SIZE"),
            pl.col("Size").is_in(["3XL", "4XL", "5XL"]).cast(pl.Int64).alias("IS_PLUS_SIZE"),
            pl.col("Size").is_in(["08Y", "10Y", "12Y", "14Y"]).cast(pl.Int64).alias("IS_KIDS_SIZE")
        ])
    except Exception as e:
        st.error(f"❌ Error cleaning SKU master data: {str(e)}")
        return pl.DataFrame()

@st.cache_data(ttl=3600)
def clean_style_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Clean style master data"""
    style_col = detect_column(pl_df, ["STYLE", "Style", "Style Code", "Article"])
    gender_col = detect_column(pl_df, ["GENDER", "Gender", "Department"])
    
    if None in [style_col, gender_col]:
        st.error("❌ Missing required columns in style master data")
        return pl.DataFrame()
    
    try:
        return pl_df.select([
            pl.col(style_col).cast(pl.Utf8).alias("STYLE"),
            pl.col(gender_col).cast(pl.Utf8).map_elements(lambda x: x.strip().title()).alias("GENDER")
        ])
    except Exception as e:
        st.error(f"❌ Error cleaning style master data: {str(e)}")
        return pl.DataFrame()

@st.cache_data(ttl=3600)
def clean_store_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Clean store master data"""
    store_col = detect_column(pl_df, ["Store", "store_code", "Store Name", "Store_Code", "EBO", "Location"])
    if store_col is None:
        st.error("❌ Missing required column 'Store' in store master data")
        return pl.DataFrame()
    
    try:
        return pl_df.select([
            pl.col(store_col).cast(pl.Utf8).map_elements(normalize_store_name).alias("STORE")
        ])
    except Exception as e:
        st.error(f"❌ Error cleaning store master data: {str(e)}")
        return pl.DataFrame()