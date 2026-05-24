"""
Personal Finance Tracker – Streamlit Web App with SQLite Storage

A web application to manage financial transactions, track running balances,
generate CSV reports, and display yearly insights. Data is stored in a SQLite
database, keyed by (first_name, middle_name, last_name, year).
"""

import csv
import io
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st


class FinanceTracker:
    """
    Manages personal finances for a specific user and year using SQLite.
    """

    def __init__(self, db_path="finance.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

        self.first_name = None
        self.middle_name = None
        self.last_name = None
        self.current_year = None
        self.df = None
        self.starting_balance = 0.0

    def _init_db(self):
        """Create the required tables if they do not exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                first_name TEXT NOT NULL,
                middle_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                starting_balance REAL NOT NULL DEFAULT 0.0,
                PRIMARY KEY (first_name, middle_name, last_name, year)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                middle_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                year INTEGER NOT NULL,
                date_time TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                channel TEXT,
                amount REAL NOT NULL,
                description TEXT,
                beneficiary TEXT,
                balance REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_user_year
            ON transactions (first_name, middle_name, last_name, year, date_time)
        """)
        self.conn.commit()

    def _load_starting_balance(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT starting_balance FROM user_settings
            WHERE first_name = ? AND middle_name = ? AND last_name = ? AND year = ?
        """, (self.first_name, self.middle_name, self.last_name, self.current_year))
        row = cursor.fetchone()
        self.starting_balance = row[0] if row else 0.0

    def _save_starting_balance(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_settings
            (first_name, middle_name, last_name, year, starting_balance)
            VALUES (?, ?, ?, ?, ?)
        """, (self.first_name, self.middle_name, self.last_name,
              self.current_year, self.starting_balance))
        self.conn.commit()

    def _save_starting_balance_inside_transaction(self, cursor):
        cursor.execute("""
            INSERT OR REPLACE INTO user_settings
            (first_name, middle_name, last_name, year, starting_balance)
            VALUES (?, ?, ?, ?, ?)
        """, (self.first_name, self.middle_name, self.last_name,
              self.current_year, self.starting_balance))

    def _recompute_balances(self):
        if self.df is None or self.df.empty:
            return
        try:
            self.df = self.df.sort_values('Date/Time')
            balance = self.starting_balance
            balances = []
            for _, row in self.df.iterrows():
                if row['Type'].lower() == 'income':
                    balance += row['Amount']
                else:
                    balance -= row['Amount']
                balances.append(balance)
            self.df['Balance'] = balances
        except (KeyError, ValueError) as error:
            st.error(f"Error recomputing balances: {error}")

    def load_data(self):
        query = """
            SELECT date_time, type, category, channel, amount,
                   description, beneficiary, balance
            FROM transactions
            WHERE first_name = ? AND middle_name = ? AND last_name = ? AND year = ?
            ORDER BY date_time
        """
        try:
            df = pd.read_sql_query(
                query,
                self.conn,
                params=(self.first_name, self.middle_name, self.last_name, self.current_year),
                parse_dates=['date_time']
            )
            if not df.empty:
                column_mapping = {
                    'date_time': 'Date/Time', 'type': 'Type', 'category': 'Category',
                    'channel': 'Channel', 'amount': 'Amount', 'description': 'Description',
                    'beneficiary': 'Beneficiary', 'balance': 'Balance'
                }
                df = df.rename(columns=column_mapping)
                df['Type'] = df['Type'].astype(str).str.capitalize()
                self.df = df[['Date/Time', 'Type', 'Category', 'Channel',
                              'Amount', 'Description', 'Beneficiary', 'Balance']]
            else:
                self.df = pd.DataFrame(columns=[
                    'Date/Time', 'Type', 'Category', 'Channel', 'Amount',
                    'Description', 'Beneficiary', 'Balance'
                ])
        except (sqlite3.Error, pd.errors.DatabaseError) as error:
            st.error(f"Error loading data: {error}")
            self.df = pd.DataFrame(columns=[
                'Date/Time', 'Type', 'Category', 'Channel', 'Amount',
                'Description', 'Beneficiary', 'Balance'
            ])
        self._load_starting_balance()
        self._recompute_balances()

    def save_data(self):
        if self.df is None:
            return
        cursor = self.conn.cursor()
        try:
            cursor.execute("BEGIN")
            cursor.execute("""
                DELETE FROM transactions
                WHERE first_name = ? AND middle_name = ? AND last_name = ? AND year = ?
            """, (self.first_name, self.middle_name, self.last_name, self.current_year))
            if not self.df.empty:
                for _, row in self.df.iterrows():
                    dt_str = row['Date/Time'].isoformat()
                    cursor.execute("""
                        INSERT INTO transactions
                        (first_name, middle_name, last_name, year, date_time,
                         type, category, channel, amount, description, beneficiary, balance)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        self.first_name, self.middle_name, self.last_name, self.current_year,
                        dt_str, row['Type'].lower(), row['Category'],
                        row['Channel'] if pd.notna(row['Channel']) else '',
                        row['Amount'], row['Description'] if pd.notna(row['Description']) else '',
                        row['Beneficiary'] if pd.notna(row['Beneficiary']) else '',
                        row['Balance']
                    ))
            self._save_starting_balance_inside_transaction(cursor)
            cursor.execute("COMMIT")
        except sqlite3.Error as error:
            self.conn.rollback()
            st.error(f"Error saving data: {error}")

    def ensure_starting_balance(self, opening_balance):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT starting_balance FROM user_settings
            WHERE first_name = ? AND middle_name = ? AND last_name = ? AND year = ?
        """, (self.first_name, self.middle_name, self.last_name, self.current_year))
        if cursor.fetchone() is None:
            if opening_balance <= 0:
                return "Opening balance must be greater than zero."
            self.starting_balance = opening_balance
            self._save_starting_balance()
            self._recompute_balances()
            self.save_data()
            return f"Starting balance set to ₦{opening_balance:,.2f}"
        else:
            self._load_starting_balance()
            return "Starting balance already exists."

    def update_starting_balance(self, new_balance):
        if new_balance <= 0:
            return False
        self.starting_balance = new_balance
        self._save_starting_balance()
        self._recompute_balances()
        self.save_data()
        return True

    # ------------------- Transaction Operations -------------------

    def add_transaction(self, date_obj, transaction_type, category,
                        amount, channel, description, beneficiary):
        if amount <= 0:
            return "Amount must be positive."
        if not category or not category.strip():
            return "Category cannot be empty."
        try:
            if self.df.empty:
                new_balance = self.starting_balance + (
                    amount if transaction_type == 'income' else -amount
                )
            else:
                last_balance = self.df.iloc[-1]['Balance']
                new_balance = last_balance + (
                    amount if transaction_type == 'income' else -amount
                )
        except (IndexError, KeyError):
            new_balance = self.starting_balance

        new_row = pd.DataFrame([{
            'Date/Time': date_obj,
            'Type': transaction_type.capitalize(),
            'Category': category.strip(),
            'Channel': channel.strip() if channel else "",
            'Amount': amount,
            'Description': description.strip() if description else "",
            'Beneficiary': beneficiary.strip() if beneficiary else "",
            'Balance': new_balance
        }])
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self._recompute_balances()
        self.save_data()
        return "Transaction added successfully."

    def edit_transaction(self, index, new_date, new_type, new_category,
                         new_channel, new_amount, new_description, new_beneficiary):
        if self.df.empty:
            return "No transactions to edit."
        if index < 0 or index >= len(self.df):
            return "Index out of range."
        if new_amount <= 0:
            return "Amount must be positive."
        if not new_category or not new_category.strip():
            return "Category cannot be empty."

        self.df.at[index, 'Date/Time'] = new_date
        self.df.at[index, 'Type'] = new_type.capitalize()
        self.df.at[index, 'Category'] = new_category.strip()
        self.df.at[index, 'Channel'] = new_channel.strip() if new_channel else ""
        self.df.at[index, 'Amount'] = new_amount
        self.df.at[index, 'Description'] = new_description.strip() if new_description else ""
        self.df.at[index, 'Beneficiary'] = new_beneficiary.strip() if new_beneficiary else ""

        self._recompute_balances()
        self.save_data()
        return "Transaction updated successfully."

    def delete_transaction(self, index):
        if self.df.empty:
            return "No transactions to delete."
        if index < 0 or index >= len(self.df):
            return "Index out of range."
        self.df = self.df.drop(index).reset_index(drop=True)
        self._recompute_balances()
        self.save_data()
        return "Transaction deleted."

    def search_transactions(self, start_date=None, end_date=None,
                            amount=None,
                            filter_type=None, filter_category=None,
                            channel_substring=None, beneficiary_substring=None,
                            description_substring=None):
        """Return DataFrame of transactions matching all criteria."""
        if self.df.empty:
            return self.df
        filtered = self.df.copy()
        if start_date:
            filtered = filtered[filtered['Date/Time'] >= pd.Timestamp(start_date)]
        if end_date:
            filtered = filtered[filtered['Date/Time'] <= pd.Timestamp(end_date)]
        if amount is not None:
            filtered = filtered[filtered['Amount'] == amount]
        if filter_type:
            filtered = filtered[filtered['Type'].str.lower() == filter_type.lower()]
        if filter_category:
            filtered = filtered[filtered['Category'].str.lower() == filter_category.lower()]
        if channel_substring:
            filtered = filtered[filtered['Channel'].str.contains(channel_substring, case=False, na=False)]
        if beneficiary_substring:
            filtered = filtered[filtered['Beneficiary'].str.contains(beneficiary_substring, case=False, na=False)]
        if description_substring:
            filtered = filtered[filtered['Description'].str.contains(description_substring, case=False, na=False)]
        return filtered

    # ------------------- CSV Operations -------------------

    def replace_with_csv(self, uploaded_file):
        """Replace all transactions with data from an uploaded CSV."""
        return self._process_csv(uploaded_file, append=False)

    def append_csv(self, uploaded_file):
        """Append transactions from an uploaded CSV to existing data."""
        return self._process_csv(uploaded_file, append=True)

    def _process_csv(self, uploaded_file, append=False):
        """Internal method to read CSV and either replace or append."""
        try:
            # Validate format using sample
            sample_df = pd.read_csv(uploaded_file, nrows=1)
            if 'Date/Time' not in sample_df.columns:
                return False, "CSV missing 'Date/Time' column."
            sample_date = str(sample_df['Date/Time'].iloc[0]).strip()
            try:
                datetime.strptime(sample_date, "%d %B %Y %H:%M")
            except ValueError:
                return False, ("Date/Time column does not match required format: "
                               "'02 January 2025 10:42'")

            uploaded_file.seek(0)
            uploaded_df = pd.read_csv(
                uploaded_file,
                parse_dates=['Date/Time'],
                date_format='%d %B %Y %H:%M'
            )

            required_columns = [
                'Date/Time', 'Type', 'Category', 'Channel', 'Amount',
                'Description', 'Beneficiary'
            ]
            for col in required_columns:
                if col not in uploaded_df.columns:
                    return False, f"Missing required column: {col}"

            uploaded_df['Amount'] = pd.to_numeric(uploaded_df['Amount'], errors='coerce')
            if uploaded_df['Amount'].isnull().any():
                return False, "Some Amount values are invalid (non-numeric)."
            if (uploaded_df['Amount'] <= 0).any():
                return False, "All Amounts must be positive."

            uploaded_df['Type'] = uploaded_df['Type'].astype(str).str.capitalize()
            invalid_types = ~uploaded_df['Type'].isin(['Income', 'Expense'])
            if invalid_types.any():
                return False, "Some rows have invalid Type (must be Income/Expense)."

            for col in ['Channel', 'Description', 'Beneficiary']:
                uploaded_df[col] = uploaded_df[col].fillna('').astype(str).str.strip()

            uploaded_df['Category'] = uploaded_df['Category'].fillna('').astype(str).str.strip()
            if (uploaded_df['Category'] == '').any():
                return False, "Category cannot be empty for any transaction."

            if 'Balance' in uploaded_df.columns:
                uploaded_df = uploaded_df.drop(columns=['Balance'])

            if append and self.df is not None and not self.df.empty:
                # Combine existing and new, then recompute balances
                combined = pd.concat([self.df, uploaded_df], ignore_index=True)
                self.df = combined
                self._recompute_balances()
                self.save_data()
                return True, f"Successfully appended {len(uploaded_df)} transactions."
            else:
                # Replace mode
                self.df = uploaded_df.copy()
                self._recompute_balances()
                self.save_data()
                return True, f"Successfully replaced with {len(uploaded_df)} transactions."
        except pd.errors.EmptyDataError:
            return False, "The CSV file is empty."
        except (KeyError, ValueError, pd.errors.ParserError) as error:
            return False, f"Error reading CSV: {error}"

    def generate_report_data(self, start_date, end_date):
        if self.df.empty:
            return None
        start_date = pd.Timestamp(start_date)
        end_date = pd.Timestamp(end_date)

        before_period = self.df['Date/Time'] < start_date
        if before_period.any():
            period_opening_balance = self.df[before_period].iloc[-1]['Balance']
        else:
            period_opening_balance = self.starting_balance

        period_mask = (self.df['Date/Time'] >= start_date) & (self.df['Date/Time'] <= end_date)
        period_df = self.df[period_mask].sort_values('Date/Time')

        if period_df.empty:
            total_income = total_expenses = 0.0
        else:
            total_income = period_df[period_df['Type'] == 'Income']['Amount'].sum()
            total_expenses = period_df[period_df['Type'] == 'Expense']['Amount'].sum()

        current_balance = period_opening_balance + total_income - total_expenses

        return {
            'period_opening_balance': period_opening_balance,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'current_balance': current_balance,
            'period_df': period_df
        }

    def get_yearly_summary(self):
        if self.df.empty:
            return None

        channel_counts = self.df['Channel'].value_counts().head(3)

        income_df = self.df[self.df['Type'] == 'Income'].copy()
        if not income_df.empty:
            income_df['Date'] = income_df['Date/Time'].dt.date
            daily_income = income_df.groupby('Date')['Amount'].sum()
            max_income_date = daily_income.idxmax()
            max_income_amount = daily_income.max()
        else:
            max_income_date = max_income_amount = None

        expense_df = self.df[self.df['Type'] == 'Expense'].copy()
        if not expense_df.empty:
            expense_df['Date'] = expense_df['Date/Time'].dt.date
            daily_expense = expense_df.groupby('Date')['Amount'].sum()
            max_expense_date = daily_expense.idxmax()
            max_expense_amount = daily_expense.max()
        else:
            max_expense_date = max_expense_amount = None

        top_income = income_df.nlargest(5, 'Amount')[['Amount', 'Category', 'Date/Time']] if not income_df.empty else None
        top_expense = expense_df.nlargest(5, 'Amount')[['Amount', 'Category', 'Date/Time']] if not expense_df.empty else None

        beneficiaries = self.df[self.df['Beneficiary'].notna() & (self.df['Beneficiary'].str.strip() != '')]
        if not beneficiaries.empty:
            expense_beneficiaries = beneficiaries[beneficiaries['Type'] == 'Expense']
            beneficiary_totals = expense_beneficiaries.groupby('Beneficiary')['Amount'].sum().sort_values(ascending=False).head(5) if not expense_beneficiaries.empty else None
        else:
            beneficiary_totals = None

        return {
            'channel_counts': channel_counts,
            'max_income_date': max_income_date,
            'max_income_amount': max_income_amount,
            'max_expense_date': max_expense_date,
            'max_expense_amount': max_expense_amount,
            'top_income': top_income,
            'top_expense': top_expense,
            'beneficiary_totals': beneficiary_totals
        }


