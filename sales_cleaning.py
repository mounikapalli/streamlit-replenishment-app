import polars as pl
import streamlit as st
from datetime import datetime

def clean_sales_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean sales data with enhanced validation and error handling.
    """
    try:
        # Track initial row count
        initial_rows = pl_df.height
        data_issues = []

        # Column Detection
        column_mappings = {
            "store": ["EBO NAME", "STORE", "store_code", "Channel", "EBO", "Store Name"],
            "sku": ["SKU", "ean", "EAN", "Product_Code", "SKU_Code"],
            "date": ["BILL_DATE", "DATE", "day", "Date", "Bill_Date"],
            "quantity": ["BILL_QUANTITY", "QTY", "quantity", "Quantity", "Bill_Qty"]
        }

        # Find columns
        found_cols = {}
        for key, alternatives in column_mappings.items():
            found = None
            for alt in alternatives:
                if alt in pl_df.columns:
                    found = alt
                    break
            if found is None:
                st.error(f"❌ Missing {key} column. Expected one of: {alternatives}")
                st.error(f"Available columns: {pl_df.columns}")
                return pl.DataFrame()
            found_cols[key] = found

        try:
            # Clean data with proper null handling
            cleaned_df = pl_df.with_columns([
                # Clean store names
                pl.col(found_cols["store"])
                .cast(pl.Utf8)
                .map_elements(lambda x: str(x).strip() if x is not None else "")
                .alias("STORE_TEMP"),

                # Clean SKUs
                pl.col(found_cols["sku"])
                .cast(pl.Utf8)
                .map_elements(lambda x: str(x).strip().replace(' ', '') if x is not None else "")
                .alias("SKU"),

                # Clean quantities - first as strings for validation
                pl.col(found_cols["quantity"])
                .cast(pl.Utf8)
                .map_elements(lambda x: str(x).strip() if x is not None else "")
                .alias("QTY_STR")
            ])

            # Remove invalid data
            cleaned_df = cleaned_df.filter(
                (pl.col("STORE_TEMP") != "") &
                (pl.col("SKU") != "") &
                (pl.col("QTY_STR") != "")
            )

            # Convert quantities to numeric
            cleaned_df = cleaned_df.with_columns([
                pl.col("QTY_STR")
                .map_elements(lambda x: float(x) if x.replace('.', '').isdigit() else None)
                .cast(pl.Float64)
                .map_elements(lambda x: max(0, x) if x is not None else None)
                .alias("QTY")
            ])

            # Remove rows with null quantities
            cleaned_df = cleaned_df.filter(pl.col("QTY").is_not_null())

            # Report removed rows
            rows_removed = initial_rows - cleaned_df.height
            if rows_removed > 0:
                msg = f"Removed {rows_removed} rows with invalid or blank data"
                st.warning(f"⚠️ {msg}")
                data_issues.append(msg)

            # Parse dates
            try:
                cleaned_df = cleaned_df.with_columns([
                    pl.col(found_cols["date"])
                    .cast(pl.Date)
                    .alias("DATE")
                ])
            except Exception as e:
                st.error(f"❌ Error parsing dates: {str(e)}")
                return pl.DataFrame()

            # Remove future dates
            future_dates = cleaned_df.filter(pl.col("DATE") > datetime.now()).height
            if future_dates > 0:
                cleaned_df = cleaned_df.filter(pl.col("DATE") <= datetime.now())
                msg = f"Removed {future_dates} transactions with future dates"
                data_issues.append(msg)

            # Final cleanup and column selection
            cleaned_df = cleaned_df.select([
                "STORE_TEMP",
                "SKU",
                "DATE",
                "QTY"
            ]).rename({"STORE_TEMP": "STORE"})

            # Report data quality issues
            if data_issues:
                st.warning("⚠️ Data quality issues found:")
                for issue in data_issues:
                    st.warning(f"- {issue}")

            if cleaned_df.is_empty():
                st.error("❌ No valid data after cleaning")
                return pl.DataFrame()

            return cleaned_df

        except Exception as e:
            st.error(f"❌ Error during data cleaning: {str(e)}")
            return pl.DataFrame()

    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return pl.DataFrame()