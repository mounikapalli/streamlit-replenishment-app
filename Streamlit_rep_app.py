import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import io

# Set page configuration for a clean, minimalist look
st.set_page_config(
    page_title="Retail Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a cleaner look
st.markdown("""
    <style>
        .main { padding: 2rem; }
        .title {
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 500;
            color: #1E1E1E;
            padding-bottom: 1rem;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 6px;
            text-align: center;
        }
        .stButton button {
            border-radius: 4px;
            padding: 0.5rem 1rem;
            background-color: #0066cc;
        }
        .dataframe {
            border: none !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# Utility Functions
def detect_column(df: pd.DataFrame, possible_names: list) -> str:
    """Find a column from a list of possible names"""
    for name in possible_names:
        matches = [col for col in df.columns if name.lower() in col.lower()]
        if matches:
            return matches[0]
    return None

def safe_numeric(value):
    """Safely convert value to numeric, return 0 if not possible"""
    try:
        num = float(value)
        return num if not pd.isna(num) else 0
    except (ValueError, TypeError):
        return 0

def clean_text(value):
    """Clean text fields"""
    if pd.isna(value):
        return ""
    return str(value).strip().upper()

# Utility Functions
def detect_column(df: pd.DataFrame, possible_names: list) -> str:
    """Find a column from a list of possible names"""
    for name in possible_names:
        matches = [col for col in df.columns if name.lower() in col.lower()]
        if matches:
            return matches[0]
    return None

def safe_numeric(value):
    """Safely convert value to numeric, return 0 if not possible"""
    try:
        num = float(value)
        return num if not pd.isna(num) else 0
    except (ValueError, TypeError):
        return 0

def clean_text(value):
    """Clean text fields"""
    if pd.isna(value):
        return ""
    return str(value).strip().upper()

# Data Reading Functions
def read_file(uploaded_file):
    """Read uploaded file into pandas DataFrame"""
    if uploaded_file is None:
        return pd.DataFrame()
        
    try:
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        if file_type == 'csv':
            df = pd.read_csv(uploaded_file)
        elif file_type in ['xls', 'xlsx']:
            df = pd.read_excel(uploaded_file)
        else:
            st.error(f"Unsupported file type: {file_type}")
            return pd.DataFrame()
            
        # Basic cleaning
        df = df.fillna('')
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip()
                
        return df
        
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return pd.DataFrame()

# Data Cleaning Functions
def clean_sales_data(df):
    """Clean sales data"""
    if df.empty:
        return pd.DataFrame()
    
    try:
        # Detect required columns
        store_col = detect_column(df, ['store', 'store name', 'ebo', 'channel'])
        sku_col = detect_column(df, ['sku', 'ean', 'product code'])
        date_col = detect_column(df, ['date', 'bill date', 'transaction date'])
        qty_col = detect_column(df, ['quantity', 'qty', 'bill quantity'])
        
        if not all([store_col, sku_col, date_col, qty_col]):
            missing = []
            if not store_col: missing.append("Store")
            if not sku_col: missing.append("SKU")
            if not date_col: missing.append("Date")
            if not qty_col: missing.append("Quantity")
            st.error(f"Missing required columns: {', '.join(missing)}")
            return pd.DataFrame()
        
        # Create cleaned dataframe
        cleaned_df = pd.DataFrame({
            'STORE': df[store_col].apply(clean_text),
            'SKU': df[sku_col].apply(clean_text),
            'DATE': pd.to_datetime(df[date_col], errors='coerce'),
            'QUANTITY': df[qty_col].apply(safe_numeric)
        })
        
        # Remove invalid records
        cleaned_df = cleaned_df.dropna(subset=['DATE'])
        cleaned_df = cleaned_df[cleaned_df['QUANTITY'] > 0]
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"Error cleaning sales data: {str(e)}")
        return pd.DataFrame()

def clean_stock_data(df):
    """Clean stock data"""
    if df.empty:
        return pd.DataFrame()
    
    try:
        # Detect required columns
        store_col = detect_column(df, ['store', 'store name', 'ebo', 'channel'])
        sku_col = detect_column(df, ['sku', 'ean', 'product code'])
        stock_col = detect_column(df, ['stock', 'quantity', 'qty', 'available'])
        
        if not all([store_col, sku_col, stock_col]):
            missing = []
            if not store_col: missing.append("Store")
            if not sku_col: missing.append("SKU")
            if not stock_col: missing.append("Stock")
            st.error(f"Missing required columns: {', '.join(missing)}")
            return pd.DataFrame()
        
        # Create cleaned dataframe
        cleaned_df = pd.DataFrame({
            'STORE': df[store_col].apply(clean_text),
            'SKU': df[sku_col].apply(clean_text),
            'STOCK': df[stock_col].apply(safe_numeric)
        })
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"Error cleaning stock data: {str(e)}")
        return pd.DataFrame()

def clean_warehouse_data(df):
    """Clean warehouse data"""
    if df.empty:
        return pd.DataFrame()
    
    try:
        # Detect required columns
        sku_col = detect_column(df, ['sku', 'ean', 'product code'])
        stock_col = detect_column(df, ['stock', 'quantity', 'available quantity'])
        
        if not all([sku_col, stock_col]):
            missing = []
            if not sku_col: missing.append("SKU")
            if not stock_col: missing.append("Stock")
            st.error(f"Missing required columns: {', '.join(missing)}")
            return pd.DataFrame()
        
        # Create cleaned dataframe
        cleaned_df = pd.DataFrame({
            'SKU': df[sku_col].apply(clean_text),
            'WAREHOUSE_STOCK': df[stock_col].apply(safe_numeric)
        })
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"Error cleaning warehouse data: {str(e)}")
        return pd.DataFrame()

def clean_sku_master(df):
    """Clean SKU master data"""
    if df.empty:
        return pd.DataFrame()
    
    try:
        # Detect required columns
        sku_col = detect_column(df, ['sku', 'ean', 'product code'])
        style_col = detect_column(df, ['style', 'style code'])
        color_col = detect_column(df, ['color', 'colour'])
        size_col = detect_column(df, ['size'])
        
        if not all([sku_col, style_col, color_col, size_col]):
            missing = []
            if not sku_col: missing.append("SKU")
            if not style_col: missing.append("Style")
            if not color_col: missing.append("Color")
            if not size_col: missing.append("Size")
            st.error(f"Missing required columns: {', '.join(missing)}")
            return pd.DataFrame()
        
        # Create cleaned dataframe
        cleaned_df = pd.DataFrame({
            'SKU': df[sku_col].apply(clean_text),
            'STYLE': df[style_col].apply(clean_text),
            'COLOR': df[color_col].apply(clean_text),
            'SIZE': df[size_col].apply(clean_text)
        })
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"Error cleaning SKU master data: {str(e)}")
        return pd.DataFrame()

def clean_style_master(df):
    """Clean style master data"""
    if df.empty:
        return pd.DataFrame()
    
    try:
        # Detect required columns
        style_col = detect_column(df, ['style', 'style code'])
        gender_col = detect_column(df, ['gender', 'department'])
        
        if not all([style_col, gender_col]):
            missing = []
            if not style_col: missing.append("Style")
            if not gender_col: missing.append("Gender")
            st.error(f"Missing required columns: {', '.join(missing)}")
            return pd.DataFrame()
        
        # Create cleaned dataframe
        cleaned_df = pd.DataFrame({
            'STYLE': df[style_col].apply(clean_text),
            'GENDER': df[gender_col].apply(clean_text)
        })
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"Error cleaning style master data: {str(e)}")
        return pd.DataFrame()

def process_uploaded_files(uploaded_files):
    """Process all uploaded files"""
    try:
        # Initialize results dictionary
        results = {}
        
        # Process each file
        if uploaded_files.get('sales'):
            df = read_file(uploaded_files['sales'])
            results['sales'] = clean_sales_data(df)
            
        if uploaded_files.get('stock'):
            df = read_file(uploaded_files['stock'])
            results['stock'] = clean_stock_data(df)
            
        if uploaded_files.get('warehouse'):
            df = read_file(uploaded_files['warehouse'])
            results['warehouse'] = clean_warehouse_data(df)
            
        if uploaded_files.get('sku_master'):
            df = read_file(uploaded_files['sku_master'])
            results['sku_master'] = clean_sku_master(df)
            
        if uploaded_files.get('style_master'):
            df = read_file(uploaded_files['style_master'])
            results['style_master'] = clean_style_master(df)
        
        return results
        
    except Exception as e:
        st.error(f"Error processing files: {str(e)}")
        return {}

# ================================= #
#       Data Cleaning Functions     #
# ================================= #

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

# ================================= #
#       Utility Functions           #
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

# ================================= #
#       Data Cleaning Module        #
# ================================= #

# ================================= #
#       Data Cleaning Module        #
# ================================= #

# ------------------------ #
# Cleaning Functions      #
# ------------------------ #

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

# ------------------------ #
# Data Cleaning Functions  #
# ------------------------ #

def detect_column(pl_df: pl.DataFrame, candidates: list[str]):
    """Find matching column from candidates"""
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

# ------------------------ #
# Data Cleaning Functions  #
# ------------------------ #

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



# ------------------------ #
# Helper functions
# ------------------------ #

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
def detect_column(pl_df: pl.DataFrame, candidates: list[str]):
    """Find matching column from candidates"""
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
#      Store Mapping Dictionary     #
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
#      Data Cleaning Functions      #
# ================================= #

@st.cache_data(ttl=3600)
def clean_sales_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """Clean sales data with validation and error handling"""
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
    """Clean stock data with validation and error handling"""
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
    """Clean warehouse data with validation and error handling"""
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
    """Clean SKU master data with validation and error handling"""
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
    """Clean style master data with validation and error handling"""
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
    """Clean store master data with validation and error handling"""
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
# Place the function at the top with other helper functions
@st.cache_data(ttl=3600)


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
    color_col = detect_column(pl_df, ["Colour", "Color"])
    size_col = detect_column(pl_df, ["Size", "SIZE"])
    
    if None in [sku_col, style_col, color_col, size_col]:
        st.error("❌ Missing required columns in SKU master data")
        return pl.DataFrame()
    
    try:
        df = pl_df.select([
            pl.col(sku_col).cast(pl.Utf8).str.strip_chars().alias("SKU"),
            pl.col(style_col).cast(pl.Utf8).alias("STYLE"),
            pl.col(color_col).cast(pl.Utf8).alias("Colour"),
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

@st.cache_data(ttl=3600)  # Cache for 1 hour
def read_to_pd(uploaded, force_csv=False, expected_columns=None):
    """
    Safely read data from uploaded file to Polars DataFrame with validation.
    Uses caching to improve performance on repeated reads.
    
    Args:
        uploaded: The uploaded file object
        force_csv: Whether to force reading as CSV
        expected_columns: List of required columns to validate against
        
    Returns:
        pl.DataFrame: The loaded and validated dataframe
    """
    if uploaded is None:
        return pl.DataFrame()
        
    try:
        uploaded.seek(0)
        file_ext = uploaded.name.lower()
        
        try:
            if force_csv or file_ext.endswith(".csv"):
                df = pl.read_csv(uploaded, low_memory=True)
            elif file_ext.endswith((".xls", ".xlsx")):
                # For Excel files, use pandas with optimized settings
                import pandas as pd
                pandas_df = pd.read_excel(
                    uploaded,
                    engine='openpyxl',
                    dtype=str  # Read all columns as strings initially for faster loading
                )
                df = pl.from_pandas(pandas_df)
            else:
                st.error(f"❌ Unsupported file format: {file_ext}")
                return pl.DataFrame()
            
            # First, convert string columns to Utf8 and clean them
            string_cols = [col for col in df.columns if df[col].dtype == pl.Utf8]
            for col in string_cols:
                df = df.with_columns([
                    pl.col(col).cast(pl.Utf8).map_elements(lambda x: str(x).strip() if x is not None else "").alias(col)
                ])
            
            # Then optimize the schema
            df = df.with_columns([
                pl.col(pl.Float64).cast(pl.Float32),  # Use smaller float type
                pl.col(pl.Int64).cast(pl.Int32)  # Use smaller integer type
            ])
            
            return df
            
        except Exception as e:
            st.error(f"❌ Error reading file {uploaded.name}: {str(e)}")
            return pl.DataFrame()
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return pl.DataFrame()
            
        # Basic validation
        if df.is_empty():
            st.error(f"❌ File {uploaded.name} is empty!")
            return pl.DataFrame()
            
        # Column validation if expected columns provided
        if expected_columns:
            missing_cols = [col for col in expected_columns if col not in df.columns]
            if missing_cols:
                st.error("❌ Missing required columns:")
                st.error(f"Missing: {missing_cols}")
                st.error(f"Available: {df.columns}")
                return pl.DataFrame()
        
        # Handle common data issues
        df = df.with_columns([
            # Handle common string issues
            *[pl.col(col).cast(pl.Utf8).str.strip_chars() 
              for col in df.select(pl.col(pl.Utf8)).columns],
            
            # Handle common numeric issues - replace infinity and null with 0
            *[pl.when(pl.col(col).is_infinite() | pl.col(col).is_null())
              .then(0)
              .otherwise(pl.col(col))
              for col in df.select(pl.col(pl.Float64)).columns]
        ])
        
        return df
        
    except Exception as e:
        st.error(f"❌ Unexpected error processing {uploaded.name}: {str(e)}")
        return pl.DataFrame()

@st.cache_data(ttl=3600)
def clean_style_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and standardize the style master data with enhanced validation and error handling.
    
    Args:
        pl_df: The input Polars DataFrame
        
    Returns:
        pl.DataFrame: The cleaned and standardized dataframe
    """
    try:
        # Start with a copy of the input DataFrame
        cleaned_df = pl_df.clone()
        
        # Required columns with alternative names and default values
        required_cols = {
            "STYLE": {
                "alternatives": ["STYLE", "Style", "Style Code", "Article"],
                "required": True,
                "default": None
            },
            "GENDER": {
                "alternatives": ["GENDER", "Gender", "Department"],
                "required": True,
                "default": "Unknown"
            },
            "Category": {
                "alternatives": ["Category", "Product Category", "Main Category"],
                "required": False,
                "default": "Uncategorized"
            },
            "Neck Type": {
                "alternatives": ["Neck Type", "Neck", "Neckline"],
                "required": False,
                "default": "Regular"
            },
            "Sleeve Type": {
                "alternatives": ["Sleeve Type", "Sleeve", "Sleeve Length"],
                "required": False,
                "default": "Regular"
            },
            "Fabric": {
                "alternatives": ["Fabric", "Material", "Composition"],
                "required": False,
                "default": "Standard"
            },
            "Category Filter": {
                "alternatives": ["Category Filter", "Sub Department", "Filter"],
                "required": False,
                "default": "Standard"
            },
            "Sub Category": {
                "alternatives": ["Sub Category", "Product Type", "Item Type"],
                "required": False,
                "default": "General"
            },
            "Type": {
                "alternatives": ["Type", "Style Type", "Product Group"],
                "required": False,
                "default": "Regular"
            },
            "SEASON": {
                "alternatives": ["SEASON", "Season", "Collection"],
                "required": False,
                "default": "Core"
            }
        }
        
        # Initialize column mapping
        col_mapping = {}
        missing_required_cols = []
        
        # Find matching columns
        for key, config in required_cols.items():
            found = None
            for alt in config["alternatives"]:
                if alt in cleaned_df.columns:
                    found = alt
                    break
            if found:
                col_mapping[key] = found
            elif config["required"]:
                missing_required_cols.append(key)
            else:
                # Add default column for non-required fields
                cleaned_df = cleaned_df.with_columns([
                    pl.lit(config["default"]).alias(key)
                ])
                col_mapping[key] = key
        
        # Report missing required columns
        if missing_required_cols:
            st.error("❌ Missing required columns in Style Master:")
            for col in missing_required_cols:
                st.error(f"- {col} (alternatives: {required_cols[col]['alternatives']})")
            st.error(f"Available columns: {cleaned_df.columns}")
            return pl.DataFrame()
        
        # Data Quality Checks
        quality_issues = []
        
        # Check for null values
        for target_col, source_col in col_mapping.items():
            null_count = cleaned_df[source_col].null_count()
            if null_count > 0:
                quality_issues.append(f"{null_count} null values in {target_col}")
        
        # Check for duplicate styles
        duplicates = (cleaned_df
                     .group_by(col_mapping["STYLE"])
                     .count()
                     .filter(pl.col("count") > 1))
        if not duplicates.is_empty():
            quality_issues.append(f"Found {duplicates.height} duplicate style codes")
        
        # Report quality issues
        if quality_issues:
            st.warning("⚠️ Data quality issues detected:")
            for issue in quality_issues:
                st.warning(f"- {issue}")
        
        try:
            # Clean and standardize the data
            for col in required_cols.keys():
                if col_mapping[col] in cleaned_df.columns:
                    # Enhanced data cleaning with proper null handling and default values
                    cleaned_df = cleaned_df.with_columns([
                        pl.when(
                            pl.col(col_mapping[col]).cast(pl.Utf8).is_null() | 
                            (pl.col(col_mapping[col]).cast(pl.Utf8).str.strip().str.lengths() == 0)
                        )
                        .then(pl.lit(required_cols[col]["default"]))
                        .otherwise(
                            pl.col(col_mapping[col])
                            .cast(pl.Utf8)
                            .map_elements(lambda x: str(x).strip().replace('  ', ' ') if x is not None else '')
                        )
                        .alias(col)
                    ])
            
            # Enhanced data standardization with proper null handling
            cleaned_df = cleaned_df.with_columns([
                # Standardize gender with enhanced mapping
                pl.col("GENDER")
                .map_elements(lambda x: str(x).lower() if x is not None else "")
                .map_elements(lambda x: (
                    "Boys" if any(term in x for term in ["boy", "junior boy", "kid boy"]) else
                    "Girls" if any(term in x for term in ["girl", "junior girl", "kid girl"]) else
                    "Men" if any(term in x for term in ["men", "male", "gent"]) else
                    "Women" if any(term in x for term in ["women", "female", "ladies"]) else
                    "Unisex" if any(term in x for term in ["unisex", "uni", "neutral"]) else
                    "Unknown"
                ))
                .alias("GENDER"),
                
                # Enhanced wear type categorization
                pl.col("Type")
                .str.to_lowercase()
                .map_elements(lambda x: (
                    "Bottom" if any(term in x for term in ["bottom", "pant", "short", "track"]) else
                    "Top" if any(term in x for term in ["top", "tee", "shirt", "jacket", "hoodie"]) else
                    "Accessories" if any(term in x for term in ["cap", "hat", "sock", "bag"]) else
                    "Other"
                ))
                .alias("WEAR_TYPE"),
                
                # Standardize neck type with common variations
                pl.col("Neck Type")
                .str.to_lowercase()
                .map_elements(lambda x: (
                    "Round Neck" if any(term in str(x) for term in ["round", "crew", "regular"]) else
                    "V-Neck" if any(term in str(x) for term in ["v-neck", "v neck", "vneck"]) else
                    "Polo" if any(term in str(x) for term in ["polo", "collar"]) else
                    "High Neck" if any(term in str(x) for term in ["high", "turtle", "mock"]) else
                    "None" if pd.isna(x) or x in ["n/a", "none", ""] else
                    str(x).title()
                ))
                .alias("Neck Type"),
                
                # Standardize sleeve type
                pl.col("Sleeve Type")
                .str.to_lowercase()
                .map_elements(lambda x: (
                    "Short" if any(term in str(x) for term in ["short", "half"]) else
                    "Long" if any(term in str(x) for term in ["long", "full"]) else
                    "Sleeveless" if any(term in str(x) for term in ["sleeveless", "tank", "no sleeve"]) else
                    "None" if pd.isna(x) or x in ["n/a", "none", ""] else
                    str(x).title()
                ))
                .alias("Sleeve Type"),
                
                # Enhanced fabric categorization
                pl.col("Fabric")
                .str.to_lowercase()
                .map_elements(lambda x: (
                    "Cotton" if any(term in str(x) for term in ["cotton", "organic", "combed"]) else
                    "Performance" if any(term in str(x) for term in ["dri-fit", "climacool", "moisture wicking"]) else
                    "Polyester" if any(term in str(x) for term in ["polyester", "poly", "synthetic"]) else
                    "Blend" if any(term in str(x) for term in ["blend", "mixed", "cotton poly"]) else
                    "Other"
                ))
                .alias("FABRIC_TYPE"),
                
                # Season standardization
                pl.col("SEASON")
                .str.to_lowercase()
                .map_elements(lambda x: (
                    "SS" if any(term in str(x) for term in ["ss", "spring", "summer"]) else
                    "AW" if any(term in str(x) for term in ["aw", "autumn", "winter", "fall"]) else
                    "Core" if any(term in str(x) for term in ["core", "basic", "essential"]) else
                    "Unknown"
                ))
                .alias("SEASON")
            ])
            
            # Validation Phase: Business Rules
            validation_warnings = []
            
            # Check for invalid gender-category combinations
            invalid_gender = cleaned_df.filter(~pl.col("GENDER").is_in(["Men", "Women", "Boys", "Girls", "Unisex"]))
            if not invalid_gender.is_empty():
                validation_warnings.append(f"Found {invalid_gender.height} items with invalid gender")
            
            # Check for invalid season assignments
            invalid_season = cleaned_df.filter(~pl.col("SEASON").is_in(["SS", "AW", "Core", "Unknown"]))
            if not invalid_season.is_empty():
                validation_warnings.append(f"Found {invalid_season.height} items with invalid season")
                # Fix invalid seasons
                cleaned_df = cleaned_df.with_columns([
                    pl.when(~pl.col("SEASON").is_in(["SS", "AW", "Core", "Unknown"]))
                    .then("Core")
                    .otherwise(pl.col("SEASON"))
                    .alias("SEASON")
                ])
            
            # Report validation warnings
            if validation_warnings:
                st.warning("⚠️ Data validation warnings:")
                for warning in validation_warnings:
                    st.warning(f"- {warning}")
                st.info("🔧 Applied automatic fixes for data quality issues")
            
            # Remove duplicates if any exist
            cleaned_df = cleaned_df.unique(subset=["STYLE"], keep="first")
            
            # Ensure we have at least the essential data
            if cleaned_df.filter(pl.col("STYLE").is_not_null()).height > 0:
                return cleaned_df
            else:
                st.error("❌ No valid style data after cleaning")
                return pl.DataFrame()
            
        except Exception as e:
            st.error(f"❌ Error during data standardization: {str(e)}")
            st.error("Attempting to return partially cleaned data...")
            if not cleaned_df.is_empty():
                return cleaned_df
            return pl.DataFrame()
            
    except Exception as e:
        st.error(f"❌ Unexpected error in style master cleaning: {str(e)}")
        return pl.DataFrame()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def process_uploaded_files(files_dict):
    """Process multiple uploaded files with progress tracking"""
    results = {}
    
    # Process files in parallel using list comprehension
    items = [(key, file) for key, file in files_dict.items()]
    results = {
        key: read_to_pd(file) if file is not None else pl.DataFrame()
        for key, file in items
    }
    
    return results

def show_sample_data(df: pl.DataFrame, label: str):
    """Display a sample of the data with appropriate cleaning applied."""
    if df.is_empty():
        st.warning(f"⚠️ No data uploaded for {label}")
        return
        
    with st.expander(f"📊 {label} Preview"):
        try:
            # Import required cleaning functions from module
            from data_cleaning import (
                clean_sales_pl, clean_stock_pl, clean_warehouse_pl,
                clean_sku_master_pl, clean_style_master_pl, clean_store_master_pl
            )
            
            # Apply appropriate cleaning function based on label
            cleaned_df = df
            if label == "Sales Data":
                cleaned_df = clean_sales_pl(df)
            elif label == "Stock Data":
                cleaned_df = clean_stock_pl(df)
            elif label == "Warehouse Stock Data":
                cleaned_df = clean_warehouse_pl(df)
            elif label == "SKU Master Data":
                cleaned_df = clean_sku_master_pl(df)
            elif label == "Style Master Data":
                cleaned_df = clean_style_master_pl(df)
            elif label == "Store Master Data":
                cleaned_df = clean_store_master_pl(df)
            
            if cleaned_df.is_empty():
                st.error(f"❌ Error cleaning {label}")
                st.write("Original columns:", ", ".join(df.columns))
                st.write("Please ensure the required columns are present and properly named.")
                return
            
            # Display info for the cleaned data
            cols = st.columns([2, 1])
            with cols[0]:
                st.write(f"Total rows: {len(cleaned_df):,}")
            with cols[1]:
                st.write(f"Total columns: {len(cleaned_df.columns)}")
            
            st.write("Cleaned columns:", ", ".join(cleaned_df.columns))
            st.dataframe(cleaned_df.head(5).to_pandas(), use_container_width=True)
            
        except Exception as e:
            st.error(f"❌ Error processing {label}: {str(e)}")
            st.write("Original Data Preview:")
            st.write("Available columns:", ", ".join(df.columns))
            st.dataframe(df.head(5).to_pandas(), use_container_width=True)

def detect_column(pl_df: pl.DataFrame, candidates: list[str]):
    """
    Enhanced column detection that handles variations in naming conventions
    """
    # Create normalized mapping of actual columns
    norm_map = {}
    for col in pl_df.columns:
        # Normalize: lowercase, strip whitespace, remove special characters
        normalized = col.strip().lower().replace('_', ' ').replace('-', ' ')
        norm_map[normalized] = col
    
    # Try to find matches with normalized candidate names
    for candidate in candidates:
        # Normalize candidate the same way
        norm_candidate = candidate.strip().lower().replace('_', ' ').replace('-', ' ')
        
        # Direct match
        if norm_candidate in norm_map:
            return norm_map[norm_candidate]
        
        # Partial matches for common variations
        for norm_col, actual_col in norm_map.items():
            # Check if candidate is contained in column name or vice versa
            if norm_candidate in norm_col or norm_col in norm_candidate:
                # Additional checks for store-related columns
                if any(store_keyword in norm_candidate for store_keyword in ['store', 'ebo', 'channel']):
                    if any(store_keyword in norm_col for store_keyword in ['store', 'ebo', 'channel', 'shop', 'location']):
                        return actual_col
                # For SKU-related columns        
                elif any(sku_keyword in norm_candidate for sku_keyword in ['sku', 'ean']):
                    if any(sku_keyword in norm_col for sku_keyword in ['sku', 'ean', 'product', 'code', 'id']):
                        return actual_col
                # For quantity-related columns
                elif any(qty_keyword in norm_candidate for qty_keyword in ['quantity', 'qty', 'stock']):
                    if any(qty_keyword in norm_col for qty_keyword in ['quantity', 'qty', 'stock', 'available', 'inventory']):
                        return actual_col
                # For date-related columns
                elif any(date_keyword in norm_candidate for date_keyword in ['date', 'day']):
                    if any(date_keyword in norm_col for date_keyword in ['date', 'day', 'time', 'bill']):
                        return actual_col
                # For size/style/color columns - exact or partial match is fine
                else:
                    return actual_col
    
    return None

def normalize_store_name(store_name: str) -> str:
    """
    Normalize store names to handle variations across different files
    """
    if not store_name or store_name.strip() == "":
        return "UNKNOWN_STORE"
    
    # Clean the input
    cleaned = store_name.strip().upper()
    
    # Remove common prefixes/suffixes that might vary
    cleaned = cleaned.replace("TSPL-", "").replace("-EBO", "").replace("EBO-", "")
    
    # Direct mapping first
    if cleaned in STORE_MAPPING:
        return STORE_MAPPING[cleaned]
    
    # Try original name
    if store_name.strip() in STORE_MAPPING:
        return STORE_MAPPING[store_name.strip()]
    
    # Fuzzy matching for common variations
    for key, value in STORE_MAPPING.items():
        key_clean = key.upper().replace("TSPL-", "").replace("-EBO", "").replace("EBO-", "")
        if key_clean in cleaned or cleaned in key_clean:
            return value
    
    # If no mapping found, return cleaned version with TSPL prefix
    return f"TSPL {cleaned}"

def robust_parse_dates(series_pl: pl.Series) -> pl.Series:
    if series_pl.dtype == pl.Date:
        return series_pl
    s = series_pl.cast(pl.Utf8)
    parsed_pd = pd.to_datetime(s.to_list(), errors="coerce")
    return pl.Series(parsed_pd).cast(pl.Date)

# ------------------------ #
# Data cleaning functions
# ------------------------ #
@st.cache_data(ttl=3600)
def clean_store_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and standardize the store master data with enhanced error handling and validation.
    
    Args:
        pl_df: The input Polars DataFrame
        
    Returns:
        pl.DataFrame: The cleaned and standardized dataframe
        
    This function performs extensive data validation and cleaning:
    1. Required column checking with flexible column naming
    2. Data type validation and conversion
    3. Business rule validation
    4. Intelligent error handling and user feedback
    """
    try:
        # Validation Phase 1: Column Detection
        required_cols = {
            "STORE": ["Store", "store_code", "Store Name", "Store_Code", "EBO", "Location"],
            "MENS": ["Mens", "Men", "Mens_Allow", "Allow_Mens", "Men's"],
            "WOMENS": ["Womens", "Women", "Womens_Allow", "Allow_Womens", "Women's"],
            "BOYS": ["Boys", "Boy", "Boys_Allow", "Allow_Boys", "Boy's"],
            "CAPACITY": ["Capacity", "Store Capacity", "Total Capacity", "Max Capacity", "Store_Cap"]
        }
        
        # Initialize error collection
        validation_errors = []
        found_cols = {}
        
        for key, alternatives in required_cols.items():
            found = None
            for alt in alternatives:
                if alt in pl_df.columns:
                    found = alt
                    break
            if found is None:
                validation_errors.append({
                    "error_type": "missing_column",
                    "column": key,
                    "alternatives": alternatives,
                    "available": pl_df.columns
                })
            else:
                found_cols[key] = found
        
        # Early return if required columns are missing
        if validation_errors:
            for error in validation_errors:
                st.error(f"❌ Could not find {error['column']} column.")
                st.error(f"Expected one of: {error['alternatives']}")
                st.error(f"Available columns: {error['available']}")
            return pl.DataFrame()
        
        # Validation Phase 2: Data Quality Check
        data_issues = []
        
        # Check for null values in key columns
        null_counts = {col: pl_df[found_cols[col]].null_count() for col in ["STORE"]}
        for col, count in null_counts.items():
            if count > 0:
                data_issues.append(f"{count} null values found in {col} column")
        
        # Check for duplicate stores
        duplicate_stores = (pl_df.group_by(found_cols["STORE"])
                          .count()
                          .filter(pl.col("count") > 1))
        if not duplicate_stores.is_empty():
            duplicates = duplicate_stores[found_cols["STORE"]].to_list()
            data_issues.append(f"Duplicate store entries found: {duplicates}")
        
        # Report data quality issues
        if data_issues:
            st.warning("⚠️ Data quality issues found:")
            for issue in data_issues:
                st.warning(f"- {issue}")
        
        # Data Cleaning and Standardization
        try:
            cleaned_df = pl_df.select([
                # Store name standardization with error catching
                pl_df[found_cols["STORE"]]
                .cast(pl.Utf8)
                .map_elements(lambda x: normalize_store_name(x))
                .alias("STORE"),
                
                # Gender allowance with flexible value handling
                pl_df[found_cols["MENS"]]
                .cast(pl.Utf8)
                .str.to_lowercase()
                .map_elements(lambda x: any(val in str(x).lower() for val in ["yes", "y", "true", "1"]))
                .alias("ALLOWS_MENS"),
                
                pl_df[found_cols["WOMENS"]]
                .cast(pl.Utf8)
                .str.to_lowercase()
                .map_elements(lambda x: any(val in str(x).lower() for val in ["yes", "y", "true", "1"]))
                .alias("ALLOWS_WOMENS"),
                
                pl_df[found_cols["BOYS"]]
                .cast(pl.Utf8)
                .str.to_lowercase()
                .map_elements(lambda x: any(val in str(x).lower() for val in ["yes", "y", "true", "1"]))
                .alias("ALLOWS_BOYS"),
                
                # Capacity with intelligent default handling
                pl.coalesce(
                    pl_df[found_cols["CAPACITY"]].cast(pl.Int64),
                    pl.lit(999999)  # Default capacity
                ).map_elements(lambda x: min(max(x, 0), 999999))  # Ensure reasonable range
                .alias("STORE_CAPACITY")
            ])
            
            # Validation Phase 3: Business Rule Validation
            if not cleaned_df.is_empty():
                # Ensure at least one gender is allowed per store
                no_gender_stores = cleaned_df.filter(
                    ~(pl.col("ALLOWS_MENS") | pl.col("ALLOWS_WOMENS") | pl.col("ALLOWS_BOYS"))
                )
                if not no_gender_stores.is_empty():
                    st.warning("⚠️ Found stores with no gender allowances. Setting default to allow all.")
                    cleaned_df = cleaned_df.with_columns([
                        pl.when(
                            ~(pl.col("ALLOWS_MENS") | pl.col("ALLOWS_WOMENS") | pl.col("ALLOWS_BOYS"))
                        ).then(True).otherwise(pl.col("ALLOWS_MENS")).alias("ALLOWS_MENS"),
                        pl.when(
                            ~(pl.col("ALLOWS_MENS") | pl.col("ALLOWS_WOMENS") | pl.col("ALLOWS_BOYS"))
                        ).then(True).otherwise(pl.col("ALLOWS_WOMENS")).alias("ALLOWS_WOMENS"),
                        pl.when(
                            ~(pl.col("ALLOWS_MENS") | pl.col("ALLOWS_WOMENS") | pl.col("ALLOWS_BOYS"))
                        ).then(True).otherwise(pl.col("ALLOWS_BOYS")).alias("ALLOWS_BOYS")
                    ])
                
                # Check for unreasonable capacity values
                low_capacity = cleaned_df.filter(pl.col("STORE_CAPACITY") < 100).height
                if low_capacity > 0:
                    st.warning(f"⚠️ Found {low_capacity} stores with unusually low capacity (<100)")
            
            return cleaned_df
            
        except Exception as e:
            st.error(f"❌ Error during data cleaning: {str(e)}")
            st.error("Available columns: " + ", ".join(pl_df.columns))
            return pl.DataFrame()
            
    except Exception as e:
        st.error(f"❌ Unexpected error in store master cleaning: {str(e)}")
        return pl.DataFrame()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def clean_sales_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and validate sales data with comprehensive error handling and data quality checks.
    
    Args:
        pl_df: Input Polars DataFrame with sales data
        
    Returns:
        pl.DataFrame: Cleaned and validated sales data
        
    This function performs:
    1. Column detection with flexible naming
    2. Data type validation and conversion
    3. Business rule validation
    4. Data quality checks
    5. Outlier detection
    6. Handling of blank/invalid quantities
    """
    try:
        # Initialize error collection
        data_issues = []
        rows_before = pl_df.height
        
        # Phase 1: Column Detection
        column_mappings = {
            "store": {
                "alternatives": ["EBO NAME", "STORE", "store_code", "Channel", "EBO", "Store Name", "Store_Code"],
                "found": None
            },
            "sku": {
                "alternatives": ["SKU", "ean", "EAN", "Product_Code", "SKU_Code", "Article Code"],
                "found": None
            },
            "date": {
                "alternatives": ["BILL_DATE", "DATE", "day", "Date", "Bill_Date", "Transaction_Date"],
                "found": None
            },
            "quantity": {
                "alternatives": ["BILL_QUANTITY", "QTY", "quantity", "Quantity", "Bill_Qty", "Sales_Qty"],
                "found": None
            },
            "style": {
                "alternatives": ["STYLE", "Style_Code", "Article", "Item_Code"],
                "found": None
            }
        }
        
        # Detect columns
        for key, config in column_mappings.items():
            config["found"] = detect_column(pl_df, config["alternatives"])
            if config["found"] is None:
                st.error(f"❌ Could not find {key} column.")
                st.error(f"Expected one of: {config['alternatives']}")
                st.error(f"Available columns: {pl_df.columns}")
                return pl.DataFrame()
        
        try:
            # Phase 2: Data Parsing and Cleaning
            parsed_date = robust_parse_dates(pl_df[column_mappings["date"]["found"]])
            
            # Phase 3: Initial Data Cleaning
            # Create expressions with unique aliases
            store_expr = pl_df[column_mappings["store"]["found"]].cast(pl.Utf8).map_elements(lambda x: normalize_store_name(x)).alias("STORE")
            sku_expr = pl_df[column_mappings["sku"]["found"]].cast(pl.Utf8).str.strip_chars().str.replace_all(r'\s+', '').alias("SKU")
            date_expr = parsed_date.alias("DATE")
            # Handle blank/invalid quantities
            qty_expr = (
                pl.when(pl.col(column_mappings["quantity"]["found"]).cast(pl.Utf8).str.strip() == "")
                .then(None)  # Convert blank strings to None
                .otherwise(
                    pl.col(column_mappings["quantity"]["found"])
                    .cast(pl.Float64)
                )
                .alias("QTY_TEMP")
            )
            
            # Clean the quantities
            cleaned_df = cleaned_df.with_columns([qty_expr])
            # Remove rows with blank/null quantities
            cleaned_df = cleaned_df.filter(pl.col("QTY_TEMP").is_not_null())
            # Final quantity processing
            cleaned_df = cleaned_df.with_columns([
                pl.when(pl.col("QTY_TEMP") < 0)
                .then(0)
                .otherwise(pl.col("QTY_TEMP"))
                .fill_null(0)
                .alias("QTY")
            ]).drop("QTY_TEMP")  # Drop temporary column
            
            cleaned_df = pl_df.select([
                store_expr,
                sku_expr,
                date_expr,
                qty_expr
            ])
            
            # Phase 4: Style Processing
            if column_mappings["style"]["found"]:
                cleaned_df = cleaned_df.with_columns([
                    pl_df[column_mappings["style"]["found"]]
                    .cast(pl.Utf8)
                    .str.strip_chars()
                    .alias("STYLE")
                ])
            else:
                cleaned_df = cleaned_df.with_columns([
                    pl.col("SKU")
                    .str.split("-")
                    .list.get(0)
                    .alias("STYLE")
                ])
            
            # Phase 5: Data Quality Checks
            
            # Check for invalid dates
            future_dates = cleaned_df.filter(pl.col("DATE") > datetime.now()).height
            if future_dates > 0:
                data_issues.append(f"Found {future_dates} transactions with future dates")
            
            # Check for unusual quantities using aggregate operations
            mean_qty = cleaned_df.select(pl.col("QTY").mean()).item()
            std_qty = cleaned_df.select(pl.col("QTY").std()).item()
            
            # Flag unusual quantities (more than 3 standard deviations from mean)
            if mean_qty is not None and std_qty is not None:
                unusual_qty = cleaned_df.filter(
                    pl.col("QTY") > (mean_qty + 3 * std_qty)
                ).height
            else:
                unusual_qty = 0
            
            if unusual_qty > 0:
                data_issues.append(f"Found {unusual_qty} transactions with unusually high quantities")
            
            # Check for duplicate transactions
            duplicates = (
                cleaned_df.group_by(["STORE", "SKU", "DATE", "QTY"])
                .count()
                .filter(pl.col("count") > 1)
            ).height
            
            if duplicates > 0:
                data_issues.append(f"Found {duplicates} potential duplicate transactions")
            
            # Phase 6: Business Rule Validation
            
            # Filter invalid records
            cleaned_df = cleaned_df.filter(
                # Basic data validation
                pl.col("SKU").is_not_null() & 
                (pl.col("SKU") != "") & 
                pl.col("STYLE").is_not_null() &
                (pl.col("STYLE") != "") &
                # Quantity validation
                (pl.col("QTY") >= 0) &
                # Date validation
                (pl.col("DATE").is_not_null())
            )
            
            # Report data quality issues
            if data_issues:
                st.warning("⚠️ Data quality issues detected:")
                for issue in data_issues:
                    st.warning(f"- {issue}")
            
            # Final validation
            if cleaned_df.is_empty():
                st.error("❌ No valid transactions after cleaning!")
                return pl.DataFrame()
            
            # Add metadata columns
            cleaned_df = cleaned_df.with_columns([
                # Flag for high quantity transactions
                (pl.col("QTY") > (mean_qty + 3 * std_qty))
                .alias("IS_UNUSUAL_QTY"),
                
                # Data quality indicator
                pl.lit("VALID").alias("DATA_QUALITY"),
                
                # Processing timestamp
                pl.lit(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                .alias("PROCESSED_AT")
            ])
            
            return cleaned_df
            
        except Exception as e:
            st.error(f"❌ Error during data cleaning: {str(e)}")
            return pl.DataFrame()
            
    except Exception as e:
        st.error(f"❌ Unexpected error in sales data cleaning: {str(e)}")
        return pl.DataFrame()

# ------------------------ #
# Data cleaning functions  #
# ------------------------ #
@st.cache_data(ttl=3600)  # Cache for 1 hour
# Function already defined above

@st.cache_data(ttl=3600)
def clean_warehouse_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    sku_col = detect_column(pl_df, ["Client SKU Id / EAN", "SKU", "Sku", "Row Labels"])
    qty_col = detect_column(pl_df, ["Total Available Quantity", "quantity", "Stock", "Available in EBO"])

    # Check if required columns were found
    if sku_col is None:
        st.error(f"Could not find SKU column. Available columns: {pl_df.columns}")
        st.error("Expected one of: ['Client SKU Id / EAN', 'SKU', 'Sku', 'Row Labels']")
        return pl.DataFrame()
    
    if qty_col is None:
        st.error(f"Could not find quantity column. Available columns: {pl_df.columns}")
        st.error("Expected one of: ['Total Available Quantity', 'quantity', 'Stock', 'Available in EBO']")
        return pl.DataFrame()

    return pl_df.select([
        pl_df[sku_col].cast(pl.Utf8).str.strip_chars().alias("SKU"),
        pl.when(pl.col(qty_col).cast(pl.Float64) < 0).then(0).otherwise(pl.col(qty_col).cast(pl.Float64)).fill_null(0).alias("WAREHOUSE_STOCK")
    ])

def identify_similar_styles(style_code: str) -> dict:
    """
    This function is now deprecated as we use Style Master directly.
    Kept for backwards compatibility.
    """
    return {}

def group_similar_colors(color: str) -> str:
    """
    This function is now deprecated as we use Style Master directly.
    Kept for backwards compatibility.
    """
    return color

@st.cache_data(ttl=3600)
def clean_sku_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    sku_col = detect_column(pl_df, ["SKU", "Sku", "ean", "Row Labels"])
    style_col = detect_column(pl_df, ["STYLE", "Style"])
    colour_col = detect_column(pl_df, ["Colour", "Color"])
    size_col = detect_column(pl_df, ["Size", "SIZE"])

    # Check if required columns were found
    if sku_col is None:
        st.error(f"Could not find SKU column. Available columns: {pl_df.columns}")
        st.error("Expected one of: ['SKU', 'Sku', 'ean', 'Row Labels']")
        return pl.DataFrame()
    
    if style_col is None:
        st.error(f"Could not find Style column. Available columns: {pl_df.columns}")
        st.error("Expected one of: ['STYLE', 'Style']")
        return pl.DataFrame()
    
    if colour_col is None:
        st.error(f"Could not find Colour column. Available columns: {pl_df.columns}")
        st.error("Expected one of: ['Colour', 'Color']")
        return pl.DataFrame()
        
    if size_col is None:
        st.error(f"Could not find Size column. Available columns: {pl_df.columns}")
        st.error("Expected one of: ['Size', 'SIZE']")
        return pl.DataFrame()

    # Start with basic cleaning
    cleaned_df = pl_df.select([
        pl.col(sku_col).cast(pl.Utf8).str.strip_chars().alias("SKU"),
        pl.col(style_col).cast(pl.Utf8).alias("STYLE"),
        pl.col(colour_col).cast(pl.Utf8).alias("Colour"),
        pl.col(size_col).cast(pl.Utf8).alias("Size"),
    ])
    
    # Calculate size range for each style
    cleaned_df = cleaned_df.with_columns([
        pl.col("Size").is_in(["S", "M", "L", "XL", "2XL"]).cast(pl.Int64).alias("IS_REGULAR_SIZE"),
        pl.col("Size").is_in(["3XL", "4XL", "5XL"]).cast(pl.Int64).alias("IS_PLUS_SIZE"),
        pl.col("Size").is_in(["08Y", "10Y", "12Y", "14Y"]).cast(pl.Int64).alias("IS_KIDS_SIZE")
    ])
    
    return cleaned_df

# ------------------------ #
# Replenishment logic functions
# SIZE_SETS with proper groupings for sportswear
SIZE_SETS = [
    ["08Y", "10Y", "12Y", "14Y"],  # Kids sizes
    ["S", "M", "L", "XL", "2XL"],  # Adult sizes  
    ["3XL", "4XL", "5XL"],         # Plus sizes
    ["30", "32", "34", "36", "38"], # Waist sizes
    ["FSE"]                        # Free size
]

def compute_size_set_optimization(df: pl.DataFrame) -> pl.DataFrame:
    """
    🧠 ADVANCED SIZE SET COMPLETION ALGORITHM
    Prioritizes completing size sets for better conversion rates
    """
    try:
        # Use the STYLE_COLOR and SIZE_CODE columns that were already created
        if "STYLE_COLOR" not in df.columns:
            # Fallback: create simple style-color grouping
            df = df.with_columns([
                pl.col("SKU").str.split("-").list.get(0).alias("STYLE_CODE"),
                pl.col("SKU").str.split("-").list.get(1).alias("COLOR_CODE"),
                pl.col("SKU").str.split("-").list.get(-1).alias("SIZE_CODE")
            ])
            df = df.with_columns([
                (pl.col("STYLE_CODE") + "-" + pl.col("COLOR_CODE")).alias("STYLE_COLOR")
            ])
        
        # Calculate size set completeness per store per style-color
        size_set_analysis = df.group_by(["STORE", "STYLE_COLOR"]).agg([
            pl.col("SIZE_CODE").n_unique().alias("AVAILABLE_SIZES"),
            pl.col("DEMAND_STOCK").sum().alias("TOTAL_DEMAND"),  # Use demand instead of replenishment
            pl.col("WEEKLY_AVG").sum().alias("STYLE_WEEKLY_SALES"),
            pl.col("WAREHOUSE_STOCK").sum().alias("STYLE_WAREHOUSE_STOCK")
        ])
        
        # Define optimal size counts per category
        size_set_analysis = size_set_analysis.with_columns([
            pl.when(pl.col("STYLE_COLOR").str.contains("KIDS|KID"))
            .then(7)  # Kids: 08Y to 14Y
            .when(pl.col("STYLE_COLOR").str.contains("PLUS"))
            .then(3)  # Plus: 3XL to 5XL
            .when(pl.col("STYLE_COLOR").str.contains("TRACK|PANT"))
            .then(9)  # Waist: 30 to 38
            .otherwise(5)  # Adult: S to 2XL
            .alias("OPTIMAL_SIZE_COUNT"),
            
            # Size set completion percentage
            (pl.col("AVAILABLE_SIZES") / pl.when(pl.col("STYLE_COLOR").str.contains("KIDS|KID"))
             .then(7).when(pl.col("STYLE_COLOR").str.contains("PLUS"))
             .then(3).when(pl.col("STYLE_COLOR").str.contains("TRACK|PANT"))
             .then(9).otherwise(5) * 100).round(1).alias("COMPLETION_PCT")
        ])
        
        # Join back with main dataframe
        df = df.join(size_set_analysis, on=["STORE", "STYLE_COLOR"], how="left")
        
        # Size set completion bonus
        df = df.with_columns([
            pl.when(pl.col("COMPLETION_PCT") >= 80)
            .then(1.0)  # Complete sets get standard allocation
            .when(pl.col("COMPLETION_PCT") >= 60)
            .then(1.2)  # Near-complete sets get 20% bonus
            .when(pl.col("COMPLETION_PCT") >= 40)
            .then(1.4)  # Partial sets get 40% bonus to complete
            .otherwise(1.6)  # Incomplete sets get 60% bonus
            .alias("SIZE_SET_BONUS")
        ])
        
        return df
        
    except Exception as e:
        st.warning(f"Size set optimization warning: {e}")
        return df.with_columns(pl.lit(1.0).alias("SIZE_SET_BONUS"))


def compute_pivot_availability(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate pivot table availability for size sets
    """
    try:
        return df  # Simplified for now - can be enhanced later
    except Exception as e:
        st.warning(f"Pivot availability warning: {e}")
        return df


def compute_advanced_forecasting(df: pl.DataFrame) -> pl.DataFrame:
    """
    📈 ADVANCED DEMAND FORECASTING with ML-inspired techniques
    """
    try:
        # Exponential smoothing for demand forecasting
        df = df.with_columns([
            # Weighted average favoring recent performance
            (pl.col("RECENT_WEEKLY_AVG") * 0.7 + pl.col("BASE_WEEKLY_AVG") * 0.3).alias("SMOOTHED_DEMAND"),
            
            # Seasonal adjustment (simple day-of-week effect)
            pl.when(pl.lit(True))  # Replace with actual date logic
            .then(1.1)  # Weekend boost
            .otherwise(1.0)
            .alias("SEASONAL_FACTOR"),
            
            # Market penetration potential
            pl.when(pl.col("WEEKS_OF_STOCK") == 0)
            .then(2.0)  # High potential for out-of-stock items
            .when(pl.col("WEEKS_OF_STOCK") < 0.5)
            .then(1.5)  # Medium potential for low stock
            .otherwise(1.0)
            .alias("PENETRATION_FACTOR")
        ])
        
        # Advanced demand calculation using trend-enhanced demand
        df = df.with_columns([
            (pl.col("SMOOTHED_DEMAND") * 
             pl.col("SEASONAL_FACTOR") * 
             pl.col("PENETRATION_FACTOR") * 
             pl.col("SIZE_SET_BONUS")).alias("ADVANCED_DEMAND")
        ])
        
        # Final enhanced demand incorporating trends (if available)
        if "TREND_OPTIMIZED_DEMAND" in df.columns:
            df = df.with_columns([
                pl.max_horizontal(["ADVANCED_DEMAND", "TREND_OPTIMIZED_DEMAND"]).alias("FINAL_ADVANCED_DEMAND")
            ])
        else:
            df = df.with_columns([
                pl.col("ADVANCED_DEMAND").alias("FINAL_ADVANCED_DEMAND")
            ])
        
        return df
        
    except Exception as e:
        st.warning(f"Advanced forecasting warning: {e}")
        return df.with_columns(pl.lit(0).alias("ADVANCED_DEMAND"))
    if df.is_empty():
        return df

    # Create size set mapping with set names
    size_to_set_info = {}
    set_names = ["Kids", "Adult", "Plus", "Waist", "FreeSize"]
    
    for i, (size_set, set_name) in enumerate(zip(SIZE_SETS, set_names)):
        for size in size_set:
            size_to_set_info[size] = {"set_id": i, "set_name": set_name, "set_size": len(size_set)}

    # Add size set information to the dataframe
    df = df.with_columns([
        pl.col("Size").map_elements(lambda x: size_to_set_info.get(x, {"set_id": -1, "set_name": "Individual", "set_size": 1})["set_id"]).alias("size_set_id"),
        pl.col("Size").map_elements(lambda x: size_to_set_info.get(x, {"set_id": -1, "set_name": "Individual", "set_size": 1})["set_name"]).alias("size_set_name"),
        pl.col("Size").map_elements(lambda x: size_to_set_info.get(x, {"set_id": -1, "set_name": "Individual", "set_size": 1})["set_size"]).alias("set_total_sizes")
    ])

    # Calculate availability flags
    df = df.with_columns([
        (pl.col("STORE_STOCK") > 0).cast(pl.Float64).alias("stock_flag"),
        ((pl.col("STORE_STOCK") + pl.col("REPLENISHMENT_STOCK")) > 0).cast(pl.Float64).alias("achieved_flag"),
    ])

    # Calculate pivot availability BEFORE replenishment (by size set within each style-color-store)
    before_avl = (
        df.group_by(["STORE", "STYLE", "Colour", "size_set_id", "set_total_sizes"])
          .agg([
              pl.sum("stock_flag").alias("available_sizes"),
              pl.len().alias("total_sizes_in_data")
          ])
          .with_columns(
              (100 * pl.col("available_sizes") / pl.col("set_total_sizes")).round(2).alias("Pivot_Avl_Before")
          )
    )

    # Calculate pivot availability AFTER replenishment
    after_avl = (
        df.group_by(["STORE", "STYLE", "Colour", "size_set_id", "set_total_sizes"])
          .agg([
              pl.sum("achieved_flag").alias("achieved_sizes"),
              pl.len().alias("total_sizes_in_data")
          ])
          .with_columns(
              (100 * pl.col("achieved_sizes") / pl.col("set_total_sizes")).round(2).alias("Pivot_Avl_After")
          )
    )

    # Join back the pivot availability metrics
    df = (
        df.join(before_avl.select(["STORE", "STYLE", "Colour", "size_set_id", "Pivot_Avl_Before"]),
                on=["STORE", "STYLE", "Colour", "size_set_id"], how="left")
          .join(after_avl.select(["STORE", "STYLE", "Colour", "size_set_id", "Pivot_Avl_After"]),
                on=["STORE", "STYLE", "Colour", "size_set_id"], how="left")
    )

    return df.unique(subset=["STORE", "SKU", "Size"])

def add_remarks(df: pl.DataFrame, sales_pl: pl.DataFrame, latest_date) -> pl.DataFrame:
    # First, clean any null SKUs from sales data
    sales_pl = sales_pl.filter(pl.col("SKU").is_not_null() & (pl.col("SKU") != ""))

    # Calculate pivot-level aggregations for each time period
    sales_30 = (
        sales_pl.filter(pl.col("DATE") >= latest_date - timedelta(days=30))
        .group_by(["STORE", "SKU", "STYLE"])  # Add STYLE for pivot-level context
        .agg([
            pl.col("QTY").sum().alias("Sales_30"),
            pl.col("QTY").count().alias("Transactions_30")
        ])
    )
    
    sales_30_60 = (
        sales_pl.filter(
            (pl.col("DATE") >= latest_date - timedelta(days=60)) & 
            (pl.col("DATE") < latest_date - timedelta(days=30))
        )
        .group_by(["STORE", "SKU", "STYLE"])
        .agg([
            pl.col("QTY").sum().alias("Sales_30_60"),
            pl.col("QTY").count().alias("Transactions_30_60")
        ])
    )
    
    sales_60_90 = (
        sales_pl.filter(
            (pl.col("DATE") >= latest_date - timedelta(days=90)) & 
            (pl.col("DATE") < latest_date - timedelta(days=60))
        )
        .group_by(["STORE", "SKU", "STYLE"])
        .agg([
            pl.col("QTY").sum().alias("Sales_60_90"),
            pl.col("QTY").count().alias("Transactions_60_90")
        ])
    )

    # Calculate total store sales for new store detection
    store_total_sales = (
        sales_pl.filter(pl.col("DATE") >= latest_date - timedelta(days=90))
        .group_by("STORE")
        .agg(pl.col("QTY").sum().alias("Store_Total_90"))
    )

    # Join all sales data
    df = (
        df.join(sales_30, on=["STORE", "SKU"], how="left")
          .join(sales_30_60, on=["STORE", "SKU"], how="left")
          .join(sales_60_90, on=["STORE", "SKU"], how="left")
          .join(store_total_sales, on="STORE", how="left")
    )
    
    # Fill null values with 0
    df = df.with_columns([
        pl.col("Sales_30").fill_null(0),
        pl.col("Sales_30_60").fill_null(0),
        pl.col("Sales_60_90").fill_null(0),
        pl.col("Store_Total_90").fill_null(0),
    ])
    
    # Create Remarks column based on your business logic
    # Use proper when-then-otherwise syntax for Polars
    try:
        df = df.with_columns(
            pl.when(pl.col("Store_Total_90") == 0)
            .then(pl.lit("New Store"))
            .when(
                (pl.col("Sales_30_60") == 0) & 
                (pl.col("Sales_60_90") == 0) & 
                (pl.col("Store_Total_90") > 0)
            )
            .then(pl.lit("New Style"))
            .otherwise(pl.lit("Normal"))
            .alias("Remarks")
        )
    except Exception as e:
        st.error(f"Error creating Remarks column: {e}")
        st.error(f"Available columns: {df.columns}")
        # Create a default Remarks column if there's an error
        df = df.with_columns(pl.lit("Normal").alias("Remarks"))
    
    # Create Trend analysis based on 30, 30-60, 60-90 day sales patterns
    try:
        df = df.with_columns(
            pl.when(
                # No sales in any period
                (pl.col("Sales_30") == 0) & 
                (pl.col("Sales_30_60") == 0) & 
                (pl.col("Sales_60_90") == 0)
            )
            .then(pl.lit("No Sales"))
            .when(
                # Strong uptrend: Sales_30 > Sales_30_60 > Sales_60_90
                (pl.col("Sales_30") > pl.col("Sales_30_60")) & 
                (pl.col("Sales_30_60") >= pl.col("Sales_60_90")) &
                (pl.col("Sales_30") > 0)
            )
            .then(pl.lit("Strong Uptrend"))
            .when(
                # Uptrend: Recent sales better than older periods
                (pl.col("Sales_30") > pl.col("Sales_60_90")) &
                (pl.col("Sales_30") > 0)
            )
            .then(pl.lit("Uptrend"))
            .when(
                # Strong downtrend: Sales_30 < Sales_30_60 < Sales_60_90
                (pl.col("Sales_30") < pl.col("Sales_30_60")) & 
                (pl.col("Sales_30_60") <= pl.col("Sales_60_90")) &
                (pl.col("Sales_60_90") > 0)
            )
            .then(pl.lit("Strong Downtrend"))
            .when(
                # Downtrend: Recent sales worse than older periods
                (pl.col("Sales_30") < pl.col("Sales_60_90")) &
                (pl.col("Sales_60_90") > 0)
            )
            .then(pl.lit("Downtrend"))
            .when(
                # Stable: Sales are consistent across periods (within 20% variance)
                (pl.col("Sales_30") > 0) & 
                (pl.col("Sales_30_60") > 0) & 
                (pl.col("Sales_60_90") > 0) &
                (
                    (pl.col("Sales_30") / pl.col("Sales_30_60")).is_between(0.8, 1.2) |
                    (pl.col("Sales_30") / pl.col("Sales_60_90")).is_between(0.8, 1.2)
                )
            )
            .then(pl.lit("Stable"))
            .when(
                # New Launch: Only recent sales, no historical sales
                (pl.col("Sales_30") > 0) & 
                (pl.col("Sales_30_60") == 0) & 
                (pl.col("Sales_60_90") == 0)
            )
            .then(pl.lit("New Launch"))
            .when(
                # Recovering: Recent sales after a gap
                (pl.col("Sales_30") > 0) & 
                (pl.col("Sales_30_60") == 0) & 
                (pl.col("Sales_60_90") > 0)
            )
            .then(pl.lit("Recovering"))
            .otherwise(pl.lit("Irregular"))
            .alias("Trend")
        )
    except Exception as e:
        st.error(f"Error creating Trend column: {e}")
        # Create a default Trend column if there's an error
        df = df.with_columns(pl.lit("Unknown").alias("Trend"))
    
    # Keep the sales columns as they are useful for analysis
    df = df.drop(["Store_Total_90"])  # Remove only the helper column

    return df

def compute_style_similarity_score(row1, row2) -> float:
    """
    Calculate similarity score between two styles based on their characteristics.
    Returns a score between 0 and 1, where 1 means most similar.
    """
    score = 0.0
    weights = {
        # Primary characteristics (50%)
        "Category": 0.20,  # Category matching is crucial
        "GENDER": 0.20,   # Gender matching is crucial
        "Type": 0.10,     # Type matching is important
        
        # Style details (30%)
        "Neck Type": 0.08,
        "Sleeve Type": 0.08,
        "Fabric": 0.08,
        "Sub Category": 0.06,
        
        # Secondary characteristics (20%)
        "SEASON": 0.10,
        "MRP_Match": 0.05,  # Price point similarity
        "SIZE_SET": 0.05   # Size range match
    }
    
    try:
        # Calculate weighted score for each characteristic
        for field, weight in weights.items():
            if field in ["MRP_Match", "SIZE_SET"]:
                continue  # These are handled separately
                
            # Get values, defaulting to None if field doesn't exist
            val1 = str(row1.get(field, "")).lower().strip()
            val2 = str(row2.get(field, "")).lower().strip()
            
            # Skip empty or invalid values
            if not val1 or not val2 or val1 == "none" or val2 == "none":
                continue
            
            # Text similarity scoring
            if field in ["Category", "Sub Category", "Type"]:
                # Enhanced partial matching with word importance weighting
                words1 = set(val1.split())
                words2 = set(val2.split())
                common_words = words1.intersection(words2)
                
                # Give higher importance to key terms
                key_terms = {"t-shirt", "shirt", "polo", "track", "pant", "short", "jacket", "hoodie"}
                key_matches = sum(1 for word in common_words if word in key_terms)
                
                if common_words:
                    # Base similarity
                    word_similarity = len(common_words) / max(len(words1), len(words2))
                    # Boost for key term matches
                    key_term_boost = (key_matches * 0.1)  # 10% boost per key term match
                    field_score = min(1.0, word_similarity + key_term_boost)
                    score += weight * field_score
            
            # Gender exact match required
            elif field == "GENDER":
                if val1 == val2:
                    score += weight
                    # Small bonus for exact gender match as it's crucial
                    score += 0.05
            
            # Fabric similarity with enhanced grouping
            elif field == "Fabric":
                fabric_groups = {
                    "cotton": ["cotton", "organic", "combed", "cotton blend"],
                    "polyester": ["polyester", "poly", "synthetic", "technical", "moisture wicking"],
                    "blend": ["blend", "mixed", "cotton poly", "poly cotton"],
                    "performance": ["dri-fit", "climacool", "moisture-wicking", "quick dry"],
                    "natural": ["linen", "flax", "wool", "merino", "cashmere"]
                }
                
                def get_fabric_group(val):
                    for group_name, terms in fabric_groups.items():
                        if any(term in val for term in terms):
                            return group_name
                    return "other"
                
                group1 = get_fabric_group(val1)
                group2 = get_fabric_group(val2)
                
                if group1 == group2:
                    score += weight
                    if group1 in ["performance"]:  # Extra weight for matching performance fabrics
                        score += weight * 0.2
                elif group1 in ["cotton", "blend"] and group2 in ["cotton", "blend"]:
                    score += weight * 0.75  # Similar fabric families
            
            # Season match with partial credit for adjacent seasons
            elif field == "SEASON":
                seasons = ["SS", "AW"]  # Simplified season matching
                if val1 == val2:
                    score += weight
                elif val1 in seasons and val2 in seasons:
                    score += weight * 0.5  # Partial match for different seasons
            
            # Style attributes with partial matching
            elif field in ["Neck Type", "Sleeve Type"]:
                if val1 == val2:
                    score += weight
                else:
                    # Group similar attributes
                    similar_groups = {
                        "neck": [
                            ["round", "crew", "crewneck"],
                            ["v-neck", "v neck", "vneck"],
                            ["polo", "collar"],
                            ["high", "mock", "turtleneck"]
                        ],
                        "sleeve": [
                            ["short", "half"],
                            ["long", "full"],
                            ["sleeveless", "tank"],
                            ["raglan", "regular"]
                        ]
                    }
                    
                    groups = similar_groups["neck"] if "neck" in field.lower() else similar_groups["sleeve"]
                    for group in groups:
                        if any(term in val1 for term in group) and any(term in val2 for term in group):
                            score += weight * 0.75
                            break
            
            else:  # Default exact matching for other fields
                if val1 == val2:
                    score += weight

        # Price point similarity
        if "STYLE_MRP" in row1 and "STYLE_MRP" in row2:
            try:
                mrp1 = float(row1["STYLE_MRP"] or 0)
                mrp2 = float(row2["STYLE_MRP"] or 0)
                if mrp1 > 0 and mrp2 > 0:
                    price_diff = abs(mrp1 - mrp2) / max(mrp1, mrp2)
                    # Graduated price similarity scoring
                    if price_diff <= 0.1:  # Within 10%
                        score += weights["MRP_Match"]
                    elif price_diff <= 0.2:  # Within 20%
                        score += weights["MRP_Match"] * 0.75
                    elif price_diff <= 0.3:  # Within 30%
                        score += weights["MRP_Match"] * 0.5
            except (ValueError, TypeError):
                pass
        
        # Size range matching with enhanced logic
        size_fields = ["IS_REGULAR_SIZE", "IS_PLUS_SIZE", "IS_KIDS_SIZE"]
        if all(x in row1 and x in row2 for x in size_fields):
            size_matches = sum(1 for x in size_fields if str(row1.get(x)) == str(row2.get(x)))
            size_similarity = size_matches / len(size_fields)
            score += weights["SIZE_SET"] * size_similarity
            
            # Extra bonus for exact size range match
            if size_matches == len(size_fields):
                score += 0.05  # Small bonus for perfect size range match
        
    except Exception as e:
        return 0.0  # Return 0 score on error
    
    # Final adjustments
    final_score = min(1.0, score)  # Cap at 1.0
    
    # Apply minimum threshold
    if final_score < 0.3:  # If similarity is too low, consider it a non-match
        final_score = 0.0
    
    return final_score

def compute_replenishment(sales_pl, stock_pl, warehouse_pl, sku_master_pl, coverage_weeks, safety_weeks, weeks_back, style_master_pl=None, store_master_pl=None):
    try:
        # Validate input files
        if sales_pl is None or stock_pl is None or warehouse_pl is None or sku_master_pl is None or style_master_pl is None:
            st.error("❌ All files including Style Master are required for computation!")
            return pl.DataFrame()
            
        # Clean all input data
        sales = clean_sales_pl(sales_pl)
        stock = clean_stock_pl(stock_pl)
        warehouse = clean_warehouse_pl(warehouse_pl)
        sku_master = clean_sku_master_pl(sku_master_pl)
        style_info = clean_style_master_pl(style_master_pl)
        
        if store_master_pl is not None:
            store_master = clean_store_master_pl(store_master_pl)
        else:
            store_master = None
            
        # Check if any cleaning failed
        if sales.is_empty() or stock.is_empty() or warehouse.is_empty() or sku_master.is_empty() or style_info.is_empty():
            st.error("❌ Data cleaning failed for one or more inputs!")
            return pl.DataFrame()
            
        st.success("✅ All data cleaned successfully!")
        
        # Continue with the rest of the function...
        # Process the cleaned data
        latest_date = sales["DATE"].max()
        cutoff = latest_date - timedelta(weeks=weeks_back)
        recent_sales = sales.filter(pl.col("DATE") >= cutoff)

        # Calculate store-level performance metrics
        store_analysis = recent_sales.group_by("STORE").agg([
            pl.col("QTY").sum().alias("Total_Sales"),
            pl.col("SKU").n_unique().alias("SKUs"),
            pl.col("STYLE").n_unique().alias("Styles")
        ])

        # Join all the data and calculate replenishment
        result = (recent_sales
                 .join(stock.select(["STORE", "SKU", "STORE_STOCK"]), on=["STORE", "SKU"], how="outer")
                 .join(warehouse.select(["SKU", "WAREHOUSE_STOCK"]), on="SKU", how="left")
                 .join(sku_master, on="SKU", how="left")
                 .join(style_info, on="STYLE", how="left"))

        # Fill null values with 0
        result = result.with_columns([
            pl.col("STORE_STOCK").fill_null(0),
            pl.col("WAREHOUSE_STOCK").fill_null(0),
            pl.col("QTY").fill_null(0)
        ])

        # Calculate weeks of stock and demand
        result = result.with_columns([
            (pl.col("QTY") / weeks_back).alias("WEEKLY_DEMAND"),
            pl.when(pl.col("WEEKLY_DEMAND") > 0)
            .then(pl.col("STORE_STOCK") / (pl.col("QTY") / weeks_back))
            .otherwise(0).alias("WEEKS_OF_STOCK")
        ])

        # Calculate replenishment quantities
        result = result.with_columns([
            pl.col("WEEKLY_DEMAND").mul(coverage_weeks + safety_weeks).alias("TARGET_STOCK"),
            pl.max_horizontal([
                pl.col("TARGET_STOCK") - pl.col("STORE_STOCK"),
                pl.lit(0)
            ]).alias("REPLENISHMENT_STOCK")
        ])

        return result
            
    except Exception as e:
        st.error(f"❌ Error during replenishment computation: {str(e)}")
        return pl.DataFrame()


    # Initialize processing status
    files_processed = {
        "Sales": False,
        "Stock": False,
        "Warehouse": False,
        "SKU Master": False,
        "Style Master": False,
        "Store Master": False
    }
    
    try:
        # Clean sales data
        sales = clean_sales_pl(sales_pl)
        files_processed["Sales"] = not sales.is_empty()
        if sales.is_empty():
            st.warning("⚠️ No valid sales data after cleaning")
        
        # Clean stock data
        stock = clean_stock_pl(stock_pl)
        files_processed["Stock"] = not stock.is_empty()
        if stock.is_empty():
            st.warning("⚠️ No valid stock data after cleaning")
        
        # Clean warehouse data
        warehouse = clean_warehouse_pl(warehouse_pl)
        files_processed["Warehouse"] = not warehouse.is_empty()
        if warehouse.is_empty():
            st.warning("⚠️ No valid warehouse data after cleaning")
        
        # Clean SKU master data
        sku_master = clean_sku_master_pl(sku_master_pl)
        files_processed["SKU Master"] = not sku_master.is_empty()
        if sku_master.is_empty():
            st.warning("⚠️ No valid SKU master data after cleaning")
        
        # Clean style master data
        style_info = clean_style_master_pl(style_master_pl)
        files_processed["Style Master"] = not style_info.is_empty()
        if style_info.is_empty():
            st.warning("⚠️ Style Master data is empty after cleaning")
            
        # Clean store master if provided
        store_master = None
        if store_master_pl is not None and not store_master_pl.is_empty():
            store_master = clean_store_master_pl(store_master_pl)
            files_processed["Store Master"] = not store_master.is_empty()
            if store_master.is_empty():
                st.warning("⚠️ Store Master data is empty after cleaning")
                
        # Check if we have enough data to proceed
        required_files = ["Sales", "Stock", "Warehouse", "SKU Master", "Style Master"]
        missing_files = [file for file in required_files if not files_processed[file]]
        
        if missing_files:
            st.error("❌ Missing required data after cleaning:")
            for file in missing_files:
                st.error(f"- {file}")
            return pl.DataFrame()
            
        st.success("✅ All required files processed successfully")
            
        # Integrate style master data
        required_style_cols = [
            "STYLE",
            "GENDER",
            "Category",
            "Neck Type",
            "Sleeve Type",
            "Fabric",
            "SEASON",
            "Category Filter",
            "Sub Category",
            "Type"
        ]
        
        # Get available columns from style_info
        available_cols = style_info.columns
        join_cols = [col for col in required_style_cols if col in available_cols]
        
        if not join_cols:
            st.error("❌ No valid columns found in Style Master for joining!")
            return pl.DataFrame()
        
        try:
            # First join - basic style information with suffix handling
            style_base = style_info.select(join_cols)
            sku_master = sku_master.join(
                style_base,
                on="STYLE",
                how="left",
                suffix="_style"  # Add suffix to avoid column conflicts
            )
            
            # Rename any suffixed columns back to their original names
            for col in sku_master.columns:
                if col.endswith("_style") and col[:-6] not in sku_master.columns:
                    sku_master = sku_master.rename({col: col[:-6]})
                    
            st.info("✓ Basic style information joined successfully")
            
            # Second join - MRP information if available
            if "MRP" in available_cols:
                mrp_info = (
                    style_info
                    .select(["STYLE", "MRP"])
                    .with_columns(pl.col("MRP").cast(pl.Float64).alias("STYLE_MRP"))
                )
                
                sku_master = sku_master.join(
                    mrp_info,
                    on="STYLE",
                    how="left",
                    suffix="_mrp"  # Add suffix to avoid conflicts
                )
                
                # Rename MRP columns if needed
                for col in sku_master.columns:
                    if col.endswith("_mrp") and col[:-4] not in sku_master.columns:
                        sku_master = sku_master.rename({col: col[:-4]})
                        
                st.info("✓ MRP information joined successfully")
            
            st.success("✨ Style Master integration completed!")
            
        except Exception as e:
            st.error(f"❌ Error during style master integration: {str(e)}")
            return pl.DataFrame()
            
        # Check if any cleaning function returned empty DataFrame due to missing columns
        if sales.is_empty() or stock.is_empty() or warehouse.is_empty() or sku_master.is_empty():
            st.error("❌ Unable to process data due to missing or incorrectly named columns.")
            return pl.DataFrame()
            
    except Exception as e:
        st.error(f"❌ Unexpected error during data processing: {str(e)}")
        return pl.DataFrame()
    if sales.is_empty() or stock.is_empty() or warehouse.is_empty() or sku_master.is_empty():
        st.error("❌ Unable to process data due to missing or incorrectly named columns. Please check the error messages above.")
        return pl.DataFrame()

    latest_date = sales["DATE"].max()
    cutoff = latest_date - timedelta(weeks=weeks_back)
    recent_sales = sales.filter(pl.col("DATE") >= cutoff)

    # ADVANCED: Trend-weighted demand calculation
    # Recent sales get higher weight for trending items
    demand = recent_sales.group_by(["STORE", "SKU"]).agg([
        pl.col("QTY").sum().alias("TOTAL_SALES"),
        (pl.col("QTY").sum() / weeks_back).alias("BASE_WEEKLY_AVG"),
        # Calculate velocity trend within the analysis period
        (pl.col("QTY").tail(int(weeks_back/2)).sum() / (weeks_back/2)).alias("RECENT_WEEKLY_AVG")
    ])
    
    # Adjust weekly average based on velocity trend
    demand = demand.with_columns(
        pl.when(pl.col("RECENT_WEEKLY_AVG") > pl.col("BASE_WEEKLY_AVG") * 1.2)
        .then(pl.col("RECENT_WEEKLY_AVG"))  # Use recent velocity for growing items
        .when(pl.col("RECENT_WEEKLY_AVG") < pl.col("BASE_WEEKLY_AVG") * 0.8)
        .then((pl.col("BASE_WEEKLY_AVG") * 0.9))  # Conservative for declining items
        .otherwise(pl.col("BASE_WEEKLY_AVG"))
        .alias("WEEKLY_AVG")
    )

    # Calculate store performance metrics
    store_performance = recent_sales.group_by("STORE").agg([
        pl.col("QTY").sum().alias("STORE_TOTAL_SALES"),
        pl.col("SKU").n_unique().alias("ACTIVE_SKUS")
    ]).with_columns(
        (pl.col("STORE_TOTAL_SALES") / pl.col("ACTIVE_SKUS")).alias("SALES_PER_SKU")
    )
    
    # Classify stores by performance
    store_performance = store_performance.with_columns(
        pl.when(pl.col("SALES_PER_SKU") >= pl.col("SALES_PER_SKU").quantile(0.8))
        .then(pl.lit("High Velocity"))
        .when(pl.col("SALES_PER_SKU") >= pl.col("SALES_PER_SKU").quantile(0.4))
        .then(pl.lit("Medium Velocity"))
        .otherwise(pl.lit("Low Velocity"))
        .alias("STORE_PERFORMANCE")
    )

    # Process SKU master data with size categorization
    sku_master_enhanced = sku_master.with_columns([
        # Add size categorization
        pl.col("Size").is_in(["S", "M", "L", "XL", "2XL"]).cast(pl.Int64).alias("IS_REGULAR_SIZE"),
        pl.col("Size").is_in(["3XL", "4XL", "5XL"]).cast(pl.Int64).alias("IS_PLUS_SIZE"),
        pl.col("Size").is_in(["08Y", "10Y", "12Y", "14Y"]).cast(pl.Int64).alias("IS_KIDS_SIZE")
    ])

    # Join with stock and SKU master data in specific order
    merged = (demand
             .join(stock, on=["STORE", "SKU"], how="left")
             .with_columns(pl.col("STORE_STOCK").fill_null(0.0))
             .join(sku_master_enhanced, on="SKU", how="left")
             .join(store_performance, on="STORE", how="left"))
    
    # Reorder columns in logical groups
    # 1. Identification columns
    id_cols = ["STORE", "SKU", "STYLE", "Colour", "Size"]
    
    # 2. Store Performance & Status
    store_cols = ["STORE_PERFORMANCE"]  # Remarks and Trend will be added later
    
    # 3. Current Stock Status
    stock_cols = ["STORE_STOCK", "WAREHOUSE_STOCK", "WEEKS_OF_STOCK", "STOCK_FILL_RATE_PCT"]
    
    # 4. Sales Analysis
    sales_cols = ["TOTAL_SALES", "BASE_WEEKLY_AVG", "RECENT_WEEKLY_AVG", "WEEKLY_AVG", 
                  "Sales_30", "Sales_30_60", "Sales_60_90", "MOMENTUM_PCT"]
    
    # 5. Demand Planning
    demand_cols = ["SAFETY_DEMAND", "BASIC_DEMAND", "ADVANCED_DEMAND", "TREND_DEMAND", 
                  "FINAL_ADVANCED_DEMAND", "DEMAND_STOCK"]
    
    # 6. Target & Replenishment
    target_cols = ["BASE_TARGET", "TARGET_STOCK", "REPLENISHMENT_STOCK"]
    
    # 7. Advanced Metrics
    advanced_cols = ["SALES_VOLATILITY", "SAFETY_MULTIPLIER", "VELOCITY_MULTIPLIER", 
                    "SIZE_SET_BONUS", "ALLOCATION_PRIORITY", "BUSINESS_VALUE"]
    
    # Column ordering will be done after adding Remarks and Trend columns

    # Handle new styles with no sales history
    # Get all SKUs from warehouse that aren't in our sales data
    all_warehouse_skus = warehouse.select(["SKU", "WAREHOUSE_STOCK"])
    
    # Create a base DataFrame for new styles
    new_styles = (
        all_warehouse_skus
        .join(sku_master.select(["SKU", "STYLE", "Colour", "Size"]), on="SKU", how="left")
        .filter(pl.col("WAREHOUSE_STOCK") > 0)  # Only consider items with warehouse stock
    )
    
    # Cross join with stores to create entries for each store
    stores_list = store_performance.select("STORE", "STORE_PERFORMANCE").unique()
    new_styles_expanded = new_styles.join(stores_list, how="cross")
    
    # Filter out SKUs that already exist in our merged data
    existing_store_skus = merged.select(["STORE", "SKU"]).unique()
    new_styles_expanded = new_styles_expanded.join(
        existing_store_skus, 
        on=["STORE", "SKU"], 
        how="anti"
    )
    
    # Get schema from merged DataFrame
    merged_schema = {name: dtype for name, dtype in zip(merged.columns, merged.dtypes)}
    
    # Add all required columns with default values to match merged DataFrame
    required_cols = {
        "TOTAL_SALES": pl.lit(0.0).cast(pl.Float64).alias("TOTAL_SALES"),
        "BASE_WEEKLY_AVG": pl.lit(0.0).cast(pl.Float64).alias("BASE_WEEKLY_AVG"),
        "RECENT_WEEKLY_AVG": pl.lit(0.0).cast(pl.Float64).alias("RECENT_WEEKLY_AVG"),
        "WEEKLY_AVG": pl.lit(0.0).cast(pl.Float64).alias("WEEKLY_AVG"),
        "STORE_STOCK": pl.lit(0.0).cast(pl.Float64).alias("STORE_STOCK"),
        "STYLE_STATUS": pl.lit("New Style").cast(pl.Utf8).alias("STYLE_STATUS"),
        "SIMILAR_STYLE_REFERENCE": pl.lit(None).cast(pl.Utf8).alias("SIMILAR_STYLE_REFERENCE"),
        "SIMILARITY_SCORE": pl.lit(None).cast(pl.Float64).alias("SIMILARITY_SCORE"),
        "ALLOCATION_SOURCE": pl.lit("New Style - Pending Similar Style Analysis").cast(pl.Utf8).alias("ALLOCATION_SOURCE"),
        "BASE_TARGET": pl.lit(0.0).cast(pl.Float64).alias("BASE_TARGET"),
        "VELOCITY_MULTIPLIER": pl.lit(1.0).cast(pl.Float64).alias("VELOCITY_MULTIPLIER"),
        "TARGET_STOCK": pl.lit(0.0).cast(pl.Float64).alias("TARGET_STOCK"),
        "DEMAND_STOCK": pl.lit(0.0).cast(pl.Float64).alias("DEMAND_STOCK"),
        "ORIG_WAREHOUSE_STOCK": pl.col("WAREHOUSE_STOCK").cast(pl.Float64),
        "WEEKS_OF_STOCK": pl.lit(0.0).cast(pl.Float64).alias("WEEKS_OF_STOCK"),
        "STOCK_FILL_RATE_PCT": pl.lit(0.0).cast(pl.Float64).alias("STOCK_FILL_RATE_PCT"),
        "MOMENTUM_PCT": pl.lit(0.0).cast(pl.Float64).alias("MOMENTUM_PCT"),
        
        # Size categorization
        "IS_REGULAR_SIZE": pl.col("Size").is_in(["S", "M", "L", "XL", "2XL"]).cast(pl.Int64).alias("IS_REGULAR_SIZE"),
        "IS_PLUS_SIZE": pl.col("Size").is_in(["3XL", "4XL", "5XL"]).cast(pl.Int64).alias("IS_PLUS_SIZE"),
        "IS_KIDS_SIZE": pl.col("Size").is_in(["08Y", "10Y", "12Y", "14Y"]).cast(pl.Int64).alias("IS_KIDS_SIZE")
    }
    
    # Add missing columns to new_styles_expanded
    missing_cols = [col for col in merged.columns if col not in new_styles_expanded.columns]
    if missing_cols:
        new_cols = [required_cols.get(col, pl.lit(None).alias(col)) for col in missing_cols]
        new_styles_expanded = new_styles_expanded.with_columns(new_cols)
    
    if not new_styles_expanded.is_empty():
        # Calculate initial allocation for new styles based on store performance
        new_styles_expanded = new_styles_expanded.with_columns([
            pl.when(pl.col("STORE_PERFORMANCE") == "High Velocity")
            .then(pl.lit(3.0))  # High velocity stores get 3 pieces per size
            .when(pl.col("STORE_PERFORMANCE") == "Medium Velocity")
            .then(pl.lit(2.0))  # Medium velocity stores get 2 pieces per size
            .otherwise(pl.lit(1.0))  # Low velocity stores get 1 piece per size
            .cast(pl.Float64)
            .alias("NEW_STYLE_BASE_ALLOCATION")
        ])
        
        # Ensure columns match exactly with merged DataFrame and cast to correct types
        for col in merged.columns:
            if col in new_styles_expanded.columns:
                target_dtype = merged_schema[col]
                new_styles_expanded = new_styles_expanded.with_columns([
                    pl.col(col).cast(target_dtype)
                ])
        
        # Select columns in the same order as merged DataFrame
        new_styles_expanded = new_styles_expanded.select(merged.columns)
        
        # Combine with existing data
        merged = pl.concat([merged, new_styles_expanded], how="vertical")
    
    # For new styles, find similar existing styles to base allocation on
    if not merged.filter(pl.col("WEEKLY_AVG") == 0).is_empty():
        # Add columns to track new style allocations
        merged = merged.with_columns([
            pl.when(pl.col("WEEKLY_AVG") == 0)
            .then(pl.lit("New Style"))
            .otherwise(pl.lit("Existing Style"))
            .alias("STYLE_STATUS"),
            
            pl.lit(None).cast(pl.Utf8).alias("SIMILAR_STYLE_REFERENCE"),
            pl.lit(None).cast(pl.Float64).alias("SIMILARITY_SCORE"),
            pl.lit(None).cast(pl.Utf8).alias("ALLOCATION_SOURCE")
        ])
        
        # First ensure we have all required columns for style matching
        style_cols = ["STYLE", "GENDER", "Category", 
                     "IS_REGULAR_SIZE", "IS_PLUS_SIZE", "IS_KIDS_SIZE"]
        
        # Add any missing style columns
        for col in style_cols:
            if col not in merged.columns:
                if col == "STYLE_PATTERN":
                    merged = merged.with_columns([
                        pl.col("STYLE").map_elements(lambda x: identify_similar_styles(x).get("pattern", "Unknown")).alias(col)
                    ])
                elif col == "COLOR_GROUP":
                    merged = merged.with_columns([
                        pl.col("Colour").map_elements(group_similar_colors).alias(col)
                    ])
                elif col in ["IS_REGULAR_SIZE", "IS_PLUS_SIZE", "IS_KIDS_SIZE"]:
                    merged = merged.with_columns([
                        pl.lit(0).cast(pl.Int64).alias(col)
                    ])
        
        # Initialize NEW_STYLE_BASE_ALLOCATION with default values based on store performance
        merged = merged.with_columns([
            pl.when(pl.col("STORE_PERFORMANCE") == "High Velocity")
            .then(3.0)
            .when(pl.col("STORE_PERFORMANCE") == "Low Velocity")
            .then(1.0)
            .otherwise(2.0)
            .alias("NEW_STYLE_BASE_ALLOCATION")
        ])
        
        # Initialize similar style metrics
        merged = merged.with_columns([
            pl.lit(0.0).alias("SIMILAR_STYLE_AVG"),
            pl.lit(0.0).alias("MAX_SIMILARITY")
        ])

        # Get performance of similar styles
        new_styles_df = merged.filter(pl.col("WEEKLY_AVG") == 0)
        
        # First initialize default allocations for all stores for new styles
        merged = merged.with_columns([
            pl.when(pl.col("WEEKLY_AVG") == 0)
            .then(
                pl.when(pl.col("STORE_PERFORMANCE") == "High Velocity").then(3.0)
                .when(pl.col("STORE_PERFORMANCE") == "Medium Velocity").then(2.0)
                .otherwise(1.0)
            )
            .alias("NEW_STYLE_BASE_ALLOCATION"),
            
            pl.when(pl.col("WEEKLY_AVG") == 0)
            .then(pl.lit("Pending Similar Style Analysis"))
            .otherwise(pl.col("ALLOCATION_SOURCE"))
            .alias("ALLOCATION_SOURCE")
        ])
        
        # Group and count new styles for summary
        new_style_counts = new_styles_df.select("STYLE").value_counts()
        st.info(f"📊 Processing {new_style_counts.height} new styles")
        
        # Process each unique style
        progress_bar = st.progress(0)
        for idx, new_style in enumerate(new_styles_df.select(style_cols).unique().iter_rows()):
            if new_style[0] is None or str(new_style[0]).strip() == "":
                continue  # Skip invalid styles
                
            # Update progress
            progress_bar.progress((idx + 1) / new_style_counts.height)
            
            # Find similar existing styles with enhanced similarity matching
            existing_styles = merged.filter(
                (pl.col("WEEKLY_AVG") > 0) &  # Only consider styles with sales history
                (pl.col("STYLE") != new_style[0])  # Don't match with self
            )
            
            # Initialize variables for when no similar styles are found
            best_match_style = "No similar style found"
            best_match_score = 0.0
            
            if not existing_styles.is_empty():
                # Prepare comprehensive style comparison
                comparison_fields = [
                    "Category", "GENDER", "Type", "Neck Type", "Sleeve Type", 
                    "Fabric", "Sub Category", "SEASON", "STYLE_MRP",
                    "IS_REGULAR_SIZE", "IS_PLUS_SIZE", "IS_KIDS_SIZE"
                ]
                
                # Create dictionaries for comparison
                new_style_dict = {}
                for i, field in enumerate(style_cols):
                    if i < len(new_style):
                        new_style_dict[field] = new_style[i]
                
                # Calculate similarity scores
                similar_styles = existing_styles.with_columns([
                    pl.struct(comparison_fields).map_elements(
                        lambda x: compute_style_similarity_score(x, new_style_dict)
                    ).alias("SIMILARITY_SCORE")
                ])
                
                # Get weighted average performance of similar styles
                similar_styles = similar_styles.filter(
                    (pl.col("SIMILARITY_SCORE") >= 0.5) &  # Minimum 50% similarity
                    (pl.col("WEEKLY_AVG") > 0)  # Must have sales history
                )
                
                if not similar_styles.is_empty():
                    # Calculate similar style performance per store
                    # Calculate weighted averages for similar styles
                    similar_styles = similar_styles.with_columns([
                        (pl.col("WEEKLY_AVG") * pl.col("SIMILARITY_SCORE")).alias("WEIGHTED_AVG")
                    ])
                    
                    # Aggregate by store for similar style metrics
                    store_metrics = (
                        similar_styles.group_by("STORE")
                        .agg([
                            (pl.col("WEIGHTED_AVG").sum() / pl.col("SIMILARITY_SCORE").sum()).alias("temp_style_avg"),
                            pl.col("SIMILARITY_SCORE").max().alias("temp_max_sim")
                        ])
                    )
                    
                    # Update merged DataFrame with the new metrics
                    merged = merged.join(
                        store_metrics,
                        on="STORE",
                        how="left"
                    ).with_columns([
                        # Replace existing columns with new values for this style
                        pl.when(pl.col("STYLE") == new_style[0])
                        .then(pl.coalesce(pl.col("temp_style_avg"), pl.lit(0.0)))
                        .otherwise(pl.col("SIMILAR_STYLE_AVG"))
                        .alias("SIMILAR_STYLE_AVG"),
                        
                        pl.when(pl.col("STYLE") == new_style[0])
                        .then(pl.coalesce(pl.col("temp_max_sim"), pl.lit(0.0)))
                        .otherwise(pl.col("MAX_SIMILARITY"))
                        .alias("MAX_SIMILARITY")
                    ]).drop(["temp_style_avg", "temp_max_sim"])
                    
                    # Get the best matching similar style for reference
                    best_match = similar_styles.filter(
                        pl.col("SIMILARITY_SCORE") == pl.col("SIMILARITY_SCORE").max()
                    ).limit(1)
                    
                    if not best_match.is_empty():
                        best_match_style = best_match.select("STYLE").row(0)[0]
                        best_match_score = best_match.select("SIMILARITY_SCORE").row(0)[0]
            
            # If no similar styles were found, ensure default values
            if best_match_style is None:
                best_match_style = "No similar style found"
                best_match_score = 0.0
                
                # Update base allocation for new style based on similar styles
                # No need for similar_perf join since SIMILAR_STYLE_AVG is already in merged
                
                # Update base allocation based on similar styles' performance
                merged = merged.with_columns([
                    pl.when((pl.col("STYLE") == new_style[0]) & (pl.col("WEEKLY_AVG") == 0))
                    .then(pl.col("SIMILAR_STYLE_AVG") * 0.8)  # Start with 80% of similar styles' performance
                    .otherwise(pl.col("NEW_STYLE_BASE_ALLOCATION"))  # Keep existing allocation
                    .alias("NEW_STYLE_BASE_ALLOCATION")
                ])
                
                # Then update the tracking columns
                # Update the dataframe with similarity information and allocation
                merged = merged.with_columns([
                    # Initialize SIMILAR_STYLE_REFERENCE if it doesn't exist
                    pl.lit(None).cast(pl.Utf8).alias("SIMILAR_STYLE_REFERENCE"),
                    pl.lit(None).cast(pl.Float64).alias("SIMILARITY_SCORE"),
                    pl.lit(None).cast(pl.Utf8).alias("ALLOCATION_SOURCE")
                ])
                
                # Then update with actual values
                merged = merged.with_columns([
                    # Update similar style reference for the current new style
                    pl.when(pl.col("STYLE") == new_style[0])
                    .then(pl.lit(best_match_style))
                    .otherwise(pl.col("SIMILAR_STYLE_REFERENCE"))
                    .alias("SIMILAR_STYLE_REFERENCE"),
                    
                    # Update similarity score
                    pl.when(pl.col("STYLE") == new_style[0])
                    .then(pl.lit(best_match_score))
                    .otherwise(pl.col("SIMILARITY_SCORE"))
                    .alias("SIMILARITY_SCORE"),
                    
                    # Update allocation source with detailed information
                    pl.when((pl.col("STYLE") == new_style[0]) & (pl.col("WEEKLY_AVG") == 0))
                    .then(
                        pl.when(best_match_score > 0)
                        .then(
                            pl.concat_str([
                                pl.lit(str(best_match_style)),
                                pl.lit(f" - {best_match_score * 100:.1f}% match - "),
                                pl.when(pl.col("STORE_PERFORMANCE") == "High Velocity")
                                .then(pl.lit("High velocity store allocation"))
                                .when(pl.col("STORE_PERFORMANCE") == "Medium Velocity")
                                .then(pl.lit("Medium velocity store allocation"))
                                .otherwise(pl.lit("Low velocity store allocation"))
                            ])
                        )
                        .otherwise(
                            pl.concat_str([
                                pl.lit("New style - "),
                                pl.when(pl.col("STORE_PERFORMANCE") == "High Velocity")
                                .then(pl.lit("High velocity store allocation"))
                                .when(pl.col("STORE_PERFORMANCE") == "Medium Velocity")
                                .then(pl.lit("Medium velocity store allocation"))
                                .otherwise(pl.lit("Low velocity store allocation"))
                            ])
                        )
                    )
                    .otherwise(pl.col("ALLOCATION_SOURCE"))
                    .alias("ALLOCATION_SOURCE")
                ])                # SIMILAR_STYLE_AVG is already in merged DataFrame, no need to join
                
                # Update allocation for new styles based on similar style performance
                merged = merged.with_columns([
                    pl.when((pl.col("STYLE") == new_style[0]) & (pl.col("WEEKLY_AVG") == 0))
                    .then(
                        pl.when(pl.col("SIMILAR_STYLE_AVG") > 0)
                        .then(
                            pl.col("SIMILAR_STYLE_AVG") * 
                            pl.when(pl.col("STORE_PERFORMANCE") == "High Velocity").then(1.2)
                            .when(pl.col("STORE_PERFORMANCE") == "Low Velocity").then(0.8)
                            .otherwise(1.0)
                        )
                        .otherwise(pl.col("NEW_STYLE_BASE_ALLOCATION"))  # Keep existing default allocation
                    )
                    .otherwise(pl.col("NEW_STYLE_BASE_ALLOCATION"))
                    .alias("NEW_STYLE_BASE_ALLOCATION")
                ])

    # First, calculate store performance multipliers
    merged = merged.with_columns([
        # Set default allocation for new styles based on store performance
        pl.when(pl.col("STORE_PERFORMANCE") == "High Velocity")
        .then(3.0)  # High velocity stores get 3 pieces
        .when(pl.col("STORE_PERFORMANCE") == "Low Velocity")
        .then(1.0)  # Low velocity stores get 1 piece
        .otherwise(2.0)  # Medium velocity stores get 2 pieces
        .alias("NEW_STYLE_BASE_ALLOCATION"),
        
        # Store velocity multiplier for existing styles
        pl.when(pl.col("STORE_PERFORMANCE") == "High Velocity")
        .then(pl.lit(1.2))
        .when(pl.col("STORE_PERFORMANCE") == "Low Velocity")
        .then(pl.lit(0.8))
        .otherwise(pl.lit(1.0))
        .alias("VELOCITY_MULTIPLIER")
    ])
    
    # Then calculate target stock
    merged = merged.with_columns([
        pl.when(pl.col("WEEKLY_AVG") == 0)
        .then(pl.col("NEW_STYLE_BASE_ALLOCATION"))
        .otherwise((coverage_weeks + safety_weeks) * pl.col("WEEKLY_AVG").ceil())
        .alias("BASE_TARGET")
    ])

    # Calculate target stock with base target and velocity multiplier
    merged = merged.with_columns([
        (pl.col("BASE_TARGET") * pl.col("VELOCITY_MULTIPLIER")).ceil().alias("TARGET_STOCK")
    ])

    merged = merged.with_columns([
        # Calculate demand: How much we need to reach target stock
        pl.when(pl.col("TARGET_STOCK") - pl.col("STORE_STOCK") < 0)
          .then(0)
          .otherwise(pl.col("TARGET_STOCK") - pl.col("STORE_STOCK"))
          .alias("DEMAND_STOCK"),
          
        # Business KPIs
        pl.when(pl.col("WEEKLY_AVG") > 0)
        .then((pl.col("STORE_STOCK") / pl.col("WEEKLY_AVG")).round(1))
        .otherwise(999)  # High number for non-selling items
        .alias("WEEKS_OF_STOCK"),
        
        # Stock efficiency
        pl.when(pl.col("TARGET_STOCK") > 0)
        .then((pl.col("STORE_STOCK") / pl.col("TARGET_STOCK") * 100).round(1))
        .otherwise(0)
        .alias("STOCK_FILL_RATE_PCT"),
        
        # Sales momentum
        pl.when(pl.col("BASE_WEEKLY_AVG") > 0)
        .then(((pl.col("RECENT_WEEKLY_AVG") / pl.col("BASE_WEEKLY_AVG")) * 100).round(1))
        .otherwise(0)
        .alias("MOMENTUM_PCT")
    ])

    # Join warehouse stock data
    merged = merged.join(warehouse, on="SKU", how="left").with_columns(
        pl.col("WAREHOUSE_STOCK").fill_null(0.0)
    )

    # ADVANCED: Smart allocation prioritizing size set completion
    # 🎯 ADVANCED INTELLIGENT ALLOCATION SYSTEM 🎯
    # Multi-tier optimization with business intelligence
    
    # Step 1: Calculate dynamic safety stock based on sales volatility
    merged = merged.with_columns([
        # Sales coefficient of variation (volatility measure)
        pl.when(pl.col("BASE_WEEKLY_AVG") > 0)
        .then((pl.col("RECENT_WEEKLY_AVG") - pl.col("BASE_WEEKLY_AVG")).abs() / pl.col("BASE_WEEKLY_AVG"))
        .otherwise(0.5)  # Default volatility for new items
        .alias("SALES_VOLATILITY"),
        
        # Dynamic safety factor based on performance and volatility
        pl.when(pl.col("STORE_PERFORMANCE") == "High Velocity")
        .then(1.5)  # Lower safety stock for high-performing stores
        .when(pl.col("STORE_PERFORMANCE") == "Medium Velocity")
        .then(2.0)  # Moderate safety stock
        .otherwise(2.5)  # Higher safety stock for low-performing stores
        .alias("SAFETY_MULTIPLIER")
    ])
    
    # Step 2: Calculate optimized demand with multiple factors (without trend initially)
    merged = merged.with_columns([
        # Base demand with safety stock
        (pl.col("WEEKLY_AVG") * pl.col("SAFETY_MULTIPLIER")).alias("SAFETY_DEMAND"),
        
        # Basic demand (will be enhanced with trends later)
        pl.col("WEEKLY_AVG").alias("BASIC_DEMAND")
    ])
    
    # Step 3: Size set completion prioritization (temporarily simplified)
    try:
        # For now, skip complex parsing and use basic grouping
        merged = merged.with_columns([
            pl.col("SKU").alias("STYLE_COLOR"),  # Use SKU as style-color for now
            pl.lit("UNK").alias("SIZE_CODE")     # Default size
        ])
        st.info("Using simplified size set analysis - can be enhanced later")
    except Exception as e:
        st.warning(f"Size set parsing warning: {e} - using basic allocation")
        merged = merged.with_columns([
            pl.col("SKU").alias("STYLE_COLOR"),  # Fallback
            pl.lit("UNK").alias("SIZE_CODE")
        ])
    
    # Step 4: Smart demand calculation combining available factors
    merged = merged.with_columns([
        # Maximum of safety demand and basic demand (before trend analysis)
        pl.max_horizontal(["SAFETY_DEMAND", "BASIC_DEMAND"]).alias("OPTIMIZED_DEMAND"),
        
        # Store velocity bonus (high performers get priority)
        pl.when(pl.col("STORE_PERFORMANCE") == "High Velocity")
        .then(1.1)  # 10% bonus allocation
        .when(pl.col("STORE_PERFORMANCE") == "Medium Velocity")
        .then(1.0)  # Standard allocation
        .otherwise(0.9)  # 10% reduction for underperformers
        .alias("STORE_BONUS")
    ])
    
    # Step 5: Basic intelligent demand calculation (before trends)
    merged = merged.with_columns([
        (pl.col("OPTIMIZED_DEMAND") * pl.col("STORE_BONUS") * coverage_weeks).ceil().alias("INTELLIGENT_DEMAND")
    ])

    merged = compute_pivot_availability(merged)
    
    # 🔧 ENSURE TREND COLUMN EXISTS (simplified approach)
    try:
        merged = add_remarks(merged, sales, latest_date)
        if "Trend" not in merged.columns:
            st.warning("Trend analysis not available - creating default trend column")
            merged = merged.with_columns(pl.lit("Stable").alias("Trend"))
            
        # Now that we have Remarks and Trend, add them to the column ordering
        ordered_cols = (
            id_cols +
            store_cols +
            ["Remarks", "Trend"] +  # Add these columns here
            stock_cols +
            sales_cols +
            demand_cols +
            target_cols +
            advanced_cols
        )
        
        # Get any remaining columns that might have been missed
        remaining_cols = [col for col in merged.columns if col not in ordered_cols]
        ordered_cols = [col for col in ordered_cols if col in merged.columns]  # Only keep columns that exist
        
        # Reorder the columns
        merged = merged.select(ordered_cols + remaining_cols)
        
    except Exception as e:
        st.error(f"Error in trend analysis: {e} - Using default trend")
        merged = merged.with_columns(pl.lit("Stable").alias("Trend"))
    
    # 🎯 NOW ADD TREND-BASED ENHANCEMENTS (Trend column guaranteed to exist)
    merged = merged.with_columns([
        # Trend-adjusted demand
        pl.when(pl.col("Trend").is_in(["Strong Uptrend"]))
        .then(pl.col("WEEKLY_AVG") * 1.4)  # 40% boost for strong trends
        .when(pl.col("Trend").is_in(["Uptrend"]))
        .then(pl.col("WEEKLY_AVG") * 1.2)  # 20% boost for uptrends
        .when(pl.col("Trend").is_in(["Strong Downtrend"]))
        .then(pl.col("WEEKLY_AVG") * 0.7)  # 30% reduction for declining items
        .when(pl.col("Trend").is_in(["Downtrend"]))
        .then(pl.col("WEEKLY_AVG") * 0.8)  # 20% reduction for declining items
        .otherwise(pl.col("WEEKLY_AVG"))
        .alias("TREND_DEMAND")
    ])
    
    # Update demand with trend analysis
    merged = merged.with_columns([
        # Re-calculate optimized demand with trends
        pl.max_horizontal(["SAFETY_DEMAND", "TREND_DEMAND"]).alias("TREND_OPTIMIZED_DEMAND")
    ])
    
    # 🚀 INTEGRATE ADVANCED ALGORITHMS 🚀
    merged = compute_size_set_optimization(merged)
    merged = compute_advanced_forecasting(merged)
    
    # 🤖 ADVANCED ALLOCATION ENGINE 🤖
    # Priority-based allocation with business rules
    
    # Step 6: Calculate allocation scores for prioritization (Trend column guaranteed)
    merged = merged.with_columns([
        # Size set completion score (higher score = more complete set)
        pl.when(pl.col("Trend").is_in(["Strong Uptrend", "Uptrend"]))
        .then(100)  # High priority for trending items
        .when(pl.col("STORE_PERFORMANCE") == "High Velocity")
        .then(80)   # High priority for good stores
        .when(pl.col("WEEKS_OF_STOCK") < 1.0)
        .then(90)   # High priority for low stock
        .otherwise(50)  # Standard priority
        .alias("ALLOCATION_PRIORITY"),
        
        # Business value score
        (pl.col("WEEKLY_AVG") * pl.col("TARGET_STOCK")).alias("BUSINESS_VALUE")
    ])
    
    # Step 7: Final intelligent replenishment using advanced demand
    merged = merged.with_columns([
        # Use final advanced demand (incorporates all intelligence)
        pl.when(pl.col("FINAL_ADVANCED_DEMAND").is_not_null())
        .then(pl.min_horizontal(["FINAL_ADVANCED_DEMAND", "WAREHOUSE_STOCK"]))
        .otherwise(pl.min_horizontal(["INTELLIGENT_DEMAND", "WAREHOUSE_STOCK"]))
        .alias("CONSTRAINED_ADVANCED_DEMAND")
    ])
    
    # Step 8: Apply minimum order quantity logic
    merged = merged.with_columns([
        # Minimum order quantity (MOQ) logic
        pl.when(pl.col("CONSTRAINED_ADVANCED_DEMAND") > 0)
        .then(pl.max_horizontal([pl.col("CONSTRAINED_ADVANCED_DEMAND"), pl.lit(2)]))  # Minimum 2 pieces
        .otherwise(0)
        .alias("MOQ_ADVANCED_DEMAND")
    ])
    
    # Step 9: Apply store gender restrictions and capacity limits if store master exists
    if store_master is not None:
        # Join store master data with suffix to avoid conflicts
        merged = merged.join(
            store_master,
            on="STORE",
            how="left",
            suffix="_store"  # Add suffix to avoid column conflicts
        ).with_columns([
            # Rename store master columns to standard names if they got suffixed
            *[pl.col(f"{col}_store").alias(col) 
              for col in ["ALLOWS_MENS", "ALLOWS_WOMENS", "ALLOWS_BOYS", "STORE_CAPACITY"] 
              if f"{col}_store" in merged.columns],
            # Default to True if no store master data
            pl.col("ALLOWS_MENS").fill_null(False),
            pl.col("ALLOWS_WOMENS").fill_null(False),
            pl.col("ALLOWS_BOYS").fill_null(False),
            pl.col("STORE_CAPACITY").fill_null(999999)
        ])
        
        # Calculate current total store inventory including pending replenishments
        merged = merged.with_columns([
            pl.col("STORE_STOCK").sum().over("STORE").alias("CURRENT_TOTAL_STOCK")
        ])
        
        # Apply gender restrictions and capacity limits
        merged = merged.with_columns([
            pl.when(
                # Allocate if: store needs stock AND warehouse has inventory AND item has potential
                # AND gender is allowed AND store has capacity
                (pl.col("WEEKS_OF_STOCK") < (coverage_weeks * 0.8)) &  # Stock below 80% of target
                (pl.col("WAREHOUSE_STOCK") > 0) &  # Warehouse has stock
                (pl.col("WEEKLY_AVG") > 0.1) &  # Item has sales potential
                (
                    # Check gender restrictions
                    (
                        (pl.col("GENDER").str.to_lowercase().is_in(["men", "mens"]) & pl.col("ALLOWS_MENS")) |
                        (pl.col("GENDER").str.to_lowercase().is_in(["women", "womens"]) & pl.col("ALLOWS_WOMENS")) |
                        (pl.col("GENDER").str.to_lowercase().is_in(["boy", "boys"]) & pl.col("ALLOWS_BOYS"))
                    )
                ) &
                # Check capacity
                (pl.col("CURRENT_TOTAL_STOCK") + pl.col("MOQ_ADVANCED_DEMAND") <= pl.col("STORE_CAPACITY"))
            )
            .then(pl.col("MOQ_ADVANCED_DEMAND"))
            .otherwise(0)
            .alias("REPLENISHMENT_STOCK")
        ])
    else:
        # If no store master, use original logic
        merged = merged.with_columns([
            pl.when(
                # Allocate if: store needs stock AND warehouse has inventory AND item has potential
                (pl.col("WEEKS_OF_STOCK") < (coverage_weeks * 0.8)) &  # Stock below 80% of target
                (pl.col("WAREHOUSE_STOCK") > 0) &  # Warehouse has stock
                (pl.col("WEEKLY_AVG") > 0.1)  # Item has sales potential
            )
            .then(pl.col("MOQ_ADVANCED_DEMAND"))
            .otherwise(0)
            .alias("REPLENISHMENT_STOCK")
        ])

    return merged

# ------------------------ #
# Streamlit UI
# ------------------------ #
st.set_page_config(
    page_title="TSPL Enterprise Replenishment System", 
    page_icon="🏃‍♂️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS for enterprise look
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        color: #0A192F;
        background-color: #F8F9FA;
    }
    
    /* Main Header */
    .main-header {
        padding: 0.3rem 0.5rem;
        background: #1e3c72;
        margin: -0.5rem -0.5rem 0.5rem -0.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        font-size: 0.9em;
    }
    
    /* Metric Cards */
    .metric-card {
        background: white;
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 4px solid #2a5298;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Enhancement Badges */
    .enhancement-badge {
        background: linear-gradient(135deg, #28a745 0%, #208838 100%);
        color: white;
        padding: 0.25rem 0.6rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin: 0.2rem;
        display: inline-block;
        box-shadow: 0 2px 4px rgba(40, 167, 69, 0.2);
        transition: transform 0.1s ease;
    }
    
    .enhancement-badge:hover {
        transform: scale(1.05);
    }
    
    /* Data Tables */
    .dataframe {
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* Section Headers */
    h1, h2, h3, h4 {
        color: #1e3c72;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    /* Sidebar */
    .css-1d391kg {  /* Sidebar */
        background-color: #F1F3F6;
        padding: 2rem 1rem;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 500;
        transition: transform 0.2s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(42, 82, 152, 0.2);
    }
    
    /* Status Messages */
    .stSuccess {
        background: rgba(40, 167, 69, 0.1);
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 8px;
    }
    
    .stError {
        background: rgba(220, 53, 69, 0.1);
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 8px;
    }
    
    /* File Uploader */
    .stUploader {
        border: 2px dashed #2a5298;
        border-radius: 8px;
        padding: 1rem;
        background: rgba(42, 82, 152, 0.05);
    }
    
    /* Custom Tab Design */
    .stTab {
        background: white;
        border-radius: 8px 8px 0 0;
        border: none;
        box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .stTab[aria-selected="true"] {
        background: #1e3c72;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1 style='font-size: 1.5em; margin: 0;'>Inventory Planning System</h1>
</div>
""", unsafe_allow_html=True)

# Add info about About page
st.markdown("""
<div style="text-align: right; padding: 1rem;">
    <p style="color: #666; font-size: 0.9rem;">
        💡 Check out our new features and system details in the <b>About</b> page!
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

with st.sidebar:
    st.markdown("""
        <div style='padding: 1rem; background: white; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
            <h2 style='color: #1e3c72; font-size: 1.5em; margin-bottom: 1rem;'>📁 Data Upload</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # Create a container for file uploaders
    with st.container():
        st.markdown("""
            <style>
                .file-upload-section {
                    background: white;
                    padding: 1rem;
                    border-radius: 10px;
                    margin: 1rem 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
            </style>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div class='file-upload-section'>", unsafe_allow_html=True)
            sales_file = st.file_uploader(
                "Upload Sales File (Required)", 
                type=["csv","xlsx","xls"], 
                key="sales"
            )
            if sales_file:
                st.success("✅ Sales file uploaded", icon="✨")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='file-upload-section'>", unsafe_allow_html=True)
            warehouse_file = st.file_uploader(
                "Upload Warehouse Stock File (Required)", 
                type=["csv","xlsx","xls"], 
                key="warehouse"
            )
            if warehouse_file:
                st.success("✅ Warehouse file uploaded", icon="📦")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='file-upload-section'>", unsafe_allow_html=True)
            style_master_file = st.file_uploader(
                "Upload Style Master File (Required)", 
                type=["csv","xlsx","xls"], 
                key="style_master"
            )
            if style_master_file:
                st.success("✅ Style master file uploaded", icon="🎨")
            st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='file-upload-section'>", unsafe_allow_html=True)
        stock_file = st.file_uploader(
            "Upload Stock File (Required)", 
            type=["csv","xlsx","xls"], 
            key="stock"
        )
        if stock_file:
            st.success("✅ Stock file uploaded", icon="📊")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='file-upload-section'>", unsafe_allow_html=True)
        sku_master_file = st.file_uploader(
            "Upload SKU Master File (Required)", 
            type=["csv","xlsx","xls"], 
            key="sku_master"
        )
        if sku_master_file:
            st.success("✅ SKU master file uploaded", icon="🏷️")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='file-upload-section'>", unsafe_allow_html=True)
        store_master_file = st.file_uploader(
            "Upload Store Master File (Required)", 
            type=["csv","xlsx","xls"], 
            key="store_master"
        )
        if store_master_file:
            st.success("✅ Store master file uploaded", icon="🏪")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Check for all required files
    st.markdown("<div style='background: white; padding: 1rem; border-radius: 10px; margin-top: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>", unsafe_allow_html=True)
    st.markdown("#### 📋 Upload Status")
    
    required_files = {
        "Sales Data": {"file": sales_file, "icon": "💰"},
        "Stock Data": {"file": stock_file, "icon": "📊"},
        "Warehouse Stock": {"file": warehouse_file, "icon": "📦"},
        "SKU Master": {"file": sku_master_file, "icon": "🏷️"},
        "Style Master": {"file": style_master_file, "icon": "🎨"}
    }
    
    missing_files = [name for name, info in required_files.items() if info["file"] is None]
    
    if missing_files:
        status_color = "#dc3545"  # Red for missing files
        status_icon = "❌"
    else:
        status_color = "#28a745"  # Green for all files present
        status_icon = "✅"
    
    # Display file status with icons and colors
    for file_name, info in required_files.items():
        icon = info["icon"]
        if info["file"] is None:
            st.markdown(f"<div style='color: #dc3545;'>{icon} {file_name}: Missing</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='color: #28a745;'>{icon} {file_name}: Uploaded</div>", unsafe_allow_html=True)
    
    # Overall status message
    if missing_files:
        st.markdown(f"""
            <div style='color: {status_color}; margin-top: 1rem; padding: 0.5rem; border-radius: 5px; background: rgba(220, 53, 69, 0.1);'>
                {status_icon} Missing required files: {', '.join(missing_files)}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style='color: {status_color}; margin-top: 1rem; padding: 0.5rem; border-radius: 5px; background: rgba(40, 167, 69, 0.1);'>
                {status_icon} All required files successfully uploaded!
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

    st.header("⚙️ Business Configuration")
    coverage_weeks = st.number_input("Coverage Weeks", 1, 12, 2, help="Number of weeks of future sales to stock")
    safety_weeks = st.number_input("Safety Buffer Weeks", 0, 12, 1, help="Additional safety stock weeks")
    weeks_back = st.number_input("Analysis Period (Weeks)", 4, 52, 12, help="Historical data to analyze for trends")
    
    st.header("🎯 Advanced Intelligence Options")
    trend_boost = st.slider("Uptrend Item Boost %", 0, 50, 20, help="Extra allocation for trending items")
    velocity_factor = st.checkbox("Apply Store Velocity Factors", True, help="Adjust allocation based on store performance")
    size_set_priority = st.checkbox("Prioritize Size Set Completion", True, help="Focus on completing size ranges")
    
    st.header("🧠 AI Configuration")
    advanced_forecasting = st.checkbox("Advanced Demand Forecasting", True, help="ML-inspired demand prediction")
    seasonal_adjustment = st.checkbox("Seasonal Adjustments", True, help="Account for seasonal patterns")
    market_penetration = st.checkbox("Market Penetration Analysis", True, help="Analyze growth opportunities")
    
    st.header("💼 Business Rules")
    min_allocation = st.number_input("Minimum Allocation", 0, 10, 2, help="Minimum pieces per allocation")
    max_allocation_factor = st.slider("Max Allocation Factor", 1.0, 3.0, 2.0, help="Maximum allocation multiplier")
    
    # Add Clean Data button and Run Replenishment button
    clean_data = st.button("🧹 Clean Data", type="secondary")
    run = st.button("🚀 Generate Intelligent Replenishment Plan", type="primary")

# Initialize session state
if 'cleaned_data' not in st.session_state:
    st.session_state.cleaned_data = None

# Read initial data
sales_pl = read_to_pd(sales_file) if sales_file else pl.DataFrame()
stock_pl = read_to_pd(stock_file) if stock_file else pl.DataFrame()
warehouse_pl = read_to_pd(warehouse_file) if warehouse_file else pl.DataFrame()
sku_master_pl = read_to_pd(sku_master_file) if sku_master_file else pl.DataFrame()
style_master_pl = read_to_pd(style_master_file) if style_master_file else pl.DataFrame()
store_master_pl = read_to_pd(store_master_file) if store_master_file else pl.DataFrame()

# Handle Clean Data button
if clean_data:
    if not all([sales_file, stock_file, warehouse_file, sku_master_file, style_master_file]):
        st.error("❌ Please upload all required files before cleaning data!")
    else:
        with st.spinner("🧹 Cleaning data..."):
            from clean_data_module import clean_all_data
            cleaned_data_dict = clean_all_data(
                sales_pl, stock_pl, warehouse_pl, sku_master_pl,
                style_master_pl, store_master_pl
            )
            st.session_state.cleaned_data = cleaned_data_dict
            if cleaned_data_dict["sales"].is_empty():
                st.error("❌ No valid sales data after cleaning")
            else:
                st.success(f"✅ Successfully cleaned data! Sales records: {cleaned_data_dict['sales'].height:,}")

# Use cleaned data if available
if st.session_state.cleaned_data is not None:
    sales_pl = st.session_state.cleaned_data["sales"]
    stock_pl = st.session_state.cleaned_data["stock"]
    warehouse_pl = st.session_state.cleaned_data["warehouse"]
    sku_master_pl = st.session_state.cleaned_data["sku_master"]
    style_master_pl = st.session_state.cleaned_data["style_master"]
    store_master_pl = st.session_state.cleaned_data["store_master"]

# Enhanced data preview with statistics
col1, col2 = st.columns(2)
with col1:
    st.header("📊 Data Overview")
    if not sales_pl.is_empty():
        st.metric("Sales Records", f"{sales_pl.height:,}")
        st.metric("Date Range", f"{sales_pl.select(pl.col('*')).height} days" if 'DATE' in sales_pl.columns else "Unknown")
    
    if not stock_pl.is_empty():
        st.metric("Stock Records", f"{stock_pl.height:,}")
        
with col2:
    st.header("🏪 Store & SKU Summary") 
    
    # Store Summary
    if not sales_pl.is_empty() and 'STORE' in sales_pl.columns:
        col1, col2, col3 = st.columns(3)
        
        # Store metrics
        with col1:
            unique_stores = sales_pl.select("STORE").unique().height
            st.metric("🏬 Active Stores", f"{unique_stores:,}")
        
        # SKU metrics
        with col2:
            unique_skus = sales_pl.select("SKU").unique().height
            st.metric("👕 Active SKUs", f"{unique_skus:,}")
            
        # Style metrics
        with col3:
            if "STYLE" in sales_pl.columns:
                unique_styles = sales_pl.select("STYLE").unique().height
                st.metric("🎨 Unique Styles", f"{unique_styles:,}")
        
        # Additional store analysis
        if not sales_pl.is_empty():
            store_analysis = (
                sales_pl.group_by("STORE")
                .agg([
                    pl.n_unique("SKU").alias("SKUs"),
                    pl.sum("QTY").round(0).alias("Total_Sales"),  # Round quantities to whole numbers
                    pl.n_unique("STYLE").alias("Styles")
                ])
                .sort("Total_Sales", descending=True)
            )
            
            st.markdown("#### 📊 Store Performance Overview")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Top 5 Stores by Sales Volume:**")
                top_stores = store_analysis.head(5)
                formatted_top = top_stores.with_columns([
                    pl.col("Total_Sales").round(0).cast(pl.Int64).alias("Total_Sales"),  # Ensure whole numbers
                    pl.col("SKUs").cast(pl.Int64).alias("Active_SKUs"),
                    pl.col("Styles").cast(pl.Int64).alias("Active_Styles")
                ])
                st.dataframe(formatted_top, use_container_width=True)
            
            with col2:
                st.markdown("**Store Statistics:**")
                avg_skus = store_analysis.select(pl.col("SKUs").mean().round(1)).item()  # One decimal place
                avg_sales = store_analysis.select(pl.col("Total_Sales").mean().round(0)).item()  # No decimals for sales
                avg_styles = store_analysis.select(pl.col("Styles").mean().round(1)).item()  # One decimal place
                
                metrics_df = pl.DataFrame({
                    "Metric": ["Avg SKUs per Store", "Avg Sales per Store", "Avg Styles per Store"],
                    "Value": [f"{avg_skus:,.1f}", f"{avg_sales:,.0f}", f"{avg_styles:,.1f}"]  # Format with 1 decimal for averages except sales
                })
                st.dataframe(metrics_df, use_container_width=True)

st.header("📋 Sample Data Preview")
show_sample_data(sales_pl, "Sales Data")
show_sample_data(stock_pl, "Stock Data")
show_sample_data(warehouse_pl, "Warehouse Stock Data")
show_sample_data(sku_master_pl, "SKU Master Data")

if run:
    # Check if all required files are present
    if not all([sales_file, stock_file, warehouse_file, sku_master_file, style_master_file]):
        st.error("❌ Please upload all required files before running the computation!")
    else:
        with st.spinner("🧠 Computing Intelligent Replenishment Plan..."):
            style_master_pl = read_to_pd(style_master_file)
            # Read store master if provided
            store_master_pl = read_to_pd(store_master_file) if store_master_file else None
            
            result_pl = compute_replenishment(
                sales_pl, stock_pl, warehouse_pl, sku_master_pl,
                coverage_weeks, safety_weeks, weeks_back,
                style_master_pl, store_master_pl
            )
        if result_pl.is_empty():
            st.warning("No data available for computation.")
        else:
            st.success("🎉 Intelligent Replenishment Plan Generated Successfully!")

            # 📊 BUSINESS INTELLIGENCE DASHBOARD
            result_df = result_pl.to_pandas()
            
            # KPI Dashboard
            col1, col2, col3, col4, col5 = st.columns(5)
            
            total_replenishment = result_df['REPLENISHMENT_STOCK'].sum()
            total_demand = result_df.get('ADVANCED_DEMAND', result_df.get('INTELLIGENT_DEMAND', [0])).sum() if 'ADVANCED_DEMAND' in result_df.columns else 0
            fill_rate = (total_replenishment / total_demand * 100) if total_demand > 0 else 0
            stores_covered = result_df[result_df['REPLENISHMENT_STOCK'] > 0]['STORE'].nunique()
            skus_allocated = result_df[result_df['REPLENISHMENT_STOCK'] > 0]['SKU'].nunique()
            
            with col1:
                st.metric("📦 Total Allocation", f"{total_replenishment:,.0f}", delta="pieces")
            with col2:
                st.metric("🎯 Fill Rate", f"{fill_rate:.1f}%", delta="demand")
            with col3:
                st.metric("🏪 Stores Covered", stores_covered, delta="locations")
            with col4:
                st.metric("👕 SKUs Allocated", skus_allocated, delta="items")
            with col5:
                avg_stock_weeks = result_df['WEEKS_OF_STOCK'].mean() if 'WEEKS_OF_STOCK' in result_df.columns else 0
                st.metric("📅 Avg Stock Weeks", f"{avg_stock_weeks:.1f}", delta="coverage")

            # Enhanced Analytics
            st.markdown("---")
            st.subheader("📈 Advanced Analytics Dashboard")
            
            tab1, tab2, tab3, tab4 = st.tabs(["🎯 Allocation Results", "📊 Performance Analysis", "🧠 Intelligence Insights", "📋 Size Set Analysis"])
            
            with tab1:
                st.markdown("#### Intelligent Allocation Results")
                
                # Show new style summary if present
                new_styles = result_df[result_df['STYLE_STATUS'] == 'New Style'] if 'STYLE_STATUS' in result_df.columns else pd.DataFrame()
                if not new_styles.empty:
                    st.markdown("### 🆕 New Style Allocations")
                    
                    # Style Master Details
                    st.markdown("#### Style Details")
                    style_details = new_styles.groupby('STYLE').agg({
                        'GENDER': 'first',
                        'Category': 'first',
                        'Type': 'first',
                        'STYLE_MRP': 'first'
                    }).reset_index()
                    style_details.columns = ['Style', 'Gender', 'Category', 'Type', 'MRP']
                    st.dataframe(style_details, use_container_width=True)
                    
                    # Allocation Summary
                    st.markdown("#### Allocation Summary")
                    allocation_summary = new_styles.groupby('STYLE').agg({
                        'SIMILAR_STYLE_REFERENCE': 'first',
                        'SIMILARITY_SCORE': 'first',
                        'NEW_STYLE_BASE_ALLOCATION': 'sum',
                        'STORE': 'count',
                        'STORE_PERFORMANCE': lambda x: ', '.join(sorted(x.unique()))
                    }).reset_index()
                    allocation_summary.columns = ['Style', 'Similar Style', 'Match %', 'Total Allocation', 'Store Count', 'Store Types']
                    allocation_summary['Match %'] = (allocation_summary['Match %'] * 100).round(1)
                    allocation_summary = allocation_summary.sort_values('Total Allocation', ascending=False)
                    st.dataframe(allocation_summary, use_container_width=True)
                    
                    # Store-wise Details
                    st.markdown("#### Store-wise Allocation Details")
                    store_details = new_styles.groupby(['STYLE', 'STORE', 'STORE_PERFORMANCE']).agg({
                        'NEW_STYLE_BASE_ALLOCATION': 'sum',
                        'ALLOCATION_SOURCE': 'first'
                    }).reset_index()
                    store_details.columns = ['Style', 'Store', 'Store Performance', 'Allocation Qty', 'Allocation Basis']
                    store_details = store_details.sort_values(['Style', 'Store Performance', 'Store'])
                    st.dataframe(store_details, use_container_width=True)
                    
                    # Summary Metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("New Styles", f"{len(style_details)}")
                    with col2:
                        avg_stores = allocation_summary['Store Count'].mean()
                        st.metric("Avg Stores per Style", f"{avg_stores:.1f}")
                    with col3:
                        avg_allocation = allocation_summary['Total Allocation'].mean()
                        st.metric("Avg Total Allocation", f"{avg_allocation:.0f}")
                    with col4:
                        avg_match = allocation_summary['Match %'].mean()
                        st.metric("Avg Style Match %", f"{avg_match:.1f}%")
                
                # AgGrid display with enhanced formatting and column groups
                gb = GridOptionsBuilder.from_dataframe(result_df)
                gb.configure_default_column(editable=False, groupable=True, sortable=True)
                
                # Configure column groups with appropriate formatting
                # 1. Identification columns
                for col in ["STORE", "SKU", "STYLE", "Colour", "Size", "STYLE_STATUS"]:
                    if col in result_df.columns:
                        gb.configure_column(col, header_name=f"📍 {col}")
                
                # 2. Store Performance & Status
                for col in ["STORE_PERFORMANCE", "Remarks", "Trend"]:
                    if col in result_df.columns:
                        gb.configure_column(col, header_name=f"📊 {col}")
                
                # 3. Current Stock Status
                for col in ["STORE_STOCK", "WAREHOUSE_STOCK", "WEEKS_OF_STOCK", "STOCK_FILL_RATE_PCT"]:
                    if col in result_df.columns:
                        gb.configure_column(col, type=["numericColumn"], 
                                         precision=1 if "PCT" in col or "WEEKS" in col else 0,
                                         header_name=f"📦 {col}")
                
                # 4. Sales Analysis
                sales_cols = ["TOTAL_SALES", "BASE_WEEKLY_AVG", "RECENT_WEEKLY_AVG", "WEEKLY_AVG", 
                            "Sales_30", "Sales_30_60", "Sales_60_90", "MOMENTUM_PCT"]
                for col in sales_cols:
                    if col in result_df.columns:
                        gb.configure_column(col, type=["numericColumn"], 
                                         precision=2 if "AVG" in col or "PCT" in col else 0,
                                         header_name=f"💰 {col}")
                
                # 5. Demand Planning
                demand_cols = ["SAFETY_DEMAND", "BASIC_DEMAND", "ADVANCED_DEMAND", "TREND_DEMAND", 
                             "FINAL_ADVANCED_DEMAND", "DEMAND_STOCK"]
                for col in demand_cols:
                    if col in result_df.columns:
                        gb.configure_column(col, type=["numericColumn"], precision=1,
                                         header_name=f"📈 {col}")
                
                # 6. Target & Replenishment
                for col in ["BASE_TARGET", "TARGET_STOCK", "REPLENISHMENT_STOCK"]:
                    if col in result_df.columns:
                        gb.configure_column(col, type=["numericColumn"], precision=0,
                                         header_name=f"🎯 {col}")
                
                # 7. Advanced Metrics
                advanced_cols = ["SALES_VOLATILITY", "SAFETY_MULTIPLIER", "VELOCITY_MULTIPLIER", 
                               "SIZE_SET_BONUS", "ALLOCATION_PRIORITY", "BUSINESS_VALUE"]
                for col in advanced_cols:
                    if col in result_df.columns:
                        gb.configure_column(col, type=["numericColumn"], precision=2,
                                         header_name=f"🧠 {col}")
                
                grid_options = gb.build()
                
                # Display the grid with increased height for better visibility
                AgGrid(result_df, 
                      gridOptions=grid_options, 
                      enable_enterprise_modules=False, 
                      height=600,
                      theme='balham')  # Using a clean theme for better readability
            
            with tab2:
                st.markdown("#### Store Performance Analysis")
                if 'STORE_PERFORMANCE' in result_df.columns:
                    perf_summary = result_df.groupby('STORE_PERFORMANCE').agg({
                        'REPLENISHMENT_STOCK': 'sum',
                        'STORE': 'nunique'
                    }).reset_index()
                    st.dataframe(perf_summary, use_container_width=True)
                
                # Trend analysis
                if 'Trend' in result_df.columns:
                    st.markdown("#### Trend Distribution")
                    trend_summary = result_df.groupby('Trend').agg({
                        'REPLENISHMENT_STOCK': 'sum',
                        'SKU': 'nunique'
                    }).reset_index()
                    st.dataframe(trend_summary, use_container_width=True)
            
            with tab3:
                st.markdown("#### AI Intelligence Insights")
                
                # Size set analysis
                if 'SIZE_SET_BONUS' in result_df.columns:
                    st.markdown("**Size Set Completion Optimization Active** ✅")
                    avg_bonus = result_df['SIZE_SET_BONUS'].mean()
                    st.info(f"Average Size Set Bonus Applied: {avg_bonus:.2f}x")
                
                # Advanced forecasting
                if 'ADVANCED_DEMAND' in result_df.columns:
                    st.markdown("**Advanced Demand Forecasting Active** ✅")
                    forecast_accuracy = result_df['ADVANCED_DEMAND'].corr(result_df['WEEKLY_AVG'])
                    st.info(f"Forecast-Sales Correlation: {forecast_accuracy:.3f}")
                
                # Business rules applied
                st.markdown("**Business Intelligence Applied:**")
                st.write("• ✅ Dynamic Safety Stock Calculation")
                st.write("• ✅ Store Performance-Based Allocation")
                st.write("• ✅ Trend-Weighted Demand Calculation")
                st.write("• ✅ Size Set Completion Priority")
                st.write("• ✅ Market Penetration Analysis")
                st.write("• ✅ Minimum Order Quantity Logic")
            
            with tab4:
                st.markdown("#### Size Set Analysis")
                if 'COMPLETION_PCT' in result_df.columns:
                    completion_summary = result_df.groupby('STORE').agg({
                        'COMPLETION_PCT': 'mean',
                        'AVAILABLE_SIZES': 'mean',
                        'OPTIMAL_SIZE_COUNT': 'mean'
                    }).reset_index()
                    st.dataframe(completion_summary, use_container_width=True)
                else:
                    st.info("Size set analysis data not available in current results.")

            # Excel download with enhanced formatting and data dictionary
            st.markdown("---")
            output = BytesIO()
            
            # Create a dictionary of column descriptions
            column_info = {
                # Identification columns
                "STORE": {
                    "Description": "Store identifier",
                    "Calculation": "Normalized from input data using STORE_MAPPING dictionary",
                    "Purpose": "Uniquely identifies each store location",
                    "Business Value": "Enables store-level analysis and allocation"
                },
                "SKU": {
                    "Description": "Stock Keeping Unit",
                    "Calculation": "Direct from SKU master, normalized format",
                    "Purpose": "Unique identifier for each product variant (style-color-size combination)",
                    "Business Value": "Enables tracking at the most granular product level"
                },
                "STYLE": {
                    "Description": "Style code",
                    "Calculation": "Extracted from SKU or Style Master",
                    "Purpose": "Groups related SKUs of the same design",
                    "Business Value": "Allows style-level analysis and allocation decisions"
                },
                "STYLE_STATUS": {
                    "Description": "Indicates if style is new or existing",
                    "Calculation": "New Style if no sales history, Existing Style otherwise",
                    "Purpose": "Identifies new styles for special handling",
                    "Business Value": "Helps manage new style introduction and allocation"
                },
                
                # Performance Metrics
                "STORE_PERFORMANCE": {
                    "Description": "Store velocity classification",
                    "Calculation": "Based on sales per SKU relative to other stores (High/Medium/Low Velocity)",
                    "Purpose": "Categorizes stores by sales performance",
                    "Business Value": "Enables differentiated allocation strategies by store performance"
                },
                "WEEKLY_AVG": {
                    "Description": "Average weekly sales",
                    "Calculation": "Total sales divided by number of weeks, with trend weighting",
                    "Purpose": "Baseline for demand calculation",
                    "Business Value": "Core metric for replenishment quantity calculation"
                },
                
                # Stock Status
                "STORE_STOCK": {
                    "Description": "Current store inventory",
                    "Calculation": "Direct from stock file",
                    "Purpose": "Current available stock in store",
                    "Business Value": "Base for calculating replenishment need"
                },
                "WAREHOUSE_STOCK": {
                    "Description": "Available warehouse stock",
                    "Calculation": "Direct from warehouse file",
                    "Purpose": "Available stock for replenishment",
                    "Business Value": "Constraints and enables replenishment decisions"
                },
                
                # Advanced Metrics
                "WEEKS_OF_STOCK": {
                    "Description": "Inventory coverage in weeks",
                    "Calculation": "STORE_STOCK / WEEKLY_AVG",
                    "Purpose": "Shows how long current stock will last",
                    "Business Value": "Key metric for stock health assessment"
                },
                "STOCK_FILL_RATE_PCT": {
                    "Description": "Stock level vs target percentage",
                    "Calculation": "(STORE_STOCK / TARGET_STOCK) * 100",
                    "Purpose": "Shows how close to target stock levels",
                    "Business Value": "Indicates stock position relative to ideal"
                },
                
                # Similar Style Analysis
                "SIMILAR_STYLE_REFERENCE": {
                    "Description": "Reference style code for new styles",
                    "Calculation": "Based on style similarity scoring",
                    "Purpose": "Identifies comparable style for new products",
                    "Business Value": "Guides new style allocation based on similar products"
                },
                "SIMILARITY_SCORE": {
                    "Description": "Similarity percentage to reference style",
                    "Calculation": "Weighted match across multiple style attributes",
                    "Purpose": "Quantifies similarity between styles",
                    "Business Value": "Indicates confidence in similar style comparison"
                },
                
                # Sales Analysis
                "MOMENTUM_PCT": {
                    "Description": "Sales trend indicator",
                    "Calculation": "(RECENT_WEEKLY_AVG / BASE_WEEKLY_AVG) * 100",
                    "Purpose": "Shows sales trajectory",
                    "Business Value": "Identifies growing or declining products"
                },
                "Sales_30": {
                    "Description": "Sales in last 30 days",
                    "Calculation": "Sum of sales quantity in last 30 days",
                    "Purpose": "Recent sales performance",
                    "Business Value": "Short-term sales trend indicator"
                },
                
                # Demand Planning
                "SAFETY_DEMAND": {
                    "Description": "Safety stock demand",
                    "Calculation": "WEEKLY_AVG * SAFETY_MULTIPLIER",
                    "Purpose": "Buffer stock requirement",
                    "Business Value": "Prevents stockouts and service level issues"
                },
                "ADVANCED_DEMAND": {
                    "Description": "AI-enhanced demand forecast",
                    "Calculation": "Combines multiple demand signals with ML enhancement",
                    "Purpose": "Smart demand prediction",
                    "Business Value": "More accurate demand forecasting"
                },
                
                # Allocation Strategy
                "TARGET_STOCK": {
                    "Description": "Ideal stock level",
                    "Calculation": "Based on coverage weeks and enhanced with store performance",
                    "Purpose": "Sets target inventory level",
                    "Business Value": "Optimal stock level balancing sales and inventory"
                },
                "REPLENISHMENT_STOCK": {
                    "Description": "Quantity to replenish",
                    "Calculation": "Complex calculation considering multiple factors",
                    "Purpose": "Final replenishment quantity",
                    "Business Value": "Actionable replenishment quantity"
                },
                
                # Size Set Analysis
                "SIZE_SET_BONUS": {
                    "Description": "Size set completion multiplier",
                    "Calculation": "Based on current size set completeness",
                    "Purpose": "Encourages complete size sets",
                    "Business Value": "Improves sales through better size availability"
                }
            }
            
            # Convert column info to DataFrame
            info_rows = []
            for col, details in column_info.items():
                info_rows.append({
                    "Column Name": col,
                    "Description": details["Description"],
                    "Calculation Method": details["Calculation"],
                    "Purpose": details["Purpose"],
                    "Business Value": details["Business Value"]
                })
            
            data_dictionary = pl.DataFrame(info_rows)
            
            try:
                # Create Excel writer with two sheets
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Convert result_pl to pandas and write main data
                    result_df = result_pl.to_pandas()
                    result_df.to_excel(writer, sheet_name="Replenishment Data", index=False)
                    
                    # Write data dictionary
                    data_dictionary.to_pandas().to_excel(writer, sheet_name="Data Dictionary", index=False)
                
                output.seek(0)
                st.download_button(
                    "Download Replenishment Excel (with Data Dictionary)",
                    data=output.getvalue(),
                    file_name="replenishment_output.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error saving Excel file: {str(e)}")
                # Try saving just the main data without the data dictionary
                try:
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        result_pl.to_pandas().to_excel(writer, sheet_name="Replenishment Data", index=False)
                    
                    output.seek(0)
                    st.download_button(
                        "Download Replenishment Data (without Data Dictionary)",
                        data=output.getvalue(),
                        file_name="replenishment_output.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e2:
                    st.error(f"Error saving simplified Excel file: {str(e2)}")
                    # Last resort: Save as CSV
                    try:
                        output = BytesIO()
                        result_pl.write_csv(output)
                        output.seek(0)
                        st.download_button(
                            "Download as CSV (fallback option)",
                            data=output.getvalue(),
                            file_name="replenishment_output.csv",
                            mime="text/csv"
                        )
                    except Exception as e3:
                        st.error(f"Error saving CSV file: {str(e3)}")
                        st.error("Unable to save file in any format. Please contact support.")
                