# ------------------- Streamlit UI -------------------

def init_session_state():
    if "tracker" not in st.session_state:
        st.session_state.tracker = FinanceTracker()
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "success_message" not in st.session_state:
        st.session_state.success_message = None
    if "error_message" not in st.session_state:
        st.session_state.error_message = None
    # For edit/delete persistence
    if "edit_delete_selected_index" not in st.session_state:
        st.session_state.edit_delete_selected_index = None
    if "edit_delete_filtered_df" not in st.session_state:
        st.session_state.edit_delete_filtered_df = None
    if "edit_delete_action" not in st.session_state:
        st.session_state.edit_delete_action = None
    # For custom category in add form
    if "add_final_category" not in st.session_state:
        st.session_state.add_final_category = ""
    if "current_tab" not in st.session_state:
        st.session_state.current_tab = 0
    # Store last search parameters to detect changes
    if "last_search_params" not in st.session_state:
        st.session_state.last_search_params = {}


def display_messages():
    if st.session_state.success_message:
        st.success(st.session_state.success_message)
        st.session_state.success_message = None
    if st.session_state.error_message:
        st.error(st.session_state.error_message)
        st.session_state.error_message = None


def set_success_message(msg):
    st.session_state.success_message = msg


def set_error_message(msg):
    st.session_state.error_message = msg


