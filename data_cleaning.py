import polars as pl
import streamlit as st
from datetime import datetime

def normalize_store_name(store_name: str) -> str:
    """
    Normalize store names to handle variations across different files
    """
    if not store_name or store_name.strip() == "":
        return "UNKNOWN_STORE"
    
    cleaned = store_name.strip().upper()
    return f"TSPL {cleaned}"

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
                "default": "Core"
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

        # Basic cleaning of all string columns
        for col in col_mapping.values():
            cleaned_df = cleaned_df.with_columns([
                pl.col(col)
                .cast(pl.Utf8)
                .map_elements(lambda x: str(x).strip() if x is not None else "")
                .alias(col)
            ])
        
        # Handle defaults and validation for each column
        for col, config in required_cols.items():
            source_col = col_mapping[col]
            cleaned_df = cleaned_df.with_columns([
                pl.when(
                    (pl.col(source_col) == "") | pl.col(source_col).is_null()
                )
                .then(pl.lit(config["default"]))
                .otherwise(pl.col(source_col))
                .alias(col)
            ])
            
            # Validate values if specified
            if "valid_values" in config:
                invalid_count = cleaned_df.filter(
                    ~pl.col(col).is_in(config["valid_values"])
                ).height
                if invalid_count > 0:
                    data_issues.append(f"Found {invalid_count} invalid values in {col}")
                    cleaned_df = cleaned_df.with_columns([
                        pl.when(~pl.col(col).is_in(config["valid_values"]))
                        .then(pl.lit(config["default"]))
                        .otherwise(pl.col(col))
                        .alias(col)
                    ])

        # Remove duplicates
        duplicates = cleaned_df.group_by("STYLE").count().filter(pl.col("count") > 1).height
        if duplicates > 0:
            data_issues.append(f"Found {duplicates} duplicate style codes")
            cleaned_df = cleaned_df.unique(subset=["STYLE"], keep="first")

        # Report data quality issues
        if data_issues:
            st.warning("⚠️ Data quality issues detected:")
            for issue in data_issues:
                st.warning(f"- {issue}")

        return cleaned_df

    except Exception as e:
        st.error(f"❌ Error in style master cleaning: {str(e)}")
        return pl.DataFrame()

def clean_sales_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and validate sales data.
    """
    try:
        if pl_df.is_empty():
            st.error("❌ Sales data is empty")
            return pl.DataFrame()
            
        # Required columns with alternatives
        required_cols = {
            "date": ["BILL_DATE", "DATE", "Bill Date", "Sales Date"],
            "store": ["STORE", "Store", "EBO NAME", "store_code"],
            "sku": ["SKU", "Sku", "EAN", "Product_Code"],
            "quantity": ["BILL_QUANTITY", "Quantity", "QTY", "Bill_Qty"]
        }
        
        # Find matching columns
        col_mapping = {}
        missing_cols = []
        
        for key, alternatives in required_cols.items():
            found = None
            for alt in alternatives:
                if alt in pl_df.columns:
                    found = alt
                    break
            if found:
                col_mapping[key] = found
            else:
                missing_cols.append(f"{key} ({'/'.join(alternatives)})")
        
        if missing_cols:
            st.error("❌ Missing required columns in sales data:")
            for col in missing_cols:
                st.error(f"- {col}")
            return pl.DataFrame()
        
        # Clean date field
        cleaned_df = pl_df.with_columns([
            pl.col(col_mapping["date"])
            .str.strptime(pl.Date, "%Y-%m-%d %H:%M:%S", strict=False)
            .alias("DATE")
        ])
        
        # Clean and standardize other fields
        cleaned_df = cleaned_df.with_columns([
            # Clean store names
            pl.col(col_mapping["store"])
            .cast(pl.Utf8)
            .map_elements(lambda x: normalize_store_name(str(x).strip()) if x is not None else "")
            .alias("STORE"),
            
            # Clean SKUs
            pl.col(col_mapping["sku"])
            .cast(pl.Utf8)
            .map_elements(lambda x: str(x).strip().upper() if x is not None else "")
            .alias("SKU"),
            
            # Clean quantities
            pl.col(col_mapping["quantity"])
            .cast(pl.Float64)
            .alias("QTY")
        ])
        
        # Remove invalid records
        initial_count = cleaned_df.height
        cleaned_df = cleaned_df.filter(
            (pl.col("DATE").is_not_null()) &
            (pl.col("STORE") != "") &
            (pl.col("SKU") != "") &
            (pl.col("QTY").is_not_null()) &
            (pl.col("QTY") > 0)
        )
        
        removed_count = initial_count - cleaned_df.height
        if removed_count > 0:
            st.warning(f"⚠️ Removed {removed_count:,} invalid records from sales data")
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"❌ Error cleaning sales data: {str(e)}")
        return pl.DataFrame()

def clean_stock_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and validate stock data.
    """
    try:
        # Required columns with alternatives
        cols = {
            "store": ["Store Name", "store_code", "Channel", "EBO NAME", "STORE", "EBO", "Store_Code", "Location"],
            "sku": ["Sku", "SKU", "ean", "EAN", "Product_Code", "SKU_Code"],
            "stock": ["quantity", "Stock", "Qty OH", "Available_Stock", "Current_Stock", "Inventory"]
        }
        
        # Find matching columns
        col_mapping = {}
        missing_cols = []
        
        for key, alternatives in cols.items():
            found = None
            for alt in alternatives:
                if alt in pl_df.columns:
                    found = alt
                    break
            if found:
                col_mapping[key] = found
            else:
                missing_cols.append(f"{key} ({'/'.join(alternatives)})")
        
        if missing_cols:
            st.error("❌ Missing required columns in stock data:")
            for col in missing_cols:
                st.error(f"- {col}")
            return pl.DataFrame()
        
        # Clean and standardize data
        cleaned_df = pl_df.select([
            pl.col(col_mapping["store"])
            .cast(pl.Utf8)
            .map_elements(normalize_store_name)
            .alias("STORE"),
            
            pl.col(col_mapping["sku"])
            .cast(pl.Utf8)
            .map_elements(lambda x: str(x).strip().upper() if x is not None else "")
            .alias("SKU"),
            
            pl.when(pl.col(col_mapping["stock"]).cast(pl.Float64) < 0)
            .then(0)
            .otherwise(pl.col(col_mapping["stock"]).cast(pl.Float64))
            .fill_null(0)
            .alias("STORE_STOCK")
        ])
        
        # Remove invalid records
        initial_count = cleaned_df.height
        cleaned_df = cleaned_df.filter(
            (pl.col("STORE") != "") &
            (pl.col("SKU") != "")
        )
        
        removed_count = initial_count - cleaned_df.height
        if removed_count > 0:
            st.warning(f"⚠️ Removed {removed_count:,} invalid records from stock data")
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"❌ Error cleaning stock data: {str(e)}")
        return pl.DataFrame()

