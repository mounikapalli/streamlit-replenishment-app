"""
Email Integration Module for Daily Sales Data Collection
Automatically fetches sales data from email attachments
"""

import imaplib
import email
from email.mime.text import MIMEText
import smtplib
import pandas as pd
import io
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import streamlit as st

logger = logging.getLogger(__name__)

class EmailSalesIntegration:
    """Handle email-based sales data collection"""
    
    def __init__(self, email_address: str, email_password: str, imap_server: str = "imap.gmail.com"):
        """
        Initialize email integration
        
        Args:
            email_address: Gmail address
            email_password: Gmail app password (not regular password)
            imap_server: IMAP server address (default: Gmail)
        """
        self.email_address = email_address
        self.email_password = email_password
        self.imap_server = imap_server
        self.smtp_server = "smtp.gmail.com"
        
    def fetch_sales_emails(self, from_email: Optional[str] = None, 
                          days_back: int = 1, 
                          subject_keyword: str = "Sales") -> List[Dict]:
        """
        Fetch emails with sales data attachments
        
        Args:
            from_email: Filter emails from specific sender
            days_back: Number of days to look back
            subject_keyword: Keyword to search in subject line
            
        Returns:
            List of dicts containing email info and attachments
        """
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email_address, self.email_password)
            mail.select("INBOX")
            
            # Search for emails from past N days
            since_date = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            search_criteria = f'(SINCE "{since_date}" SUBJECT "{subject_keyword}")'
            
            if from_email:
                search_criteria = f'(SINCE "{since_date}" FROM "{from_email}" SUBJECT "{subject_keyword}")'
            
            status, messages = mail.search(None, search_criteria)
            email_ids = messages[0].split()
            
            emails_data = []
            
            for email_id in email_ids[-10:]:  # Get last 10 matching emails
                status, msg = mail.fetch(email_id, "(RFC822)")
                email_body = msg[0][1]
                email_message = email.message_from_bytes(email_body)
                
                email_info = {
                    "from": email_message["From"],
                    "subject": email_message["Subject"],
                    "date": email_message["Date"],
                    "attachments": []
                }
                
                # Extract attachments
                for part in email_message.walk():
                    if part.get_content_disposition() == "attachment":
                        filename = part.get_filename()
                        if filename and filename.endswith(('.csv', '.xlsx', '.xls')):
                            attachment_data = part.get_payload(decode=True)
                            email_info["attachments"].append({
                                "filename": filename,
                                "data": attachment_data,
                                "content_type": part.get_content_type()
                            })
                
                if email_info["attachments"]:
                    emails_data.append(email_info)
            
            mail.close()
            mail.logout()
            
            return emails_data
            
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            st.error(f"Error connecting to email: {str(e)}")
            return []
    
    def parse_sales_attachment(self, attachment_data: bytes, 
                               filename: str) -> Optional[pd.DataFrame]:
        """
        Parse sales data from email attachment
        
        Args:
            attachment_data: Binary attachment data
            filename: Original filename
            
        Returns:
            Pandas DataFrame or None if parsing fails
        """
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(attachment_data))
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(io.BytesIO(attachment_data))
            else:
                return None
            
            return df
            
        except Exception as e:
            logger.error(f"Error parsing attachment {filename}: {str(e)}")
            return None
    
    def merge_sales_data(self, existing_df: pd.DataFrame, 
                        new_df: pd.DataFrame,
                        duplicate_handling: str = "skip") -> pd.DataFrame:
        """
        Merge new sales data with existing data
        
        Args:
            existing_df: Existing sales data
            new_df: New sales data from email
            duplicate_handling: 'skip', 'update', or 'append'
            
        Returns:
            Merged DataFrame
        """
        try:
            if existing_df.empty:
                return new_df
            
            if duplicate_handling == "append":
                return pd.concat([existing_df, new_df], ignore_index=True)
            
            elif duplicate_handling == "skip":
                # Remove duplicates based on common columns
                common_cols = list(set(existing_df.columns) & set(new_df.columns))
                if common_cols:
                    new_df = new_df[~new_df[common_cols].isin(
                        existing_df[common_cols].to_dict(orient='list')
                    ).all(axis=1)]
                return pd.concat([existing_df, new_df], ignore_index=True)
            
            elif duplicate_handling == "update":
                # Update matching rows
                merged = existing_df.copy()
                for col in new_df.columns:
                    if col in merged.columns:
                        merged[col] = merged[col].combine_first(new_df[col])
                return merged
            
            return existing_df
            
        except Exception as e:
            logger.error(f"Error merging data: {str(e)}")
            return existing_df
    
    def send_confirmation_email(self, recipient_email: str, 
                                summary: str) -> bool:
        """
        Send confirmation email after processing
        
        Args:
            recipient_email: Email to send confirmation to
            summary: Summary of processed data
            
        Returns:
            True if successful
        """
        try:
            message = MIMEText(f"""
            Sales data has been successfully received and integrated.
            
            Processing Summary:
            {summary}
            
            Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """)
            
            message["Subject"] = "Sales Data - Integration Confirmation"
            message["From"] = self.email_address
            message["To"] = recipient_email
            
            with smtplib.SMTP_SSL(self.smtp_server, 465) as server:
                server.login(self.email_address, self.email_password)
                server.sendmail(self.email_address, recipient_email, message.as_string())
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending confirmation email: {str(e)}")
            return False


