"""
Progress Tracking Module - Shows file processing progress with time estimates
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Optional, Callable

class ProcessingProgressTracker:
    """Track file processing progress with time estimates"""
    
    def __init__(self, total_rows: int, total_bytes: int, operation_name: str = "Processing"):
        """
        Initialize progress tracker
        
        Args:
            total_rows: Total number of rows to process
            total_bytes: Total file size in bytes
            operation_name: Name of the operation (e.g., "Processing", "Merging")
        """
        self.total_rows = total_rows
        self.total_bytes = total_bytes
        self.operation_name = operation_name
        self.start_time = datetime.now()
        self.rows_processed = 0
        self.bytes_processed = 0
        self.speed_rows_per_second = 0
        self.speed_bytes_per_second = 0
        
    def update(self, rows_processed: int, bytes_processed: int = 0):
        """
        Update progress
        
        Args:
            rows_processed: Number of rows processed so far
            bytes_processed: Number of bytes processed (optional)
        """
        self.rows_processed = rows_processed
        self.bytes_processed = bytes_processed if bytes_processed > 0 else rows_processed * 100  # Estimate
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed > 0:
            self.speed_rows_per_second = rows_processed / elapsed
            self.speed_bytes_per_second = self.bytes_processed / elapsed
    
    def get_progress_percentage(self) -> float:
        """Get progress as percentage (0-100)"""
        if self.total_rows <= 0:
            return 0
        return min(100, (self.rows_processed / self.total_rows) * 100)
    
    def get_elapsed_time(self) -> str:
        """Get formatted elapsed time"""
        elapsed = datetime.now() - self.start_time
        return self._format_timedelta(elapsed)
    
    def get_estimated_time_remaining(self) -> Optional[str]:
        """Get estimated remaining time"""
        if self.speed_rows_per_second <= 0 or self.rows_processed == 0:
            return None
        
        remaining_rows = self.total_rows - self.rows_processed
        if remaining_rows <= 0:
            return "Done!"
        
        seconds_remaining = remaining_rows / self.speed_rows_per_second
        remaining_time = timedelta(seconds=seconds_remaining)
        return self._format_timedelta(remaining_time)
    
    def get_estimated_total_time(self) -> Optional[str]:
        """Get estimated total processing time"""
        if self.speed_rows_per_second <= 0:
            return None
        
        seconds_total = self.total_rows / self.speed_rows_per_second
        total_time = timedelta(seconds=seconds_total)
        return self._format_timedelta(total_time)
    
    @staticmethod
    def _format_timedelta(td: timedelta) -> str:
        """Format timedelta to readable string"""
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)


def display_processing_progress(tracker: ProcessingProgressTracker,
                               show_details: bool = True):
    """
    Display processing progress with estimates
    
    Args:
        tracker: ProcessingProgressTracker instance
        show_details: Whether to show detailed metrics
    """
    progress_pct = tracker.get_progress_percentage()
    
    # Progress bar
    st.progress(progress_pct / 100, text=f"{progress_pct:.1f}% {tracker.operation_name}")
    
    if show_details:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Processed",
                f"{tracker.rows_processed:,} / {tracker.total_rows:,}",
                delta=f"{tracker.rows_processed:,}",
                delta_color="off"
            )
        
        with col2:
            st.metric(
                "Speed",
                f"{tracker.speed_rows_per_second:.0f} rows/s",
                delta=None,
                delta_color="off"
            )
        
        with col3:
            elapsed = tracker.get_elapsed_time()
            st.metric(
                "Elapsed Time",
                elapsed,
                delta=None,
                delta_color="off"
            )
        
        with col4:
            remaining = tracker.get_estimated_time_remaining()
            if remaining and remaining != "Done!":
                st.metric(
                    "Est. Remaining",
                    remaining,
                    delta=None,
                    delta_color="off"
                )
            else:
                st.metric(
                    "Status",
                    "Complete! ✅",
                    delta=None,
                    delta_color="off"
                )


def process_file_with_progress(df: pd.DataFrame,
                               processing_func: Callable,
                               chunk_size: int = 1000,
                               operation_name: str = "Processing") -> pd.DataFrame:
    """
    Process dataframe in chunks with progress tracking
    
    Args:
        df: DataFrame to process
        processing_func: Function to apply (receives chunk as input)
        chunk_size: Size of chunks to process
        operation_name: Name of operation for display
        
    Returns:
        Processed DataFrame
    """
    total_rows = len(df)
    total_bytes = df.memory_usage(deep=True).sum()
    
    tracker = ProcessingProgressTracker(total_rows, total_bytes, operation_name)
    
    progress_placeholder = st.empty()
    metrics_placeholder = st.empty()
    
    processed_chunks = []
    
    for i in range(0, total_rows, chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        processed_chunk = processing_func(chunk)
        processed_chunks.append(processed_chunk)
        
        # Update progress
        rows_done = min(i + chunk_size, total_rows)
        tracker.update(rows_done)
        
        # Display progress
        with progress_placeholder.container():
            display_processing_progress(tracker, show_details=True)
        
        time.sleep(0.01)  # Small delay for UI update
    
    # Clear placeholders and show final result
    progress_placeholder.empty()
    
    result_df = pd.concat(processed_chunks, ignore_index=True)
    
    with metrics_placeholder.container():
        st.success(f"✅ {operation_name} Complete!")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", f"{len(result_df):,}")
        with col2:
            st.metric("Total Time", tracker.get_elapsed_time())
        with col3:
            st.metric("Avg Speed", f"{tracker.speed_rows_per_second:.0f} rows/s")
    
    return result_df


def streamlit_file_upload_with_progress(file_label: str = "Upload File",
                                        file_types: list = ["csv", "xlsx"]) -> Optional[tuple]:
    """
    Streamlit file uploader with processing progress
    
    Returns:
        Tuple of (dataframe, filename) or None
    """
    uploaded_file = st.file_uploader(file_label, type=file_types)
    
    if uploaded_file:
        # Load file with progress
        with st.spinner("📂 Loading file..."):
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(uploaded_file)
                else:
                    st.error("Unsupported file format")
                    return None
                
                file_size_mb = uploaded_file.size / (1024 * 1024)
                st.success(f"✅ Loaded: {uploaded_file.name} ({file_size_mb:.2f} MB)")
                st.info(f"📊 Shape: {len(df):,} rows × {len(df.columns)} columns")
                
                return df, uploaded_file.name
            
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
                return None
    
    return None


# Example progress display for data merging
def show_merge_progress(old_df_rows: int, new_df_rows: int):
    """Show progress for data merge operation"""
    
    total_rows = old_df_rows + new_df_rows
    tracker = ProcessingProgressTracker(
        total_rows=total_rows,
        total_bytes=total_rows * 1000,  # Rough estimate
        operation_name="Merging Data"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Merge Summary")
        st.info(f"Old Data: {old_df_rows:,} rows")
        st.info(f"New Data: {new_df_rows:,} rows")
    
    with col2:
        st.subheader("⏱️ Estimated Time")
        # Simulate merge speed (typically very fast for concatenation)
        tracker.update(int(total_rows * 0.5))
        remaining = tracker.get_estimated_time_remaining()
        
        st.success(f"Estimated Total: < 1 second")
        st.success(f"Total Result: {total_rows:,} rows")
