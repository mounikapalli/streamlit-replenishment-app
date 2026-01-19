import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import io

# Page Configuration
st.set_page_config(
    page_title="Retail Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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

def show_sample_data(df: pd.DataFrame, label: str):
    """Display a sample of the data with improved styling"""
    if df.empty:
        st.info(f"ℹ️ No data uploaded for {label}")
        return
        
    with st.expander(f"📊 {label} Preview", expanded=False):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"**Rows:** {len(df):,}")
        with col2:
            st.markdown(f"**Columns:** {len(df.columns)}")
        
        st.markdown("**Available Columns:**")
        st.markdown(", ".join(f"`{col}`" for col in df.columns))
        
        st.markdown("**Sample Data:**")
        st.dataframe(
            df.head(5),
            use_container_width=True,
            height=200
        )

def main():
    # Sidebar
    with st.sidebar:
        st.markdown("## 📊 Analytics Dashboard")
        st.markdown("---")
        st.markdown("### 📁 Data Upload")
        
        # File uploaders with improved UI
        uploaded_files = {
            "sales": st.file_uploader("Sales Data (CSV/Excel)", type=["csv", "xlsx"]),
            "stock": st.file_uploader("Stock Data (CSV/Excel)", type=["csv", "xlsx"]),
            "warehouse": st.file_uploader("Warehouse Data (CSV/Excel)", type=["csv", "xlsx"]),
            "sku_master": st.file_uploader("SKU Master (CSV/Excel)", type=["csv", "xlsx"]),
            "style_master": st.file_uploader("Style Master (CSV/Excel)", type=["csv", "xlsx"])
        }
        
        # Process uploaded files
        data = process_uploaded_files(uploaded_files)
        
        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        time_period = st.selectbox(
            "Analysis Period",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Custom Range"]
        )
        
        if time_period == "Custom Range":
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
    
    # Main Content
    st.markdown("<h1 class='title'>Retail Analytics Dashboard</h1>", unsafe_allow_html=True)
    
    # Data Preview Section
    st.markdown("## Data Overview")
    st.markdown("Review your uploaded data below. Click to expand each section.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'sales' in data:
            show_sample_data(data['sales'], "Sales Data")
        if 'stock' in data:
            show_sample_data(data['stock'], "Stock Data")
        if 'warehouse' in data:
            show_sample_data(data['warehouse'], "Warehouse Data")
    
    with col2:
        if 'sku_master' in data:
            show_sample_data(data['sku_master'], "SKU Master")
        if 'style_master' in data:
            show_sample_data(data['style_master'], "Style Master")
    
    # Check if all required data is available
    if all(key in data for key in ['sales', 'stock', 'warehouse', 'sku_master', 'style_master']):
        st.markdown("## Analysis")
        
        # Key Metrics
        metrics_cols = st.columns(4)
        
        with metrics_cols[0]:
            total_sales = data['sales']['QUANTITY'].sum()
            st.markdown(f"""
                <div class='metric-card'>
                    <h3>Total Sales</h3>
                    <h2>{total_sales:,.0f}</h2>
                </div>
            """, unsafe_allow_html=True)
            
        with metrics_cols[1]:
            store_count = data['stock']['STORE'].nunique()
            st.markdown(f"""
                <div class='metric-card'>
                    <h3>Store Count</h3>
                    <h2>{store_count:,.0f}</h2>
                </div>
            """, unsafe_allow_html=True)
            
        with metrics_cols[2]:
            sku_count = data['sku_master']['SKU'].nunique()
            st.markdown(f"""
                <div class='metric-card'>
                    <h3>Total SKUs</h3>
                    <h2>{sku_count:,.0f}</h2>
                </div>
            """, unsafe_allow_html=True)
            
        with metrics_cols[3]:
            total_stock = data['stock']['STOCK'].sum()
            st.markdown(f"""
                <div class='metric-card'>
                    <h3>Total Stock</h3>
                    <h2>{total_stock:,.0f}</h2>
                </div>
            """, unsafe_allow_html=True)
        
        # Analysis Tabs
        tabs = st.tabs([
            "📈 Sales Analysis",
            "📊 Stock Analysis",
            "🏬 Store Performance",
            "📦 SKU Analysis"
        ])
        
        with tabs[0]:
            st.markdown("### Sales Trends")
            # Add your sales analysis visualizations here
        
        with tabs[1]:
            st.markdown("### Stock Distribution")
            # Add your stock analysis visualizations here
        
        with tabs[2]:
            st.markdown("### Store Performance")
            # Add your store performance visualizations here
        
        with tabs[3]:
            st.markdown("### SKU Analysis")
            # Add your SKU analysis visualizations here
    
    else:
        st.info("👆 Please upload all required data files to begin analysis")

if __name__ == "__main__":
    main()