def clean_warehouse_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and validate warehouse data.
    """
    try:
        # Required columns with alternatives
        cols = {
            "sku": ["Client SKU Id / EAN", "SKU", "Sku", "Row Labels"],
            "stock": ["Total Available Quantity", "quantity", "Stock", "Available in EBO"]
        }
        
        # Find matching columns
        col_mapping = {}
        missing_cols = []
        
        for key, alternatives in cols.items():
            found = None
            for alt in alternatives:
                if alt in pl_df.columns:
                    found = alt
                    break
            if found:
                col_mapping[key] = found
            else:
                missing_cols.append(f"{key} ({'/'.join(alternatives)})")
        
        if missing_cols:
            st.error("❌ Missing required columns in warehouse data:")
            for col in missing_cols:
                st.error(f"- {col}")
            return pl.DataFrame()
        
        # Clean and standardize data
        cleaned_df = pl_df.select([
            pl.col(col_mapping["sku"])
            .cast(pl.Utf8)
            .map_elements(lambda x: str(x).strip().upper() if x is not None else "")
            .alias("SKU"),
            
            pl.when(pl.col(col_mapping["stock"]).cast(pl.Float64) < 0)
            .then(0)
            .otherwise(pl.col(col_mapping["stock"]).cast(pl.Float64))
            .fill_null(0)
            .alias("WAREHOUSE_STOCK")
        ])
        
        # Remove invalid records
        initial_count = cleaned_df.height
        cleaned_df = cleaned_df.filter(pl.col("SKU") != "")
        
        removed_count = initial_count - cleaned_df.height
        if removed_count > 0:
            st.warning(f"⚠️ Removed {removed_count:,} invalid records from warehouse data")
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"❌ Error cleaning warehouse data: {str(e)}")
        return pl.DataFrame()

def clean_sku_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and validate SKU master data.
    """
    try:
        # Required columns with alternatives
        cols = {
            "sku": ["SKU", "Sku", "ean", "Row Labels"],
            "style": ["STYLE", "Style"],
            "color": ["Colour", "Color"],
            "size": ["Size", "SIZE"]
        }
        
        # Find matching columns
        col_mapping = {}
        missing_cols = []
        
        for key, alternatives in cols.items():
            found = None
            for alt in alternatives:
                if alt in pl_df.columns:
                    found = alt
                    break
            if found:
                col_mapping[key] = found
            else:
                missing_cols.append(f"{key} ({'/'.join(alternatives)})")
        
        if missing_cols:
            st.error("❌ Missing required columns in SKU master data:")
            for col in missing_cols:
                st.error(f"- {col}")
            return pl.DataFrame()
        
        # Clean and standardize data
        cleaned_df = pl_df.select([
            pl.col(col_mapping["sku"])
            .cast(pl.Utf8)
            .map_elements(lambda x: str(x).strip().upper() if x is not None else "")
            .alias("SKU"),
            
            pl.col(col_mapping["style"])
            .cast(pl.Utf8)
            .map_elements(lambda x: str(x).strip().upper() if x is not None else "")
            .alias("STYLE"),
            
            pl.col(col_mapping["color"])
            .cast(pl.Utf8)
            .map_elements(lambda x: str(x).strip().title() if x is not None else "")
            .alias("Colour"),
            
            pl.col(col_mapping["size"])
            .cast(pl.Utf8)
            .map_elements(lambda x: str(x).strip().upper() if x is not None else "")
            .alias("Size")
        ])
        
        # Add size categorization
        cleaned_df = cleaned_df.with_columns([
            pl.col("Size").is_in(["S", "M", "L", "XL", "2XL"])
            .cast(pl.Int64)
            .alias("IS_REGULAR_SIZE"),
            
            pl.col("Size").is_in(["3XL", "4XL", "5XL"])
            .cast(pl.Int64)
            .alias("IS_PLUS_SIZE"),
            
            pl.col("Size").is_in(["08Y", "10Y", "12Y", "14Y"])
            .cast(pl.Int64)
            .alias("IS_KIDS_SIZE")
        ])
        
        # Remove invalid records
        initial_count = cleaned_df.height
        cleaned_df = cleaned_df.filter(
            (pl.col("SKU") != "") &
            (pl.col("STYLE") != "") &
            (pl.col("Size") != "")
        )
        
        removed_count = initial_count - cleaned_df.height
        if removed_count > 0:
            st.warning(f"⚠️ Removed {removed_count:,} invalid records from SKU master data")
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"❌ Error cleaning SKU master data: {str(e)}")
        return pl.DataFrame()

