import streamlit as st
import polars as pl
from datetime import timedelta, datetime
from pathlib import Path
from new_style_cleaning import clean_style_master_pl
from new_store_cleaning import clean_store_master_pl

# Configure page settings
st.set_page_config(
    page_title="Inventory Replenishment System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Page header with custom styling
st.markdown("""
    <style>
        .main-header {
            color: #2c3e50;
            font-size: 2.5em;
            font-weight: 600;
            margin-bottom: 1em;
            text-align: center;
            padding: 0.5em;
            background: #f8f9fa;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .sub-header {
            color: #34495e;
            font-size: 1.5em;
            font-weight: 500;
            margin: 1em 0;
            padding: 0.5em;
            border-bottom: 2px solid #eceef0;
        }
        .success-text { color: #28a745; }
        .warning-text { color: #ffc107; }
        .error-text { color: #dc3545; }
        .info-text { color: #17a2b8; }
    </style>
    <div class="main-header">📊 Inventory Replenishment System</div>
""", unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.markdown("### 📁 Data Files")
    sales_file = st.file_uploader("Sales Data", type=["csv", "xlsx"])
    stock_file = st.file_uploader("Store Stock", type=["csv", "xlsx"])
    warehouse_file = st.file_uploader("Warehouse Stock", type=["csv", "xlsx"])
    sku_master_file = st.file_uploader("SKU Master", type=["csv", "xlsx"])
    style_master_file = st.file_uploader("Style Master", type=["csv", "xlsx"])
    store_master_file = st.file_uploader("Store Master (Optional)", type=["csv", "xlsx"])
    
    st.markdown("### ⚙️ Settings")
    coverage_weeks = st.number_input("Coverage Weeks", min_value=1, max_value=12, value=4)
    safety_weeks = st.number_input("Safety Stock Weeks", min_value=0, max_value=4, value=1)
    weeks_back = st.number_input("Analysis Period (Weeks)", min_value=4, max_value=52, value=12)

def main():
    # Initialize session state if needed
    if 'files_validated' not in st.session_state:
        st.session_state.files_validated = False

    # File validation
    files_ready = (
        sales_file is not None and
        stock_file is not None and 
        warehouse_file is not None and
        sku_master_file is not None and
        style_master_file is not None
    )

    if not files_ready:
        st.warning("⚠️ Please upload all required files to proceed.")
        return

    try:
        # Read files with progress reporting
        with st.spinner("🔄 Reading data files..."):
            # Process uploaded files
            sales_pl = read_to_pd(sales_file)
            stock_pl = read_to_pd(stock_file)
            warehouse_pl = read_to_pd(warehouse_file)
            sku_master_pl = read_to_pd(sku_master_file)
            style_master_pl = read_to_pd(style_master_file)
            store_master_pl = read_to_pd(store_master_file) if store_master_file else pl.DataFrame()

            # Validate data
            if any(df.is_empty() for df in [sales_pl, stock_pl, warehouse_pl, sku_master_pl, style_master_pl]):
                st.error("❌ One or more files are empty or could not be read properly.")
                return

            st.success("✅ All files loaded successfully!")
            
            # Show data previews in expanders
            show_sample_data(sales_pl, "Sales Data")
            show_sample_data(stock_pl, "Store Stock")
            show_sample_data(warehouse_pl, "Warehouse Stock")
            show_sample_data(sku_master_pl, "SKU Master")
            show_sample_data(style_master_pl, "Style Master")
            if not store_master_pl.is_empty():
                show_sample_data(store_master_pl, "Store Master")

        # Compute replenishment with progress bar
        with st.spinner("🧮 Computing replenishment recommendations..."):
            result_pl = compute_replenishment(
                sales_pl, stock_pl, warehouse_pl, sku_master_pl,
                coverage_weeks, safety_weeks, weeks_back,
                style_master_pl, store_master_pl
            )

            if not result_pl.is_empty():
                # Success! Show download button and summary
                csv_buffer = result_pl.write_csv()
                st.download_button(
                    label="📥 Download Replenishment Plan",
                    data=csv_buffer,
                    file_name=f"replenishment_plan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
                
                # Show summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        "Total SKUs", 
                        f"{result_pl['SKU'].n_unique():,}"
                    )
                with col2:
                    st.metric(
                        "Total Stores",
                        f"{result_pl['STORE'].n_unique():,}"
                    )
                with col3:
                    replen_qty = result_pl['REPLENISHMENT_STOCK'].sum()
                    st.metric(
                        "Total Replenishment Qty",
                        f"{replen_qty:,.0f}"
                    )
                
                # Show detailed results
                st.markdown("### 📊 Replenishment Plan")
                st.dataframe(
                    result_pl
                    .sort(by=["STORE", "STYLE"])
                    .head(1000)
                    .to_pandas(),
                    use_container_width=True
                )

            else:
                st.error("❌ Error computing replenishment. Please check the error messages above.")

    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()