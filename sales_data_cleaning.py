import polars as pl
import streamlit as st
from datetime import datetime

def clean_sales_data_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and standardize sales data with enhanced validation and blank quantity removal.
    """
    try:
        initial_rows = pl_df.height
        data_issues = []

        # Required columns with defaults and validation rules
        required_cols = {
            "BILL_QUANTITY": {
                "alternatives": ["BILL_QUANTITY", "Bill Quantity", "Quantity"],
                "required": True,
                "numeric": True,
                "min_value": 0
            },
            "STYLE": {
                "alternatives": ["STYLE", "Style", "Style Code"],
                "required": True,
                "allow_blank": False
            },
            "STORE": {
                "alternatives": ["STORE", "Store", "Store Name"],
                "required": True,
                "allow_blank": False
            },
            "DATE": {
                "alternatives": ["DATE", "BILL_DATE", "Bill Date", "Sales Date"],
                "required": True,
                "datetime": True
            }
        }

        # Find matching columns
        col_mapping = {}
        missing_required = []
        
        for key, config in required_cols.items():
            found = None
            for alt in config["alternatives"]:
                if alt in pl_df.columns:
                    found = alt
                    break
            
            if found:
                col_mapping[key] = found
            else:
                missing_required.append(key)

        if missing_required:
            st.error("❌ Missing required columns:")
            for col in missing_required:
                st.error(f"- {col} (alternatives: {required_cols[col]['alternatives']})")
            return pl.DataFrame()

        # Start cleaning with a clone
        cleaned_df = pl_df.clone()

        # Clean and validate BILL_QUANTITY
        cleaned_df = cleaned_df.with_columns([
            pl.col(col_mapping["BILL_QUANTITY"])
            .cast(pl.Float64)
            .alias("BILL_QUANTITY")
        ])

        # Remove rows with null, zero, or negative quantities
        invalid_qty = cleaned_df.filter(
            pl.col("BILL_QUANTITY").is_null() | 
            (pl.col("BILL_QUANTITY") <= 0)
        ).height

        if invalid_qty > 0:
            msg = f"Removed {invalid_qty} rows with invalid quantities (null, zero, or negative)"
            data_issues.append(msg)
            
        cleaned_df = cleaned_df.filter(
            ~pl.col("BILL_QUANTITY").is_null() & 
            (pl.col("BILL_QUANTITY") > 0)
        )

        # Clean STYLE codes
        cleaned_df = cleaned_df.with_columns([
            pl.col(col_mapping["STYLE"])
            .cast(pl.Utf8)
            .map_elements(lambda x: str(x).strip().upper() if x is not None else "")
            .alias("STYLE")
        ])

        # Remove rows with blank styles
        blank_styles = cleaned_df.filter(pl.col("STYLE") == "").height
        if blank_styles > 0:
            msg = f"Removed {blank_styles} rows with blank style codes"
            data_issues.append(msg)
            cleaned_df = cleaned_df.filter(pl.col("STYLE") != "")

        # Clean store names
        cleaned_df = cleaned_df.with_columns([
            pl.col(col_mapping["STORE"])
            .cast(pl.Utf8)
            .map_elements(lambda x: str(x).strip().title() if x is not None else "")
            .alias("STORE")
        ])

        # Remove rows with blank stores
        blank_stores = cleaned_df.filter(pl.col("STORE") == "").height
        if blank_stores > 0:
            msg = f"Removed {blank_stores} rows with blank store names"
            data_issues.append(msg)
            cleaned_df = cleaned_df.filter(pl.col("STORE") != "")

        # Clean and validate dates
        cleaned_df = cleaned_df.with_columns([
            pl.col(col_mapping["DATE"])
            .str.strptime(pl.Date, "%Y-%m-%d %H:%M:%S", strict=False)
            .alias("DATE")
        ])

        # Remove rows with invalid dates
        invalid_dates = cleaned_df.filter(pl.col("DATE").is_null()).height
        if invalid_dates > 0:
            msg = f"Removed {invalid_dates} rows with invalid dates"
            data_issues.append(msg)
            cleaned_df = cleaned_df.filter(~pl.col("DATE").is_null())

        # Report cleaning summary
        rows_removed = initial_rows - cleaned_df.height
        if rows_removed > 0:
            pct_removed = (rows_removed / initial_rows) * 100
            st.warning(
                f"⚠️ Removed {rows_removed} rows ({pct_removed:.1f}%) with invalid data:"
            )
            for issue in data_issues:
                st.warning(f"- {issue}")

        if cleaned_df.height == 0:
            st.error("❌ No valid rows remained after cleaning!")
            return pl.DataFrame()

        return cleaned_df

    except Exception as e:
        st.error(f"❌ Error in sales cleaning: {str(e)}")
        return pl.DataFrame()