import requests
import pandas as pd

# Example API URL
url = "https://api.ginesys.in/v1/sales"
params = {"start_date": "2025-10-01", "end_date": "2025-10-10"}
headers = {"Authorization": "Bearer YOUR_API_KEY"}

response = requests.get(url, headers=headers, params=params)
data = response.json()

df = pd.DataFrame(data['sales'])
df.to_excel("sales_data.xlsx", index=False)
