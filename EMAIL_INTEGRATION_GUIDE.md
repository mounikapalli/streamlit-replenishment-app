# Email Sales Data Integration Guide

## Overview
Automatically receive daily sales data via email and integrate it into your Streamlit app.

## Setup Instructions

### 1. Gmail Configuration (Required for Email Integration)

**Step 1: Enable 2-Factor Authentication**
- Go to [Google Account Security](https://myaccount.google.com/security)
- Scroll to "How you sign in to Google"
- Enable "2-Step Verification"

**Step 2: Generate App Password**
- Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
- Select "Mail" and "Windows Computer"
- Google will generate a 16-character password
- **Save this password** - you'll need it in the app

### 2. Configure in Your App

In the Streamlit app sidebar:
1. Navigate to **Settings → Email Integration**
2. Enter your Gmail address
3. Paste your App Password
4. (Optional) Specify sender email if you only want data from specific people
5. Set how many days back to look for emails
6. Choose how to handle duplicates

### 3. Email Setup at Your Source

**Your store/system should send daily sales emails with:**
- Subject: Contains "Sales" (or your custom keyword)
- Attachment: CSV or Excel file with columns:
  - `Date` or `DATE`
  - `Store` or `STORE_ID`
  - `SKU` or `PRODUCT_ID`
  - `Quantity` or `QTY`
  - `Amount` or `SALES`

**Example filename:** `Sales_2025-01-20.csv` or `Daily_Sales_Report.xlsx`

## Usage

### Manual Processing
1. Click "Process Email Sales Data"
2. App will fetch emails from the last N days
3. Automatically parse and integrate data
4. View summary of processed records

### How It Works
- Connects to your Gmail inbox via IMAP
- Searches for emails matching your criteria
- Extracts CSV/Excel attachments
- Parses sales data
- Merges with existing data (avoiding duplicates)
- Updates your sales database

## Duplicate Handling Options

- **skip**: Ignores duplicates (adds only new records)
- **update**: Updates existing records with new values
- **append**: Adds all records (may create duplicates)

## Security Notes

⚠️ **Important:**
- Use App Passwords, NOT your regular Gmail password
- Never share your App Password
- It only works for Gmail/Google accounts
- Revoke the password anytime from App Passwords page if needed

## Troubleshooting

**Error: "Invalid login"**
- Verify you're using Gmail App Password (not regular password)
- Ensure 2-Factor Authentication is enabled

**Error: "IMAP access not enabled"**
- Go to [Account Security](https://myaccount.google.com/security)
- Allow "Less secure app access" (if you can't use App Passwords)

**No emails found**
- Check email subject contains your keyword
- Verify sender matches (if filter is set)
- Try increasing "Days to Look Back"

**Attachments not recognized**
- Ensure files are .csv or .xlsx format
- Check file contains expected columns
- Try downloading the file manually to verify it's valid

## Column Mapping

The system will automatically recognize these common column names:

**Date**: `date`, `Date`, `DATE`, `timestamp`, `Timestamp`
**Store**: `store`, `Store`, `STORE`, `store_id`, `Store_ID`
**SKU**: `sku`, `SKU`, `product_id`, `Product_ID`
**Quantity**: `quantity`, `Quantity`, `QTY`, `qty`
**Amount**: `amount`, `Amount`, `sales`, `Sales`, `SALES`

## Scheduled Automation (Optional)

To run email collection automatically every day at a set time:

1. Use Windows Task Scheduler or cron job
2. Run: `streamlit run Streamlit_rep_app_final.py`
3. Configure email in the settings
4. System will check for new emails at startup

---

Need help? Check the email integration settings in the app for more options!
