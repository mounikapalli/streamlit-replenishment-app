"""
Database Manager - Handles persistent data storage in SQLite database
"""
import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path
import tempfile
from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# Database file location (persistent across sessions)
DB_DIR = Path(tempfile.gettempdir()) / "streamlit_app_db"
DB_DIR.mkdir(exist_ok=True)
DB_FILE = DB_DIR / "sales_data.db"


# Caching decorator for database operations
@st.cache_data(ttl=7200, show_spinner=False)  # Cache for 2 hours, no spinner
def _cached_load_all_data():
    """Cached version of loading all data"""
    db = SalesDatabase()
    try:
        conn = db.get_connection()
        df = pd.read_sql_query("SELECT * FROM sales_data ORDER BY date DESC", conn)
        conn.close()
        if df.empty:
            return None
        return df
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return None


@st.cache_data(ttl=7200, show_spinner=False)  # Disable spinner for faster feel
def _cached_get_data_summary():
    """Cached version of getting summary - optimized with single query"""
    db = SalesDatabase()
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Single optimized query instead of multiple queries
        cursor.execute("""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT store) as total_stores,
            COUNT(DISTINCT sku) as total_skus,
            MIN(date) as min_date,
            MAX(date) as max_date,
            SUM(quantity) as total_quantity,
            SUM(amount) as total_amount
        FROM sales_data
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "total_rows": result[0] or 0,
                "total_stores": result[1] or 0,
                "total_skus": result[2] or 0,
                "min_date": result[3],
                "max_date": result[4],
                "total_quantity": result[5] or 0,
                "total_amount": result[6] or 0
            }
        return {}
        
    except Exception as e:
        logger.error(f"Error getting summary: {str(e)}")
        return {}


@st.cache_data(ttl=7200, show_spinner=False)  # Cache for 2 hours, no spinner
def _cached_get_quick_summary():
    """Ultra-fast summary - only row count and date range"""
    db = SalesDatabase()
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT 
            COUNT(*) as total_rows,
            MIN(date) as min_date,
            MAX(date) as max_date,
            SUM(amount) as total_amount
        FROM sales_data
        LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "total_rows": result[0] or 0,
                "min_date": result[1],
                "max_date": result[2],
                "total_amount": result[3] or 0
            }
        return {}
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {}


class SalesDatabase:
    """Manage SQLite database for sales data"""
    
    def __init__(self, db_path: str = str(DB_FILE)):
        """Initialize database connection"""
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database and create tables"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create sales_data table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                store TEXT,
                sku TEXT,
                quantity REAL,
                amount REAL,
                year INTEGER,
                month INTEGER,
                upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_file TEXT
            )
            """)
            
            # Create index for faster queries
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_date ON sales_data(date)
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_store ON sales_data(store)
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sku ON sales_data(sku)
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_year ON sales_data(year)
            """)
            
            # Create upload_history table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_file TEXT,
                rows_uploaded INTEGER,
                status TEXT
            )
            """)
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            st.error(f"Database error: {str(e)}")
    
    def save_dataframe(self, df: pd.DataFrame, source_file: str = "merged_data") -> bool:
        """
        Save dataframe to database
        
        Args:
            df: DataFrame to save
            source_file: Name of source file
            
        Returns:
            True if successful
        """
        try:
            if df is None or df.empty:
                st.warning("No data to save")
                return False
            
            conn = self.get_connection()
            
            # Prepare data for insertion
            df_copy = df.copy()
            
            # Add year and month columns if date column exists
            date_cols = [col for col in df_copy.columns if 'date' in col.lower()]
            if date_cols:
                date_col = date_cols[0]
                try:
                    df_copy[date_col] = pd.to_datetime(df_copy[date_col])
                    df_copy['year'] = df_copy[date_col].dt.year
                    df_copy['month'] = df_copy[date_col].dt.month
                except:
                    pass
            
            # Map common column names to database schema
            column_mapping = {
                'date': 'date', 'Date': 'date', 'DATE': 'date',
                'store': 'store', 'Store': 'store', 'STORE': 'store', 'store_id': 'store', 'Store_ID': 'store',
                'sku': 'sku', 'SKU': 'sku', 'product_id': 'sku', 'Product_ID': 'sku',
                'quantity': 'quantity', 'Quantity': 'quantity', 'QTY': 'quantity', 'qty': 'quantity',
                'amount': 'amount', 'Amount': 'amount', 'sales': 'amount', 'Sales': 'amount', 'SALES': 'amount'
            }
            
            # Rename columns to match schema
            df_copy = df_copy.rename(columns=column_mapping)
            
            # Select only relevant columns
            cols_to_save = [col for col in ['date', 'store', 'sku', 'quantity', 'amount', 'year', 'month'] 
                           if col in df_copy.columns]
            df_copy = df_copy[cols_to_save]
            df_copy['source_file'] = source_file
            
            # Insert data into database
            df_copy.to_sql('sales_data', conn, if_exists='append', index=False)
            
            # Record upload history
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO upload_history (source_file, rows_uploaded, status)
            VALUES (?, ?, ?)
            """, (source_file, len(df), 'success'))
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ Saved {len(df):,} rows to database")
            logger.info(f"Saved {len(df)} rows from {source_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")
            st.error(f"Error saving data: {str(e)}")
            return False
    
    def load_all_data(self) -> Optional[pd.DataFrame]:
        """Load all data from database (uses cache)"""
        return _cached_load_all_data()
    
    def load_data_by_year(self, year: int) -> Optional[pd.DataFrame]:
        """Load data for specific year"""
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(
                "SELECT * FROM sales_data WHERE year = ? ORDER BY date DESC",
                conn,
                params=(year,)
            )
            conn.close()
            
            if df.empty:
                return None
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return None
    
    def load_data_by_date_range(self, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Load data within date range"""
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(
                "SELECT * FROM sales_data WHERE date BETWEEN ? AND ? ORDER BY date DESC",
                conn,
                params=(start_date, end_date)
            )
            conn.close()
            
            if df.empty:
                return None
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            return None
    
    def get_data_summary(self) -> dict:
        """Get summary statistics of stored data (uses cache)"""
        return _cached_get_data_summary()
    
    def get_upload_history(self, limit: int = 10) -> List[dict]:
        """Get upload history"""
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(
                "SELECT * FROM upload_history ORDER BY upload_timestamp DESC LIMIT ?",
                conn,
                params=(limit,)
            )
            conn.close()
            
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error getting history: {str(e)}")
            return []
    
    def delete_all_data(self) -> bool:
        """Delete all data from database (careful!)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sales_data")
            conn.commit()
            conn.close()
            st.warning("⚠️ All data deleted from database")
            return True
        except Exception as e:
            logger.error(f"Error deleting data: {str(e)}")
            return False


def streamlit_database_status():
    """Display database status in Streamlit - uses quick summary for speed"""
    # Use quick summary for instant display
    summary = _cached_get_quick_summary()
    
    if summary.get('total_rows', 0) == 0:
        st.info("📊 Database is empty. Upload data to get started.")
        return
    
    st.subheader("📊 Database Summary")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Rows", f"{summary['total_rows']:,}")
    with col2:
        st.metric("Total Amount", f"₹{summary['total_amount']:,.0f}")
    with col3:
        date_range = ""
        if summary['min_date'] and summary['max_date']:
            date_range = f"{summary['min_date']} to {summary['max_date']}"
        st.metric("Date Range", date_range or "N/A")
    
    # Show upload history (cached separately)
    with st.expander("📜 Upload History"):
        db = SalesDatabase()
        history = db.get_upload_history()
        if history:
            for record in history:
                st.write(f"📁 {record['source_file']} - {record['rows_uploaded']:,} rows - {record['upload_timestamp']}")
        else:
            st.info("No upload history")


def streamlit_data_management():
    """Streamlit UI for database management"""
    
    with st.expander("🗄️ Database Management", expanded=False):
        st.warning("⚠️ Warning: These are advanced operations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Refresh Summary", key="refresh_db"):
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear All Data", key="clear_db"):
                db = SalesDatabase()
                if db.delete_all_data():
                    st.rerun()