def login_form():
    st.sidebar.header("Login / Select User & Year")
    with st.sidebar.form("login_form"):
        first = st.text_input("First name", value="").strip().lower()
        middle = st.text_input("Middle name (optional)", value="").strip().lower()
        last = st.text_input("Last name", value="").strip().lower()
        year = st.number_input("Year", min_value=2000, max_value=2100,
                               value=2025, step=1, format="%d")
        submitted = st.form_submit_button("Load / Switch User")
        if submitted:
            if not first or not last:
                set_error_message("First name and last name are required.")
                return
            try:
                tracker = st.session_state.tracker
                tracker.first_name = first
                tracker.middle_name = middle if middle else ""
                tracker.last_name = last
                tracker.current_year = int(year)
                tracker.load_data()
                st.session_state.logged_in = True
                set_success_message(f"Logged in as {first} {last} ({year})")
                st.rerun()
            except Exception as e:
                set_error_message(f"Login failed: {str(e)}")


def set_starting_balance_ui():
    tracker = st.session_state.tracker
    try:
        cursor = tracker.conn.cursor()
        cursor.execute("""
            SELECT starting_balance FROM user_settings
            WHERE first_name = ? AND middle_name = ? AND last_name = ? AND year = ?
        """, (tracker.first_name, tracker.middle_name, tracker.last_name, tracker.current_year))
        if cursor.fetchone() is None:
            st.warning(
                f"No starting balance for {tracker.first_name} {tracker.middle_name} "
                f"{tracker.last_name}, year {tracker.current_year}."
            )
            with st.form("start_balance_form"):
                opening = st.number_input(
                    "Opening balance (must be > 0)",
                    min_value=0.01, step=100.0, format="%.2f"
                )
                if st.form_submit_button("Set Starting Balance"):
                    try:
                        msg = tracker.ensure_starting_balance(opening)
                        if "error" not in msg.lower() and "already" not in msg.lower():
                            set_success_message(msg)
                            st.rerun()
                        else:
                            set_error_message(msg)
                    except Exception as e:
                        set_error_message(f"Failed to set balance: {str(e)}")
    except Exception as e:
        set_error_message(f"Error checking starting balance: {str(e)}")


