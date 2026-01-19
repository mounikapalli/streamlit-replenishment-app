import polars as pl
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def read_to_pd(uploaded, force_csv=False, expected_columns=None):
    """
    Safely read data from uploaded file to Polars DataFrame with validation.
    Uses caching to improve performance on repeated reads.
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

def show_sample_data(df: pl.DataFrame, label: str):
    """
    Show a preview of the dataframe with basic statistics.
    """
    if not df.is_empty():
        with st.expander(f"📊 {label} Preview"):
            cols = st.columns([2, 1])
            with cols[0]:
                st.write(f"Total rows: {len(df):,}")
            with cols[1]:
                st.write(f"Total columns: {len(df.columns)}")
            st.dataframe(df.head(5).to_pandas(), use_container_width=True)
    else:
        st.warning(f"⚠️ No data uploaded for {label}")

def detect_column(pl_df: pl.DataFrame, candidates: list[str]) -> str:
    """
    Enhanced column detection that handles variations in naming conventions.
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
    Normalize store names to handle variations across different files.
    """
    if not store_name or store_name.strip() == "":
        return "UNKNOWN_STORE"
    
    # Clean the input
    cleaned = store_name.strip().upper()
    
    # Store mapping for data normalization across different files
    STORE_MAPPING = {
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