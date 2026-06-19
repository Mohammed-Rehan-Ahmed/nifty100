import openpyxl

missing_tickers = [
    'ULTRACEMCO', 'UNIONBANK', 'UNITDSPR', 'VBL', 
    'VEDL', 'WIPRO', 'ZOMATO', 'ZYDUSLIFE', 'AGTL'
]

file_path = "data/raw/companies.xlsx"

print(f"Opening {file_path}...")
wb = openpyxl.load_workbook(file_path)
ws = wb.active

print("Appending missing tickers...")
for ticker in missing_tickers:
    # id is the first column, fill the other 11 columns with placeholders
    row_data = [ticker] + ["Placeholder"] * 11
    ws.append(row_data)

wb.save(file_path)
print("✨ Successfully patched companies.xlsx without altering your headers!")