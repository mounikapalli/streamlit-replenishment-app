import polars as pl
import streamlit as st

def clean_style_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and standardize style master data with enhanced validation.
    """
    try:
        initial_rows = pl_df.height
        data_issues = []

        # Required columns with defaults and validation rules
        required_cols = {
            "STYLE": {
                "alternatives": ["STYLE", "Style", "Style Code"],
                "required": True,
                "default": None,
                "allow_blank": False
            },
            "GENDER": {
                "alternatives": ["GENDER", "Gender", "Department"],
                "required": True,
                "default": "Unisex",
                "valid_values": ["Men", "Women", "Boys", "Girls", "Unisex"]
            },
            "Category": {
                "alternatives": ["Category", "Product Category"],
                "required": False,
                "default": "Uncategorized"
            },
            "Neck Type": {
                "alternatives": ["Neck Type", "Neck", "Neckline"],
                "required": False,
                "default": "Regular"
            },
            "Sleeve Type": {
                "alternatives": ["Sleeve Type", "Sleeve"],
                "required": False,
                "default": "Regular"
            },
            "Fabric": {
                "alternatives": ["Fabric", "Material"],
                "required": False,
                "default": "Standard"
            },
            "SEASON": {
                "alternatives": ["SEASON", "Season"],
                "required": False,
                "default": "Core",
                "valid_values": ["SS", "AW", "Core"]
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
            elif config.get("required", False):
                missing_required.append(key)
            else:
                # Add default column for non-required fields
                pl_df = pl_df.with_columns(pl.lit(config["default"]).alias(key))
                col_mapping[key] = key

        if missing_required:
            st.error("❌ Missing required columns:")
            for col in missing_required:
                st.error(f"- {col} (alternatives: {required_cols[col]['alternatives']})")
            return pl.DataFrame()

        # Clean and validate data
        cleaned_df = pl_df.clone()
        
        for col, config in required_cols.items():
            if col in col_mapping:
                # Basic cleaning
                cleaned_df = cleaned_df.with_columns([
                    pl.when(
                        pl.col(col_mapping[col]).is_null() | 
                        (pl.col(col_mapping[col]).cast(pl.Utf8).str.strip() == "")
                    )
                    .then(pl.lit(config.get("default", "")))
                    .otherwise(
                        pl.col(col_mapping[col])
                        .cast(pl.Utf8)
                        .map_elements(lambda x: str(x).strip().title() if x is not None else "")
                    )
                    .alias(col)
                ])

                # Validate values if specified
                if "valid_values" in config:
                    invalid_count = cleaned_df.filter(
                        ~pl.col(col).is_in(config["valid_values"])
                    ).height
                    
                    if invalid_count > 0:
                        msg = f"Found {invalid_count} invalid values in {col}"
                        data_issues.append(msg)
                        # Correct invalid values
                        cleaned_df = cleaned_df.with_columns([
                            pl.when(~pl.col(col).is_in(config["valid_values"]))
                            .then(pl.lit(config["default"]))
                            .otherwise(pl.col(col))
                            .alias(col)
                        ])

                # Check for nulls
                null_count = cleaned_df[col].null_count()
                if null_count > 0:
                    msg = f"{null_count} null values in {col}"
                    data_issues.append(msg)

        # Remove duplicates
        duplicates = (
            cleaned_df
            .group_by("STYLE")
            .count()
            .filter(pl.col("count") > 1)
        ).height

        if duplicates > 0:
            msg = f"Found {duplicates} duplicate style codes"
            data_issues.append(msg)
            # Keep first occurrence of duplicates
            cleaned_df = cleaned_df.unique(subset=["STYLE"], keep="first")

        # Standardize gender values
        cleaned_df = cleaned_df.with_columns([
            pl.col("GENDER")
            .map_elements(lambda x: x.title() if x is not None else "Unisex")
            .map_elements(lambda x: (
                "Men" if x in ["Mens", "Male", "M"] else
                "Women" if x in ["Womens", "Female", "W", "Ladies"] else
                "Boys" if x in ["Boy", "Junior Boy", "Kids Boy"] else
                "Girls" if x in ["Girl", "Junior Girl", "Kids Girl"] else
                "Unisex" if x in ["Uni", "Universal", "Common"] else x
            ))
            .alias("GENDER")
        ])

        # Report issues
        if data_issues:
            st.warning("⚠️ Data quality issues detected:")
            for issue in data_issues:
                st.warning(f"- {issue}")
            st.info("🔧 Applied automatic fixes for data quality issues")

        return cleaned_df

    except Exception as e:
        st.error(f"❌ Error in style master cleaning: {str(e)}")
        return pl.DataFrame()