import streamlit as st
import polars as pl

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
                removed = store_master_pl.height - cleaned_store.height
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

def clean_sales_pl(pl_df: pl.DataFrame) -> pl.DataFrame:
    """
    Clean and validate sales data with comprehensive error handling.
    """
    try:
        if pl_df.is_empty():
            st.error("❌ Sales data is empty")
            return pl.DataFrame()
            
        # Required columns
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
        
        # Start cleaning with a copy
        cleaned_df = pl_df.clone()
        
        # Clean and validate date
        cleaned_df = cleaned_df.with_columns([
            pl.col(col_mapping["date"])
            .str.strptime(pl.Date, "%Y-%m-%d %H:%M:%S", strict=False)
            .alias("DATE")
        ])
        
        # Clean store names
        cleaned_df = cleaned_df.with_columns([
            pl.col(col_mapping["store"])
            .cast(pl.Utf8)
            .map_elements(lambda x: str(x).strip().title() if x is not None else "")
            .alias("STORE")
        ])
        
        # Clean SKUs
        cleaned_df = cleaned_df.with_columns([
            pl.col(col_mapping["sku"])
            .cast(pl.Utf8)
            .map_elements(lambda x: str(x).strip().upper() if x is not None else "")
            .alias("SKU")
        ])
        
        # Clean and validate quantities
        cleaned_df = cleaned_df.with_columns([
            pl.col(col_mapping["quantity"])
            .cast(pl.Float64)
            .alias("QTY")
        ])
        
        # Remove invalid records
        cleaned_df = cleaned_df.filter(
            (pl.col("DATE").is_not_null()) &
            (pl.col("STORE") != "") &
            (pl.col("SKU") != "") &
            (pl.col("QTY").is_not_null()) &
            (pl.col("QTY") > 0)
        )
        
        return cleaned_df
        
    except Exception as e:
        st.error(f"❌ Error cleaning sales data: {str(e)}")
        return pl.DataFrame()