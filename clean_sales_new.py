import polars as pl
import streamlit as st
from datetime import datetime, timedelta

def normalize_store_name(store_name: str) -> str:
    """Normalize store names (existing function)"""
    # Copy your existing normalize_store_name function here
    pass

def robust_parse_dates(series_pl: pl.Series) -> pl.Series:
    """Parse dates (existing function)"""
    # Copy your existing robust_parse_dates function here
    pass

def clean_sales_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and validate sales data with comprehensive error handling and data quality checks.
    Now includes proper handling of blank quantities.
    
    Args:
        pl_df: Input Polars DataFrame with sales data
        
    Returns:
        pl.DataFrame: Cleaned and validated sales data
    """
    try:
        # Initialize error collection and track rows
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
            for alt in config["alternatives"]:
                if alt in pl_df.columns:
                    config["found"] = alt
                    break
            if config["found"] is None:
                st.error(f"❌ Could not find {key} column.")
                st.error(f"Expected one of: {config['alternatives']}")
                st.error(f"Available columns: {pl_df.columns}")
                return pl.DataFrame()
        
        try:
            # Phase 2: Initial cleaning and validation
            cleaned_df = pl_df.with_columns([
                # Convert quantities to string and clean
                pl.col(column_mappings["quantity"]["found"])
                .cast(pl.Utf8)
                .str.strip()
                .alias("QTY_TEMP_STR"),
                
                # Clean store names
                pl.col(column_mappings["store"]["found"])
                .cast(pl.Utf8)
                .map_elements(lambda x: normalize_store_name(x))
                .alias("STORE"),
                
                # Clean SKUs
                pl.col(column_mappings["sku"]["found"])
                .cast(pl.Utf8)
                .str.strip_chars()
                .str.replace_all(r'\s+', '')
                .alias("SKU"),
                
                # Parse dates
                robust_parse_dates(pl_df[column_mappings["date"]["found"]])
                .alias("DATE")
            ])
            
            # Remove rows with blank or invalid quantities
            cleaned_df = cleaned_df.filter(
                (pl.col("QTY_TEMP_STR") != "") & 
                (pl.col("QTY_TEMP_STR").is_not_null())
            )
            
            # Report on removed rows
            rows_removed = rows_before - cleaned_df.height
            if rows_removed > 0:
                msg = f"⚠️ Removed {rows_removed:,} rows with blank or invalid quantities"
                st.warning(msg)
                data_issues.append(msg)
            
            # Convert valid quantities to numeric and clean
            cleaned_df = cleaned_df.with_columns([
                pl.col("QTY_TEMP_STR")
                .cast(pl.Float64)
                .map_elements(lambda x: max(0, float(x)) if x is not None else 0)
                .alias("QTY")
            ]).drop("QTY_TEMP_STR")
            
            # Add STYLE column if found
            if column_mappings["style"]["found"]:
                cleaned_df = cleaned_df.with_columns([
                    pl.col(column_mappings["style"]["found"])
                    .cast(pl.Utf8)
                    .str.strip_chars()
                    .alias("STYLE")
                ])
            else:
                # Extract STYLE from SKU if not found
                cleaned_df = cleaned_df.with_columns([
                    pl.col("SKU")
                    .str.split("-")
                    .list.get(0)
                    .alias("STYLE")
                ])
            
            # Phase 3: Data Quality Checks
            # Check for invalid dates
            future_dates = cleaned_df.filter(pl.col("DATE") > datetime.now()).height
            if future_dates > 0:
                msg = f"Found {future_dates} transactions with future dates"
                data_issues.append(msg)
            
            # Check for unusual quantities
            mean_qty = cleaned_df.select(pl.col("QTY").mean()).item()
            std_qty = cleaned_df.select(pl.col("QTY").std()).item()
            
            if mean_qty is not None and std_qty is not None:
                unusual_qty = cleaned_df.filter(
                    pl.col("QTY") > (mean_qty + 3 * std_qty)
                ).height
                
                if unusual_qty > 0:
                    msg = f"Found {unusual_qty} transactions with unusually high quantities"
                    data_issues.append(msg)
            
            # Check for duplicate transactions
            duplicates = (
                cleaned_df.group_by(["STORE", "SKU", "DATE", "QTY"])
                .count()
                .filter(pl.col("count") > 1)
            ).height
            
            if duplicates > 0:
                msg = f"Found {duplicates} potential duplicate transactions"
                data_issues.append(msg)
            
            # Report data quality issues
            if data_issues:
                st.warning("⚠️ Data quality issues detected:")
                for issue in data_issues:
                    st.warning(f"- {issue}")
            
            # Final validation - ensure we have valid data
            if cleaned_df.is_empty():
                st.error("❌ No valid transactions after cleaning!")
                return pl.DataFrame()
            
            return cleaned_df
            
        except Exception as e:
            st.error(f"❌ Error during data cleaning: {str(e)}")
            return pl.DataFrame()
            
    except Exception as e:
        st.error(f"❌ Unexpected error in sales data cleaning: {str(e)}")
        return pl.DataFrame()