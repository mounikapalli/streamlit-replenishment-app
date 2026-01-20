"""
Data Merge Helper - Handles merging multiple data uploads
"""
import pandas as pd
import streamlit as st
from datetime import datetime
from typing import Optional, Tuple

class DataMergeManager:
    """Manage multiple data uploads and merging"""
    
    @staticmethod
    def load_file(uploaded_file) -> Optional[pd.DataFrame]:
        """Load CSV or Excel file"""
        try:
            if uploaded_file.name.endswith('.csv'):
                return pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                return pd.read_excel(uploaded_file)
            return None
        except Exception as e:
            st.error(f"Error loading {uploaded_file.name}: {str(e)}")
            return None
    
    @staticmethod
    def get_data_summary(df: pd.DataFrame) -> dict:
        """Get summary statistics of dataframe"""
        if df is None or df.empty:
            return None
        
        summary = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "file_size": df.memory_usage(deep=True).sum() / 1024 / 1024,  # MB
        }
        
        # Add date range if date column exists
        date_cols = [col for col in df.columns if 'date' in col.lower()]
        if date_cols:
            date_col = date_cols[0]
            try:
                if df[date_col].dtype == 'object':
                    df[date_col] = pd.to_datetime(df[date_col])
                summary["min_date"] = df[date_col].min()
                summary["max_date"] = df[date_col].max()
            except:
                pass
        
        return summary
    
    @staticmethod
    def merge_datasets(old_df: Optional[pd.DataFrame], 
                       new_df: pd.DataFrame,
                       merge_type: str = "append") -> pd.DataFrame:
        """
        Merge old and new datasets
        
        Args:
            old_df: Previously uploaded data
            new_df: New data to add
            merge_type: 'append' (add all), 'update' (overwrite by date), or 'dedupe' (remove duplicates)
        """
        
        if old_df is None or old_df.empty:
            return new_df.copy()
        
        if merge_type == "append":
            # Simply concatenate all data
            merged = pd.concat([old_df, new_df], ignore_index=True)
            return merged
        
        elif merge_type == "update":
            # Update by date - newer data overwrites older
            date_cols = [col for col in old_df.columns if 'date' in col.lower()]
            if date_cols:
                date_col = date_cols[0]
                try:
                    merged = pd.concat([old_df, new_df], ignore_index=True)
                    merged = merged.sort_values(by=date_col, ascending=False)
                    # Keep first occurrence (most recent)
                    merged = merged.drop_duplicates(subset=[col for col in merged.columns if col != date_col], keep='first')
                    return merged.sort_values(by=date_col)
                except:
                    pass
            
            # Fallback to append if date column not found
            return pd.concat([old_df, new_df], ignore_index=True)
        
        elif merge_type == "dedupe":
            # Combine and remove exact duplicates
            merged = pd.concat([old_df, new_df], ignore_index=True)
            merged = merged.drop_duplicates(keep='first')
            return merged
        
        return pd.concat([old_df, new_df], ignore_index=True)
    
    @staticmethod
    def display_comparison(old_df: Optional[pd.DataFrame], 
                          new_df: pd.DataFrame,
                          title: str = "Data Comparison"):
        """Display side-by-side comparison of old and new data"""
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Previous Data")
            if old_df is not None and not old_df.empty:
                old_summary = DataMergeManager.get_data_summary(old_df)
                st.metric("Rows", f"{old_summary['rows']:,}")
                st.metric("Columns", old_summary['columns'])
                if "min_date" in old_summary and "max_date" in old_summary:
                    st.text(f"Date Range: {old_summary['min_date'].date()} to {old_summary['max_date'].date()}")
                with st.expander("Preview"):
                    st.dataframe(old_df.head(10), use_container_width=True)
            else:
                st.info("No previous data")
        
        with col2:
            st.subheader("📁 New Data")
            new_summary = DataMergeManager.get_data_summary(new_df)
            st.metric("Rows", f"{new_summary['rows']:,}")
            st.metric("Columns", new_summary['columns'])
            if "min_date" in new_summary and "max_date" in new_summary:
                st.text(f"Date Range: {new_summary['min_date'].date()} to {new_summary['max_date'].date()}")
            with st.expander("Preview"):
                st.dataframe(new_df.head(10), use_container_width=True)
        
        # Merge summary
        if old_df is not None and not old_df.empty:
            merged = DataMergeManager.merge_datasets(old_df, new_df, "append")
            st.divider()
            st.subheader("✅ Merged Result (Preview)")
            st.metric("Total Rows", f"{len(merged):,}")
            st.metric("Total Rows Added", f"{len(new_df):,}")
            if len(merged) > 0:
                st.success(f"✓ Successfully prepared {len(new_df):,} new records for merge!")