def streamlit_email_integration_ui():
    """Streamlit UI for email integration settings"""
    
    st.subheader("📧 Email Sales Data Integration")
    
    with st.expander("Configure Email Settings"):
        email_address = st.text_input(
            "Gmail Address",
            help="Your Gmail address"
        )
        
        email_password = st.text_input(
            "Gmail App Password",
            type="password",
            help="Use Gmail App Password, not your regular password. Get it from: https://myaccount.google.com/apppasswords"
        )
        
        sender_email = st.text_input(
            "Expected Sender Email (Optional)",
            help="Leave empty to accept from any sender"
        )
        
        days_back = st.slider(
            "Days to Look Back",
            min_value=1,
            max_value=30,
            value=1,
            help="How many days back to search for emails"
        )
        
        subject_keyword = st.text_input(
            "Subject Keyword",
            value="Sales",
            help="Keyword to search in email subject"
        )
        
        duplicate_handling = st.selectbox(
            "How to Handle Duplicates",
            options=["skip", "update", "append"],
            help="skip: Skip duplicates | update: Update existing data | append: Add all data"
        )
        
        return {
            "email_address": email_address,
            "email_password": email_password,
            "sender_email": sender_email if sender_email else None,
            "days_back": days_back,
            "subject_keyword": subject_keyword,
            "duplicate_handling": duplicate_handling
        }


def process_email_sales_data(email_config: Dict, existing_sales_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Main function to process email sales data
    
    Args:
        email_config: Email configuration dictionary
        existing_sales_df: Existing sales data
        
    Returns:
        Updated sales DataFrame or None
    """
    if not all([email_config.get("email_address"), email_config.get("email_password")]):
        st.warning("Please configure email settings first")
        return None
    
    try:
        email_integration = EmailSalesIntegration(
            email_address=email_config["email_address"],
            email_password=email_config["email_password"]
        )
        
        st.info("Fetching emails...")
        emails = email_integration.fetch_sales_emails(
            from_email=email_config.get("sender_email"),
            days_back=email_config.get("days_back", 1),
            subject_keyword=email_config.get("subject_keyword", "Sales")
        )
        
        if not emails:
            st.warning("No emails with attachments found")
            return None
        
        st.success(f"Found {len(emails)} email(s) with attachments")
        
        all_new_data = pd.DataFrame()
        
        for email_info in emails:
            st.write(f"📧 From: {email_info['from']} - {email_info['subject']}")
            
            for attachment in email_info["attachments"]:
                df = email_integration.parse_sales_attachment(
                    attachment["data"],
                    attachment["filename"]
                )
                
                if df is not None:
                    st.write(f"   ✅ Processed: {attachment['filename']} ({len(df)} rows)")
                    all_new_data = pd.concat([all_new_data, df], ignore_index=True)
        
        if all_new_data.empty:
            st.warning("No valid sales data found in attachments")
            return None
        
        # Merge with existing data
        merged_data = email_integration.merge_sales_data(
            existing_sales_df,
            all_new_data,
            duplicate_handling=email_config.get("duplicate_handling", "skip")
        )
        
        st.success(f"✅ Successfully integrated {len(all_new_data)} new records!")
        
        return merged_data
        
    except Exception as e:
        st.error(f"Error processing email data: {str(e)}")
        logger.error(f"Error: {str(e)}")
        return None