def add_transaction_ui():
    st.subheader("Add Transaction")

    # Predefined categories
    all_categories = [
        'transportation', 'black/f tax', 'food', 'education', 'rent',
        'contribution/help', 'clothing', 'entertainment', 'data/airtime',
        'electricity', 'gadget&accessories', 'miscellaneous', 'repairs',
        'charges', 'subscription', 'self', 'refund',
        'salary', 'bonus', 'allowance', 'dividend'
    ]
    all_categories = sorted(set(all_categories))

    # Category selection (outside the form to allow dynamic updates)
    cat_option = st.selectbox(
        "Category (or choose '[new custom category]' to create a new one)",
        all_categories + ["[new custom category]"],
        key="cat_select"
    )

    # Handle custom category input
    if cat_option == "[new custom category]":
        custom_cat = st.text_input("Enter new category name", key="custom_cat_input").strip()
        final_category = custom_cat if custom_cat else ""
        st.session_state.add_final_category = final_category
    else:
        final_category = cat_option
        st.session_state.add_final_category = final_category

    # Main add form
    with st.form("add_transaction_form"):
        col1, col2 = st.columns(2)
        with col1:
            t_date = st.date_input("Date", datetime.now())
            t_time = st.time_input("Time", datetime.now().time())
        with col2:
            t_type = st.selectbox("Type", ["Income", "Expense"]).lower()
            amount = st.number_input("Amount", min_value=0.01, step=10.0, format="%.2f")

        channel = st.text_input("Channel", value="").strip()
        description = st.text_input("Description", value="").strip()
        beneficiary = st.text_input("Beneficiary", value="").strip()

        submitted = st.form_submit_button("Add Transaction")
        if submitted:
            # Use the stored final category
            category = st.session_state.add_final_category
            if not category:
                set_error_message("Category cannot be empty. Please select or enter a category.")
                return
            try:
                dt = datetime.combine(t_date, t_time)
                tracker = st.session_state.tracker
                msg = tracker.add_transaction(
                    dt, t_type, category, amount, channel, description, beneficiary
                )
                if "successfully" in msg.lower():
                    set_success_message(msg)
                    st.rerun()
                else:
                    set_error_message(msg)
            except Exception as e:
                set_error_message(f"Unexpected error: {str(e)}")


