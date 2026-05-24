# 💰 Personal Finance Tracker

A command-line financial management application that helps users track income and expenses, maintain running balances, generate reports, and gain insights. Data is stored per user and per year, with support for manual entry and CSV uploads.

---

## 📁 Project Overview

- **Title:** Personal Finance Tracker  
- **Language:** Python 3.x  
- **Data Storage:** CSV files (per user/year)  
- **Core Libraries:** `pandas`, `csv`, `datetime`, `os`  
- **Architecture:** Object-Oriented Programming (OOP)

---

## 🛠️ Technologies Used

- **Python 3.6+**  
- **pandas** – Data manipulation and balance recomputation  
- **csv** – Report generation  
- **datetime** – Date/time parsing and formatting  
- **os** – File and directory management  

---

## ✨ Key Features

- 👤 **User & Year Management** – Separate data for each user and year  
- ➕ **Manual Transaction Entry** – Add income/expense with detailed fields  
- ✏️ **Edit / Delete Transactions** – Modify or remove existing entries  
- 🔍 **View with Filters** – Filter by date range, type, and category  
- 📂 **CSV Upload** – Bulk import transactions with validation  
- 📊 **Generate CSV Reports** – Export transactions and summary for any date range  
- 📈 **Yearly Summary** – Top channels, highest income/expense days, top beneficiaries  
- 💰 **Starting Balance** – Set and edit opening balance with automatic balance recomputation  
- ✅ **Robust Input Validation** – Prevents crashes from invalid data  

---

## 💻 System Requirements

- Python 3.6 or higher  
- pandas library (`pip install pandas`)  
- Works on Windows, macOS, Linux  

---

## 🧩 Implementation Details

### Class Structure

```python
class FinanceTracker:
    def __init__(self):                     # Setup directories, default state
    def _get_file_path(self)                # Build CSV path for transactions
    def _get_balance_file_path(self)        # Build path for starting balance
    def _load_starting_balance(self)        # Load from file, default 0.0
    def _save_starting_balance(self)        # Save starting balance to file
    def _recompute_balances(self)           # Recalculate running balance after changes
    def _ensure_starting_balance(self)      # Prompt for opening balance if missing
    def load_data(self)                     # Load transactions from CSV
    def save_data(self)                     # Save transactions to CSV
    def add_transaction(self)               # Manual entry
    def edit_transaction(self)              # Modify existing transaction
    def delete_transaction(self)            # Remove transaction
    def view_transactions(self)             # Display with optional filters
    def upload_csv(self)                    # Bulk import from CSV
    def generate_report(self)               # CSV report for date range
    def generate_summary(self)              # Console yearly insights
    def set_user_year(self)                 # Switch user/year context
    def set_starting_balance(self)          # Edit opening balance
    def run(self)                           # Main menu loop
```

### Data Storage

- **Transactions File:** `finance_data/{first}_{middle}_{last}_{year}.csv`  
- **Starting Balance File:** `finance_data/{first}_{middle}_{last}_{year}_start_balance.txt`  
- **Reports Directory:** `finance_data/reports/`  
- **CSV Columns:** `Date/Time`, `Type`, `Category`, `Channel`, `Amount`, `Description`, `Beneficiary`, `Balance`

### Date/Time Format

- **Storage & Display:** `"02 January 2025 10:42"` (day month year hour:minute)  
- **Parsing:** Uses `datetime.strptime` with `%d %B %Y %H:%M`  

### Balance Recalculation

- Every transaction addition, edit, deletion, or starting balance change triggers `_recompute_balances()`.  
- Sorts transactions by date/time, then iteratively updates the `Balance` column starting from `starting_balance`.

---

## 🧠 Challenges & Solutions

| Challenge | Solution | Impact |
|-----------|----------|--------|
| **Input Validation** – User may enter non‑numeric amounts, invalid types, or empty categories | Strict loops with try/except, positive amount checks, and predefined category lists; blank fields handled gracefully | Prevents crashes and ensures data integrity |
| **CSV Upload Issues** – Wrong file structure, missing columns, incorrect date format, negative amounts | Validate required columns, parse sample date, check amount >0, and standardise Type values before loading | Reliable bulk import without corrupting existing data |
| **Date Formatting** – Inconsistent parsing or writing of dates across different operations | Centralise date format string (`"%d %B %Y %H:%M"`); use `datetime.strptime` for input and `dt.strftime` for output | All dates are consistent, sortable, and human‑readable |
| **Opening Balance Error** – Starting balance not correctly factored into running balances or reports | Store balance in separate file; `_recompute_balances()` always uses `self.starting_balance` as base; report generation queries balance just before the period | Accurate running balance and period‑correct opening balance in reports |

---

## 🚀 Future Enhancements

### Short‑term
- Budget setting with spending alerts  
- Recurring transactions (monthly subscriptions)  
- Export to Excel/PDF  

### Medium‑term
- Web interface (Flask/Django)  
- Multi‑currency support  
- Graphical spending charts (matplotlib)  

### Long‑term
- Mobile app (React Native)  
- Cloud sync and multi‑device access  
- Automatic bank statement parsing (PDF/OFX)  

---

## 📦 Installation & Usage

### Setup

1. Ensure Python 3.6+ is installed.  
2. Install pandas:  
   ```bash
   pip install pandas
   ```  
3. Save the script as `finance_tracker.py` in a directory of your choice.  
4. Run the application:  
   ```bash
   python finance_tracker.py
   ```

### First Run

- You will be prompted to enter **first name**, **middle name (optional)**, **last name**, and **year**.  
- If no starting balance exists for that user/year, you must enter a positive opening balance.  
- Data files are automatically created in the `finance_data/` folder.

### Main Menu Options

| Option | Description |
|--------|-------------|
| 1 | Add transaction manually |
| 2 | Edit an existing transaction |
| 3 | Delete a transaction |
| 4 | View transactions (with date/type/category filters) |
| 5 | Upload CSV file (replaces all transactions) |
| 6 | Generate CSV report for a date range |
| 7 | Show yearly summary (console) |
| 8 | Switch to a different user or year |
| 9 | Edit starting balance for current year |
| 0 | Exit |

### CSV Upload Format

The CSV must have the following columns (exact names, case‑sensitive):

```
Date/Time,Type,Category,Channel,Amount,Description,Beneficiary
```

- **Date/Time:** `"02 January 2025 10:42"` format  
- **Type:** `Income` or `Expense`  
- **Amount:** Positive number (decimals allowed)  
- **Balance column is optional** – it will be recomputed automatically.

Example row:  
`02 January 2025 10:42,Income,Salary,Bank Transfer,5000.00,Monthly salary,Employer Inc.`

---

## 🎓 Learning Outcomes

- Object‑oriented design for data‑centric applications  
- File I/O with CSV and text files  
- Using `pandas` for data validation and transformation  
- Robust input validation and error handling  
- Date/time parsing and formatting  
- Generating user‑friendly reports and summaries  

---

## ✅ Conclusion

The Personal Finance Tracker is a practical, well‑structured Python application that demonstrates essential software engineering practices: data persistence, input validation, error recovery, and user‑centric reporting. Its modular design and clear separation of concerns make it easy to extend with new features or a graphical interface.
