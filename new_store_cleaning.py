import polars as pl
import streamlit as st

def clean_store_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and standardize store master data with enhanced error handling.
    """
    if pl_df is None or pl_df.is_empty():
        st.error("❌ No data provided to clean_store_master_pl")
        return pl.DataFrame()
        
    try:
        # Required columns with flexible mapping
        required_cols = {
            "STORE": {
                "alternatives": ["Store", "store_code", "Store Name", "Store_Code", "EBO", "Location"],
                "required": True,
                "default": None,
                "allow_blank": False
            },
            "ALLOWS_MENS": {
                "alternatives": ["Mens", "Men", "Mens_Allow", "Allow_Mens", "Men's"],
                "required": False,
                "default": True,
                "type": "boolean"
            },
            "ALLOWS_WOMENS": {
                "alternatives": ["Womens", "Women", "Womens_Allow", "Allow_Womens", "Women's"],
                "required": False,
                "default": True,
                "type": "boolean"
            },
            "ALLOWS_BOYS": {
                "alternatives": ["Boys", "Boy", "Boys_Allow", "Allow_Boys", "Boy's"],
                "required": False,
                "default": True,
                "type": "boolean"
            },
            "STORE_CAPACITY": {
                "alternatives": ["Capacity", "Store Capacity", "Total Capacity", "Max Capacity", "Store_Cap"],
                "required": False,
                "default": 999999,
                "type": "numeric",
                "min_value": 0,
                "max_value": 999999
            }
        }

        # Find matching columns
        col_mapping = {}
        missing_required = []
        
        try:
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
                st.error("❌ Missing required columns in Store Master:")
                for col in missing_required:
                    st.error(f"- {col} (alternatives: {required_cols[col]['alternatives']})")
                    st.error(f"Available columns: {pl_df.columns}")
                return pl.DataFrame()
                
        except Exception as e:
            st.error(f"❌ Error mapping store columns: {str(e)}")
            return pl.DataFrame()

        try:
            # Data cleaning and validation
            cleaned_df = pl_df.clone()
            
            # Clean store names and standardize them
            cleaned_df = cleaned_df.with_columns([
                pl.col(col_mapping["STORE"])
                .cast(pl.Utf8)
                .map_elements(lambda x: normalize_store_name(x) if x is not None else "UNKNOWN_STORE")
                .alias("STORE")
            ])
            
            # Clean boolean columns (gender allowances)
            boolean_fields = ["ALLOWS_MENS", "ALLOWS_WOMENS", "ALLOWS_BOYS"]
            for field in boolean_fields:
                if field in col_mapping:
                    cleaned_df = cleaned_df.with_columns([
                        pl.col(col_mapping[field])
                        .cast(pl.Utf8)
                        .str.to_lowercase()
                        .map_elements(lambda x: any(val in str(x).lower() 
                                                  for val in ["yes", "y", "true", "1", "allow"]))
                        .fill_null(True)  # Default to allowing all genders
                        .alias(field)
                    ])
                else:
                    # If column wasn't found, add it with default value
                    cleaned_df = cleaned_df.with_columns(pl.lit(True).alias(field))
            
            # Clean and validate capacity
            if "STORE_CAPACITY" in col_mapping:
                cleaned_df = cleaned_df.with_columns([
                    pl.coalesce(
                        pl.col(col_mapping["STORE_CAPACITY"]).cast(pl.Int64),
                        pl.lit(999999)
                    )
                    .map_elements(lambda x: min(max(x, 0), 999999))  # Clamp to valid range
                    .alias("STORE_CAPACITY")
                ])
            else:
                cleaned_df = cleaned_df.with_columns(pl.lit(999999).alias("STORE_CAPACITY"))
            
            # Check for stores with no gender allowances
            no_gender_stores = cleaned_df.filter(
                ~(pl.col("ALLOWS_MENS") | pl.col("ALLOWS_WOMENS") | pl.col("ALLOWS_BOYS"))
            )
            
            if not no_gender_stores.is_empty():
                st.warning(f"⚠️ Found {no_gender_stores.height} stores with no gender allowances")
                st.info("🔧 Setting these stores to allow all genders by default")
                
                cleaned_df = cleaned_df.with_columns([
                    pl.when(
                        ~(pl.col("ALLOWS_MENS") | pl.col("ALLOWS_WOMENS") | pl.col("ALLOWS_BOYS"))
                    ).then(pl.lit(True)).otherwise(pl.col("ALLOWS_MENS")).alias("ALLOWS_MENS"),
                    
                    pl.when(
                        ~(pl.col("ALLOWS_MENS") | pl.col("ALLOWS_WOMENS") | pl.col("ALLOWS_BOYS"))
                    ).then(pl.lit(True)).otherwise(pl.col("ALLOWS_WOMENS")).alias("ALLOWS_WOMENS"),
                    
                    pl.when(
                        ~(pl.col("ALLOWS_MENS") | pl.col("ALLOWS_WOMENS") | pl.col("ALLOWS_BOYS"))
                    ).then(pl.lit(True)).otherwise(pl.col("ALLOWS_BOYS")).alias("ALLOWS_BOYS")
                ])
            
            # Check for unreasonable capacities
            low_capacity = cleaned_df.filter(pl.col("STORE_CAPACITY") < 100).height
            if low_capacity > 0:
                st.warning(f"⚠️ Found {low_capacity} stores with unusually low capacity (<100)")
            
            # Check for duplicate stores
            duplicates = (
                cleaned_df.group_by("STORE")
                .len()  # Using len instead of count as per warning
                .filter(pl.col("count") > 1)
            ).height
            
            if duplicates > 0:
                st.warning(f"⚠️ Found {duplicates} duplicate store entries")
                st.info("🔧 Keeping first occurrence of each store")
                cleaned_df = cleaned_df.unique(subset=["STORE"], keep="first")
            
            return cleaned_df
            
        except Exception as e:
            st.error(f"❌ Error cleaning store data: {str(e)}")
            return pl.DataFrame()

    except Exception as e:
        st.error(f"❌ Unexpected error in store master cleaning: {str(e)}")
        return pl.DataFrame()