def search_and_select_transaction_ui():
    """Provide search fields, display matching transactions, and let user select one."""
    st.subheader("Search Transactions")
    tracker = st.session_state.tracker
    if tracker.df.empty:
        st.info("No transactions found.")
        return None, None

    # Get current search parameters
    with st.expander("Search Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("Start date", value=None, key="search_start")
            end_date = st.date_input("End date", value=None, key="search_end")
            filter_type = st.selectbox("Type", ["All", "Income", "Expense"], key="search_type")
        with col2:
            amount = st.number_input("Amount", min_value=0.0, value=0.0, step=10.0, key="search_amount")
            filter_category = st.text_input("Category (exact match)", value="", key="search_cat")
        with col3:
            channel_sub = st.text_input("Channel (contains)", value="", key="search_channel")
            beneficiary_sub = st.text_input("Beneficiary (contains)", value="", key="search_beneficiary")
            description_sub = st.text_input("Description (contains)", value="", key="search_desc")

    # Build current parameters dict
    current_params = {
        "start_date": start_date,
        "end_date": end_date,
        "filter_type": filter_type,
        "amount": amount,
        "filter_category": filter_category,
        "channel_sub": channel_sub,
        "beneficiary_sub": beneficiary_sub,
        "description_sub": description_sub,
    }

    # If any search parameter changed, clear stored selection
    if st.session_state.last_search_params != current_params:
        st.session_state.edit_delete_selected_index = None
        st.session_state.edit_delete_filtered_df = None
        st.session_state.last_search_params = current_params

    # Apply filters
    filtered = tracker.search_transactions(
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        amount=amount if amount > 0 else None,
        filter_type=None if filter_type == "All" else filter_type.lower(),
        filter_category=filter_category.strip() if filter_category else None,
        channel_substring=channel_sub.strip() if channel_sub else None,
        beneficiary_substring=beneficiary_sub.strip() if beneficiary_sub else None,
        description_substring=description_sub.strip() if description_sub else None,
    )

    if filtered.empty:
        st.info("No transactions match the search criteria.")
        return None, None

    # Prepare display dataframe
    display_df = filtered.copy()
    display_df['Date/Time'] = display_df['Date/Time'].dt.strftime("%d %b %Y %H:%M")
    st.dataframe(display_df, use_container_width=True)

    # Selection dropdown
    indices = list(filtered.index)
    if indices:
        selected_index = st.selectbox(
            "Select transaction to edit/delete",
            indices,
            format_func=lambda idx: f"{filtered.loc[idx, 'Date/Time'].strftime('%d %b %Y %H:%M')} | {filtered.loc[idx, 'Type']} | ₦{filtered.loc[idx, 'Amount']:,.2f} | {filtered.loc[idx, 'Category']}"
        )
        return selected_index, filtered
    return None, None


def edit_transaction_ui(selected_index, filtered_df):
    """Display edit form for the selected transaction."""
    tracker = st.session_state.tracker
    row = filtered_df.loc[selected_index]

    st.subheader("Edit Transaction")
    with st.form("edit_transaction_form"):
        new_date = st.date_input("Date", row['Date/Time'].date())
        new_time = st.time_input("Time", row['Date/Time'].time())
        new_type = st.selectbox(
            "Type", ["Income", "Expense"],
            index=0 if row['Type'] == 'Income' else 1
        )
        new_category = st.text_input("Category", row['Category']).strip()
        new_channel = st.text_input(
            "Channel", row['Channel'] if pd.notna(row['Channel']) else ""
        ).strip()
        new_amount = st.number_input(
            "Amount", min_value=0.01, value=float(row['Amount']), step=10.0
        )
        new_desc = st.text_input(
            "Description", row['Description'] if pd.notna(row['Description']) else ""
        ).strip()
        new_ben = st.text_input(
            "Beneficiary", row['Beneficiary'] if pd.notna(row['Beneficiary']) else ""
        ).strip()

        if st.form_submit_button("Save Changes"):
            if not new_category:
                set_error_message("Category cannot be empty.")
                return
            try:
                new_dt = datetime.combine(new_date, new_time)
                msg = tracker.edit_transaction(
                    selected_index, new_dt, new_type.lower(), new_category,
                    new_channel, new_amount, new_desc, new_ben
                )
                if "successfully" in msg:
                    set_success_message(msg)
                    # Clear stored selection after successful edit
                    st.session_state.edit_delete_selected_index = None
                    st.session_state.edit_delete_filtered_df = None
                    st.rerun()
                else:
                    set_error_message(msg)
            except Exception as e:
                set_error_message(f"Edit failed: {str(e)}")


def delete_transaction_ui(selected_index, filtered_df):
    """Confirm and delete the selected transaction."""
    tracker = st.session_state.tracker
    row = filtered_df.loc[selected_index]
    st.subheader("Delete Transaction")
    st.warning(f"Are you sure you want to delete this transaction?\n\n"
               f"Date: {row['Date/Time'].strftime('%d %b %Y %H:%M')}\n"
               f"Type: {row['Type']}\n"
               f"Amount: ₦{row['Amount']:,.2f}\n"
               f"Category: {row['Category']}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Delete"):
            try:
                msg = tracker.delete_transaction(selected_index)
                if "deleted" in msg:
                    set_success_message(msg)
                    # Clear stored selection after deletion
                    st.session_state.edit_delete_selected_index = None
                    st.session_state.edit_delete_filtered_df = None
                    st.rerun()
                else:
                    set_error_message(msg)
            except Exception as e:
                set_error_message(f"Delete failed: {str(e)}")
    with col2:
        if st.button("Cancel"):
            set_success_message("Operation cancelled.")
            # Clear stored selection to avoid immediate re-show
            st.session_state.edit_delete_selected_index = None
            st.session_state.edit_delete_filtered_df = None
            st.rerun()


def view_transactions_ui():
    st.subheader("Edit or Delete a Transaction")

    # If we have a stored selection from previous interaction, use it
    if st.session_state.edit_delete_selected_index is not None and st.session_state.edit_delete_filtered_df is not None:
        selected_index = st.session_state.edit_delete_selected_index
        filtered_df = st.session_state.edit_delete_filtered_df
        # Allow user to change action
        action = st.radio("Action", ["Edit", "Delete"], horizontal=True, key="persisted_action")
        st.session_state.edit_delete_action = action
    else:
        # Perform fresh search and selection (without auto-storing)
        selected_index, filtered_df = search_and_select_transaction_ui()
        if selected_index is None:
            return

        # Show action radio and proceed button
        action = st.radio("Action", ["Edit", "Delete"], horizontal=True, key="new_action")
        if st.button("Proceed"):
            st.session_state.edit_delete_selected_index = selected_index
            st.session_state.edit_delete_filtered_df = filtered_df
            st.session_state.edit_delete_action = action
            st.rerun()
        return

    # Now act based on the stored action
    action = st.session_state.edit_delete_action
    if action == "Edit":
        edit_transaction_ui(selected_index, filtered_df)
    else:
        delete_transaction_ui(selected_index, filtered_df)


def upload_csv_ui():
    st.subheader("Upload CSV File")
    st.markdown("""
    **Required CSV format:**
    - Columns: `Date/Time`, `Type`, `Category`, `Channel`, `Amount`, `Description`, `Beneficiary`
    - Date/Time format: `02 January 2025 10:42`
    - Type: `Income` or `Expense`
    - Amount: positive number
    """)
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        mode = st.radio("Upload mode", ["Replace all transactions", "Append to existing transactions"])
        if st.button("Process CSV"):
            try:
                tracker = st.session_state.tracker
                if mode == "Replace all transactions":
                    success, msg = tracker.replace_with_csv(uploaded_file)
                else:
                    success, msg = tracker.append_csv(uploaded_file)
                if success:
                    set_success_message(msg)
                    st.rerun()
                else:
                    set_error_message(msg)
            except Exception as e:
                set_error_message(f"Unexpected error during upload: {str(e)}")


def generate_report_ui():
    st.subheader("Generate Report")
    tracker = st.session_state.tracker
    if tracker.df.empty:
        st.info("No transactions available. Add some first.")
        return

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start date", value=datetime.now().replace(day=1))
    with col2:
        end_date = st.date_input("End date", value=datetime.now())

    if st.button("Generate Report CSV"):
        if start_date > end_date:
            set_error_message("Start date must be before end date.")
            return
        try:
            report_data = tracker.generate_report_data(start_date, end_date)
            if report_data is None or report_data['period_df'].empty:
                st.info("No transactions in selected period.")
                return

            output = io.StringIO()
            writer = csv.writer(output)
            name_parts = [tracker.first_name, tracker.middle_name, tracker.last_name]
            full_name = " ".join([p.capitalize() for p in name_parts if p]) or "Unknown User"

            writer.writerow(["Field", "Value"])
            writer.writerow(["Name", full_name])
            writer.writerow([
                "Date Range",
                f"{start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}"
            ])
            writer.writerow(["Total Income", f"₦{report_data['total_income']:,.2f}"])
            writer.writerow(["Total Expenses", f"₦{report_data['total_expenses']:,.2f}"])
            writer.writerow(["Opening Balance", f"₦{report_data['period_opening_balance']:,.2f}"])
            writer.writerow(["Current Balance", f"₦{report_data['current_balance']:,.2f}"])
            writer.writerow([])

            headers = [
                'Date/Time', 'Type', 'Category', 'Channel', 'Amount',
                'Description', 'Beneficiary', 'Balance'
            ]
            writer.writerow(headers)

            for _, row in report_data['period_df'].iterrows():
                date_str = row['Date/Time'].strftime("%d %B %Y %H:%M")
                writer.writerow([
                    date_str, row['Type'], row['Category'],
                    row['Channel'] if pd.notna(row['Channel']) else '',
                    row['Amount'],
                    row['Description'] if pd.notna(row['Description']) else '',
                    row['Beneficiary'] if pd.notna(row['Beneficiary']) else '',
                    row['Balance']
                ])

            st.download_button(
                label="Download Report CSV",
                data=output.getvalue(),
                file_name=(
                    f"report_{tracker.first_name}_{tracker.last_name}_"
                    f"{tracker.current_year}_{start_date.strftime('%Y%m%d')}_to_"
                    f"{end_date.strftime('%Y%m%d')}.csv"
                ),
                mime="text/csv"
            )
            set_success_message("Report generated successfully! Click the button above to download.")
        except Exception as e:
            set_error_message(f"Failed to generate report: {str(e)}")


def yearly_summary_ui():
    st.subheader("Yearly Summary")
    tracker = st.session_state.tracker
    try:
        summary = tracker.get_yearly_summary()
        if summary is None:
            st.info("No transactions found for the year.")
            return

        st.markdown("### Top 3 Payment Channels")
        if summary['channel_counts'].empty:
            st.write("No channel data available.")
        else:
            for channel, count in summary['channel_counts'].items():
                st.write(f"- **{channel}**: {count} transaction(s)")

        st.markdown("### Highest Income Day")
        if summary['max_income_date'] is not None:
            st.write(
                f"**{summary['max_income_date'].strftime('%d-%m-%Y')}** – "
                f"₦{summary['max_income_amount']:,.2f}"
            )
        else:
            st.write("No income transactions.")

        st.markdown("### Highest Expense Day")
        if summary['max_expense_date'] is not None:
            st.write(
                f"**{summary['max_expense_date'].strftime('%d-%m-%Y')}** – "
                f"₦{summary['max_expense_amount']:,.2f}"
            )
        else:
            st.write("No expense transactions.")

        st.markdown("### Top 5 Income Transactions")
        if summary['top_income'] is not None:
            for i, row in summary['top_income'].iterrows():
                st.write(
                    f"{i+1}. ₦{row['Amount']:,.2f} – {row['Category']} "
                    f"(on {row['Date/Time'].strftime('%d-%m-%Y')})"
                )
        else:
            st.write("None.")

        st.markdown("### Top 5 Expense Transactions")
        if summary['top_expense'] is not None:
            for i, row in summary['top_expense'].iterrows():
                st.write(
                    f"{i+1}. ₦{row['Amount']:,.2f} – {row['Category']} "
                    f"(on {row['Date/Time'].strftime('%d-%m-%Y')})"
                )
        else:
            st.write("None.")

        st.markdown("### Top 5 Beneficiaries (Expenses)")
        if summary['beneficiary_totals'] is not None:
            for beneficiary, amount in summary['beneficiary_totals'].items():
                st.write(f"- **{beneficiary}**: ₦{amount:,.2f}")
        else:
            st.write("No beneficiary data available.")
    except Exception as e:
        set_error_message(f"Error loading summary: {str(e)}")


def edit_starting_balance_ui():
    st.subheader("Edit Starting Balance")
    tracker = st.session_state.tracker
    st.write(f"Current starting balance: ₦{tracker.starting_balance:,.2f}")
    with st.form("edit_start_balance"):
        new_balance = st.number_input(
            "New starting balance (must be > 0)",
            min_value=0.01, step=100.0, format="%.2f"
        )
        if st.form_submit_button("Update"):
            if new_balance <= 0:
                set_error_message("Balance must be positive.")
            else:
                try:
                    if tracker.update_starting_balance(new_balance):
                        set_success_message(f"Starting balance updated to ₦{new_balance:,.2f}")
                        st.rerun()
                    else:
                        set_error_message("Failed to update starting balance.")
                except Exception as e:
                    set_error_message(f"Update failed: {str(e)}")


def main():
    st.set_page_config(page_title="Finance Tracker", layout="wide")
    st.title("💰 Personal Finance Tracker")

    init_session_state()
    display_messages()

    if not st.session_state.logged_in:
        login_form()
        return

    tracker = st.session_state.tracker
    st.sidebar.success(
        f"Logged in as: {tracker.first_name} {tracker.middle_name} "
        f"{tracker.last_name} ({tracker.current_year})"
    )
    if st.sidebar.button("Logout / Switch User"):
        st.session_state.logged_in = False
        # Clear edit/delete persistence
        st.session_state.edit_delete_selected_index = None
        st.session_state.edit_delete_filtered_df = None
        set_success_message("Logged out successfully.")
        st.rerun()

    set_starting_balance_ui()

    # Custom tab bar using radio to keep selection across reruns
    tab_names = ["➕ Add", "✏️ Edit/Delete", "📤 Upload CSV", "📊 Report", "📈 Summary", "⚙️ Settings"]
    selected_tab = st.radio(
        "Navigation",
        tab_names,
        index=st.session_state.current_tab,
        horizontal=True,
        key="tab_radio",
        on_change=lambda: setattr(st.session_state, "current_tab", tab_names.index(st.session_state.tab_radio))
    )
    st.session_state.current_tab = tab_names.index(selected_tab)

    if selected_tab == "➕ Add":
        add_transaction_ui()
    elif selected_tab == "✏️ Edit/Delete":
        view_transactions_ui()
    elif selected_tab == "📤 Upload CSV":
        upload_csv_ui()
    elif selected_tab == "📊 Report":
        generate_report_ui()
    elif selected_tab == "📈 Summary":
        yearly_summary_ui()
    elif selected_tab == "⚙️ Settings":
        edit_starting_balance_ui()


if __name__ == "__main__":
    main()