def clean_store_master_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and validate store master data.
    """
    try:
        # Required columns with alternatives
        cols = {
            "store": ["Store", "store_code", "Store Name", "Store_Code", "EBO", "Location"],
            "mens": ["Mens", "Men", "Mens_Allow", "Allow_Mens", "Men's"],
            "womens": ["Womens", "Women", "Womens_Allow", "Allow_Womens", "Women's"],
            "boys": ["Boys", "Boy", "Boys_Allow", "Allow_Boys", "Boy's"],
            "capacity": ["Capacity", "Store Capacity", "Total Capacity", "Max Capacity", "Store_Cap"]
        }
        
        # Find matching columns
        col_mapping = {}
        missing_cols = []
        
        for key, alternatives in cols.items():
            found = None
            for alt in alternatives:
                if alt in pl_df.columns:
                    found = alt
                    break
            if found:
                col_mapping[key] = found
            else:
                missing_cols.append(f"{key} ({'/'.join(alternatives)})")
        
        if missing_cols:
            st.error("❌ Missing required columns in store master data:")
            for col in missing_cols:
                st.error(f"- {col}")
            return pl.DataFrame()
        
        # Clean and standardize data
        cleaned_df = pl_df.select([
            pl.col(col_mapping["store"])
            .cast(pl.Utf8)
            .map_elements(normalize_store_name)
            .alias("STORE"),
            
            pl.col(col_mapping["mens"])
            .cast(pl.Utf8)
            .str.to_lowercase()
            .map_elements(lambda x: any(val in str(x).lower() for val in ["yes", "y", "true", "1"]))
            .alias("ALLOWS_MENS"),
            
            pl.col(col_mapping["womens"])
            .cast(pl.Utf8)
            .str.to_lowercase()
            .map_elements(lambda x: any(val in str(x).lower() for val in ["yes", "y", "true", "1"]))
            .alias("ALLOWS_WOMENS"),
            
            pl.col(col_mapping["boys"])
            .cast(pl.Utf8)
            .str.to_lowercase()
            .map_elements(lambda x: any(val in str(x).lower() for val in ["yes", "y", "true", "1"]))
            .alias("ALLOWS_BOYS"),
            
            pl.coalesce(
                pl.col(col_mapping["capacity"]).cast(pl.Int64),
                pl.lit(999999)  # Default capacity
            )
            .map_elements(lambda x: min(max(x, 0), 999999))
            .alias("STORE_CAPACITY")
        ])
        
        # Remove invalid records
        initial_count = cleaned_df.height
        cleaned_df = cleaned_df.filter(pl.col("STORE") != "")
        
        removed_count = initial_count - cleaned_df.height
        if removed_count > 0:
            st.warning(f"⚠️ Removed {removed_count:,} invalid records from store master data")
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"❌ Error cleaning store master data: {str(e)}")
        return pl.DataFrame()

def clean_all_data(sales_pl, stock_pl, warehouse_pl, sku_master_pl, style_master_pl, store_master_pl=None):
    """
    Clean all input data files with comprehensive validation and reporting.
    """
    cleaned_data = {}
    data_issues = {}

    # Clean sales data
    if not sales_pl.is_empty():
        try:
            cleaned_sales = clean_sales_pl(sales_pl)
            data_issues["Sales"] = []
            if cleaned_sales.height < sales_pl.height:
                removed = sales_pl.height - cleaned_sales.height
                data_issues["Sales"].append(f"Removed {removed:,} invalid records")
            cleaned_data["sales"] = cleaned_sales
        except Exception as e:
            st.error(f"❌ Error cleaning sales data: {str(e)}")
            cleaned_data["sales"] = pl.DataFrame()
    else:
        st.error("❌ No sales data provided")
        cleaned_data["sales"] = pl.DataFrame()

    # Clean stock data
    if not stock_pl.is_empty():
        try:
            cleaned_stock = clean_stock_pl(stock_pl)
            data_issues["Stock"] = []
            if cleaned_stock.height < stock_pl.height:
                removed = stock_pl.height - cleaned_stock.height
                data_issues["Stock"].append(f"Removed {removed:,} invalid records")
            cleaned_data["stock"] = cleaned_stock
        except Exception as e:
            st.error(f"❌ Error cleaning stock data: {str(e)}")
            cleaned_data["stock"] = pl.DataFrame()
    else:
        st.error("❌ No stock data provided")
        cleaned_data["stock"] = pl.DataFrame()

    # Clean warehouse data
    if not warehouse_pl.is_empty():
        try:
            cleaned_warehouse = clean_warehouse_pl(warehouse_pl)
            data_issues["Warehouse"] = []
            if cleaned_warehouse.height < warehouse_pl.height:
                removed = warehouse_pl.height - cleaned_warehouse.height
                data_issues["Warehouse"].append(f"Removed {removed:,} invalid records")
            cleaned_data["warehouse"] = cleaned_warehouse
        except Exception as e:
            st.error(f"❌ Error cleaning warehouse data: {str(e)}")
            cleaned_data["warehouse"] = pl.DataFrame()
    else:
        st.error("❌ No warehouse data provided")
        cleaned_data["warehouse"] = pl.DataFrame()

    # Clean SKU master data
    if not sku_master_pl.is_empty():
        try:
            cleaned_sku = clean_sku_master_pl(sku_master_pl)
            data_issues["SKU Master"] = []
            if cleaned_sku.height < sku_master_pl.height:
                removed = sku_master_pl.height - cleaned_sku.height
                data_issues["SKU Master"].append(f"Removed {removed:,} invalid records")
            cleaned_data["sku_master"] = cleaned_sku
        except Exception as e:
            st.error(f"❌ Error cleaning SKU master data: {str(e)}")
            cleaned_data["sku_master"] = pl.DataFrame()
    else:
        st.error("❌ No SKU master data provided")
        cleaned_data["sku_master"] = pl.DataFrame()

    # Clean style master data
    if not style_master_pl.is_empty():
        try:
            cleaned_style = clean_style_master_pl(style_master_pl)
            data_issues["Style Master"] = []
            if cleaned_style.height < style_master_pl.height:
                removed = style_master_pl.height - cleaned_style.height
                data_issues["Style Master"].append(f"Removed {removed:,} invalid records")
            cleaned_data["style_master"] = cleaned_style
        except Exception as e:
            st.error(f"❌ Error cleaning style master data: {str(e)}")
            cleaned_data["style_master"] = pl.DataFrame()
    else:
        st.error("❌ No style master data provided")
        cleaned_data["style_master"] = pl.DataFrame()

    # Clean store master data if provided
    if store_master_pl is not None and not store_master_pl.is_empty():
        try:
            cleaned_store = clean_store_master_pl(store_master_pl)
            data_issues["Store Master"] = []
            if cleaned_store.height < store_master_pl.height:
                removed = store_master_pl.height - store_master_pl.height
                data_issues["Store Master"].append(f"Removed {removed:,} invalid records")
            cleaned_data["store_master"] = cleaned_store
        except Exception as e:
            st.warning(f"⚠️ Error cleaning store master data: {str(e)}")
            cleaned_data["store_master"] = pl.DataFrame()
    else:
        cleaned_data["store_master"] = None

    # Report data cleaning results
    st.markdown("### 🧹 Data Cleaning Results")
    
    for dataset, issues in data_issues.items():
        if issues:
            st.warning(f"⚠️ {dataset} Data Issues:")
            for issue in issues:
                st.warning(f"  • {issue}")
        else:
            st.success(f"✅ {dataset}: No issues found")

    return cleaned_data