def streamlit_multi_upload_ui(data_type: str = "Sales") -> Tuple[Optional[pd.DataFrame], str]:
    """
    Streamlit UI for multi-file uploads with comparison
    
    Returns:
        Tuple of (merged_dataframe, merge_type)
    """
    
    st.subheader(f"📂 {data_type} Data Upload & Merge")
    
    # Initialize session state for storing old data
    session_key = f"{data_type.lower()}_old_data"
    if session_key not in st.session_state:
        st.session_state[session_key] = None
    
    # Display current stored data
    with st.expander("📊 Current Stored Data Info", expanded=True):
        old_data = st.session_state[session_key]
        if old_data is not None and not old_data.empty:
            old_summary = DataMergeManager.get_data_summary(old_data)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Stored Rows", f"{old_summary['rows']:,}")
            with col2:
                st.metric("Stored Columns", old_summary['columns'])
            with col3:
                if "min_date" in old_summary and "max_date" in old_summary:
                    st.metric("Date Range", f"{old_summary['min_date'].date()} to {old_summary['max_date'].date()}")
            
            with st.expander("View Stored Data Preview"):
                st.dataframe(old_data.head(20), use_container_width=True)
        else:
            st.info("No data stored yet. Upload files to get started.")
    
    # Upload new files
    st.markdown("### 📥 Add New Data Files")
    uploaded_files = st.file_uploader(
        f"Upload {data_type} files (CSV/Excel)",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
        help="Upload multiple years/batches of data. They will be combined."
    )
    
    if uploaded_files:
        new_data_list = []
        
        st.info(f"Processing {len(uploaded_files)} file(s)...")
        
        for uploaded_file in uploaded_files:
            df = DataMergeManager.load_file(uploaded_file)
            if df is not None:
                new_data_list.append(df)
                st.success(f"✓ Loaded {uploaded_file.name}: {len(df):,} rows")
        
        if new_data_list:
            # Combine new files
            if len(new_data_list) > 1:
                new_combined = pd.concat(new_data_list, ignore_index=True)
                st.info(f"Combined {len(new_data_list)} files: {len(new_combined):,} total rows")
            else:
                new_combined = new_data_list[0]
            
            # Show merge options
            st.markdown("### ⚙️ Merge Options")
            merge_type = st.radio(
                "How to merge with existing data:",
                options=["append", "update", "dedupe"],
                format_func=lambda x: {
                    "append": "📎 Append (Add all rows)",
                    "update": "🔄 Update (Newer overwrites older)",
                    "dedupe": "🔀 Deduplicate (Remove exact duplicates)"
                }.get(x, x),
                help="""
                - **Append**: Simply add all new rows (best for yearly data)
                - **Update**: Use newer data to overwrite older matching records
                - **Deduplicate**: Remove any exact duplicate rows
                """
            )
            
            # Show comparison
            DataMergeManager.display_comparison(
                st.session_state[session_key],
                new_combined,
                f"{data_type} Data Comparison"
            )
            
            # Merge and save button
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Merge & Store Data", key=f"merge_btn_{data_type}"):
                    merged_data = DataMergeManager.merge_datasets(
                        st.session_state[session_key],
                        new_combined,
                        merge_type
                    )
                    st.session_state[session_key] = merged_data
                    st.success(f"✅ Data merged! Total records: {len(merged_data):,}")
                    st.balloons()
            
            with col2:
                if st.button("🔄 Replace Data", key=f"replace_btn_{data_type}"):
                    st.session_state[session_key] = new_combined
                    st.info(f"Data replaced. Total records: {len(new_combined):,}")
            
            return st.session_state[session_key], merge_type
    
    return st.session_state[session_key], "append"


def save_merged_data_to_csv(df: pd.DataFrame, filename: str = "merged_data.csv") -> bytes:
    """Convert dataframe to CSV bytes for download"""
    return df.to_csv(index=False).encode()
