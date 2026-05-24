"""
Personal Finance Tracker

A command-line application to manage financial transactions, track balances,
generate reports, and provide insights. Data is stored per user and year.
"""

import csv
import os
import sys
from datetime import datetime
import pandas as pd


class FinanceTracker:
    """
    Manages personal finances for a specific user and year.

    Attributes:
        data_dir (str): Root directory for storing data files.
        reports_dir (str): Subdirectory for generated report CSV files.
        first_name (str): User's first name (lowercase).
        middle_name (str): User's middle name (lowercase, may be empty).
        last_name (str): User's last name (lowercase).
        current_year (int): Year for which transactions are tracked.
        df (pd.DataFrame): DataFrame holding all transactions.
        starting_balance (float): Initial balance at the beginning of the year.
    """

    def __init__(self):
        """Initialize the finance tracker by setting up directories and default state."""
        # Main data directory
        self.data_dir = "finance_data"
        os.makedirs(self.data_dir, exist_ok=True)

        # Subdirectory for reports
        self.reports_dir = os.path.join(self.data_dir, "reports")
        os.makedirs(self.reports_dir, exist_ok=True)

        # User identification
        self.first_name = None
        self.middle_name = None
        self.last_name = None
        self.current_year = None

        # Transaction data and balance
        self.df = None
        self.starting_balance = 0.0

    # ------------------- Helper Methods -------------------

    def _get_file_path(self):
        """
        Generate the CSV file path for the current user and year.

        Returns:
            str: Full path to the transactions CSV file.
        """
        name_part = f"{self.first_name}_{self.middle_name}_{self.last_name}"
        return os.path.join(self.data_dir, f"{name_part}_{self.current_year}.csv")

    def _get_balance_file_path(self):
        """
        Generate the text file path for the starting balance.

        Returns:
            str: Full path to the starting balance file.
        """
        name_part = f"{self.first_name}_{self.middle_name}_{self.last_name}"
        return os.path.join(self.data_dir, f"{name_part}_{self.current_year}_start_balance.txt")

    def _load_starting_balance(self):
        """Load the starting balance from the file; default to 0.0 on error or missing file."""
        balance_file = self._get_balance_file_path()
        if os.path.exists(balance_file):
            try:
                with open(balance_file, 'r', encoding='utf-8') as file:
                    self.starting_balance = float(file.read().strip())
            except (ValueError, IOError) as error:
                print(f"Error reading starting balance file: {error}. Using 0.0 as balance.")
                self.starting_balance = 0.0
        else:
            self.starting_balance = 0.0

    def _save_starting_balance(self):
        """Save the current starting balance to the file."""
        balance_file = self._get_balance_file_path()
        try:
            with open(balance_file, 'w', encoding='utf-8') as file:
                file.write(str(self.starting_balance))
        except IOError as error:
            print(f"Error saving starting balance: {error}")

    def _recompute_balances(self):
        """
        Recalculate the running balance for all transactions.

        Sorts transactions by date/time, then updates the 'Balance' column
        based on the starting balance and each transaction's type and amount.
        """
        if self.df is None or self.df.empty:
            return
        try:
            # Ensure chronological order
            self.df = self.df.sort_values('Date/Time')
            current_balance = self.starting_balance
            balances = []

            for _, row in self.df.iterrows():
                if row['Type'].lower() == 'income':
                    current_balance += row['Amount']
                else:  # expense
                    current_balance -= row['Amount']
                balances.append(current_balance)

            self.df['Balance'] = balances
        except Exception as error:
            print(f"Error recomputing balances: {error}")

    def _ensure_starting_balance(self):
        """
        Ensure a starting balance exists for the current user/year.

        If no balance file is found, prompts the user to enter a positive opening balance.
        Otherwise, loads the existing balance.
        """
        balance_file = self._get_balance_file_path()
        if not os.path.exists(balance_file):
            print(f"\nNo starting balance found for {self.first_name} {self.middle_name} "
                  f"{self.last_name}, year {self.current_year}.")
            while True:
                try:
                    opening_balance = float(
                        input("Please enter the opening balance for this year (must be > 0): ")
                    )
                    if opening_balance <= 0:
                        print("Opening balance must be greater than zero.")
                        continue
                    self.starting_balance = opening_balance
                    self._save_starting_balance()
                    self._recompute_balances()
                    self.save_data()
                    print(f"Starting balance set to ₦{opening_balance:,.2f}")
                    break
                except ValueError:
                    print("Invalid number. Please enter a numeric value.")
        else:
            self._load_starting_balance()

    def load_data(self):
        """
        Load transaction data from the CSV file for the current user/year.

        If the file does not exist or cannot be read, initializes an empty DataFrame.
        Also loads the starting balance and recomputes balances to ensure consistency.
        """
        file_path = self._get_file_path()
        if os.path.exists(file_path):
            try:
                data_frame = pd.read_csv(
                    file_path,
                    parse_dates=['Date/Time'],
                    date_format='%d %B %Y %H:%M'
                )
                data_frame['Amount'] = pd.to_numeric(data_frame['Amount'])
                data_frame['Balance'] = pd.to_numeric(data_frame['Balance'])
                self.df = data_frame
            except Exception as error:
                print(f"Error loading data file: {error}. Starting with an empty dataset.")
                self.df = pd.DataFrame(columns=[
                    'Date/Time', 'Type', 'Category', 'Channel', 'Amount',
                    'Description', 'Beneficiary', 'Balance'
                ])
        else:
            self.df = pd.DataFrame(columns=[
                'Date/Time', 'Type', 'Category', 'Channel', 'Amount',
                'Description', 'Beneficiary', 'Balance'
            ])

        self._load_starting_balance()
        self._recompute_balances()

    def save_data(self):
        """
        Save the current transaction DataFrame to a CSV file.

        Formats the Date/Time column as required ('02 January 2025 10:42').
        Also saves the starting balance to its separate file.
        """
        try:
            if self.df is not None and not self.df.empty:
                file_path = self._get_file_path()
                df_to_save = self.df.copy()
                df_to_save['Date/Time'] = df_to_save['Date/Time'].dt.strftime("%d %B %Y %H:%M")
                df_to_save.to_csv(file_path, index=False)
            self._save_starting_balance()
        except Exception as error:
            print(f"Error saving data: {error}")

    # ------------------- Transaction Operations -------------------

    def add_transaction(self):
        """
        Manually add a single transaction.

        Prompts the user for all required fields, validates input,
        computes the new running balance, and saves the updated data.
        """
        self._ensure_starting_balance()

        print("\n--- Add New Transaction ---")

        # Date/Time input with strict format
        while True:
            date_string = input(
                "Date/Time (format: '02 January 2025 10:42', empty for now): "
            ).strip()
            if not date_string:
                date_object = datetime.now()
                break
            try:
                date_object = datetime.strptime(date_string, "%d %B %Y %H:%M")
                break
            except ValueError:
                print("Invalid format. Please use: '02 January 2025 10:42'")

        # Transaction type (Income / Expense)
        while True:
            transaction_type = input("Type (Income/Expense): ").strip().lower()
            if transaction_type in ['income', 'expense']:
                break
            print("Type must be 'Income' or 'Expense'.")

        # Predefined categories
        expense_categories = [
            'transportation', 'black/f tax', 'food', 'education', 'rent',
            'contribution/help', 'clothing', 'entertainment', 'data/airtime',
            'electricity', 'gadget&accessories', 'miscellaneous', 'repairs',
            'charges', 'subscription', 'self', 'refund'
        ]
        income_categories = ['salary', 'bonus', 'allowance', 'dividend', 'self']
        category_list = expense_categories if transaction_type == 'expense' else income_categories
        print(f"Predefined categories: {', '.join(category_list)}")

        category = input("Category (or type 'new' to create a new one): ").strip()
        if not category:
            print("Category cannot be empty. Using 'miscellaneous'.")
            category = 'miscellaneous'
        elif category.lower() == 'new':
            category = input("Enter new category name: ").strip()
            if not category:
                category = 'miscellaneous'
        elif category.lower() not in [cat.lower() for cat in category_list]:
            print(f"Warning: '{category}' is not in predefined list. "
                  "It will be saved as a custom category.")

        # Amount (positive number)
        while True:
            try:
                amount = float(input("Amount: "))
                if amount <= 0:
                    print("Amount must be positive.")
                    continue
                break
            except ValueError:
                print("Invalid number. Please enter a positive amount.")

        channel = input("Channel: ").strip()
        description = input("Description: ").strip()
        beneficiary = input("Beneficiary: ").strip()

        # Compute new running balance
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
        except Exception as error:
            print(f"Error computing balance: {error}. Using starting balance as fallback.")
            new_balance = self.starting_balance

        # Create and append the new transaction
        new_row = pd.DataFrame([{
            'Date/Time': date_object,
            'Type': transaction_type.capitalize(),
            'Category': category,
            'Channel': channel,
            'Amount': amount,
            'Description': description,
            'Beneficiary': beneficiary,
            'Balance': new_balance
        }])
        self.df = pd.concat([self.df, new_row], ignore_index=True)
        self._recompute_balances()
        self.save_data()
        print("Transaction added successfully.")

    def edit_transaction(self):
        """
        Edit an existing transaction by its index.

        Displays all transactions with indices, then prompts for new values.
        Leaves fields unchanged if input is left blank.
        """
        if self.df.empty:
            print("No transactions to edit.")
            return

        self.view_transactions(show_index=True)
        try:
            index_input = input("\nEnter the index of the transaction to edit: ").strip()
            if not index_input:
                print("No index entered. Operation cancelled.")
                return
            index = int(index_input)
            if index < 0 or index >= len(self.df):
                print("Index out of range.")
                return

            current_row = self.df.iloc[index]
            print(f"\nEditing transaction #{index} (current values shown in brackets):")
            print("Leave field blank to keep current value.\n")

            # Date/Time
            current_date_str = current_row['Date/Time'].strftime("%d %B %Y %H:%M")
            new_date_string = input(f"Date/Time [{current_date_str}]: ").strip()
            if new_date_string:
                try:
                    new_date = datetime.strptime(new_date_string, "%d %B %Y %H:%M")
                except ValueError:
                    print("Invalid date format. Keeping original.")
                    new_date = current_row['Date/Time']
            else:
                new_date = current_row['Date/Time']

            # Type
            current_type = current_row['Type']
            new_type_input = input(f"Type (Income/Expense) [{current_type}]: ").strip().lower()
            if new_type_input:
                if new_type_input not in ['income', 'expense']:
                    print("Invalid type. Keeping original.")
                    new_type = current_type
                else:
                    new_type = new_type_input.capitalize()
            else:
                new_type = current_type

            # Category
            current_category = current_row['Category']
            new_category = input(f"Category [{current_category}]: ").strip()
            if not new_category:
                new_category = current_category

            # Channel
            current_channel = current_row['Channel'] if pd.notna(current_row['Channel']) else ""
            new_channel = input(f"Channel [{current_channel}]: ").strip()
            if not new_channel:
                new_channel = current_channel

            # Amount (positive)
            current_amount = current_row['Amount']
            while True:
                try:
                    new_amount_string = input(f"Amount [{current_amount:.2f}]: ").strip()
                    if not new_amount_string:
                        new_amount = current_amount
                        break
                    new_amount = float(new_amount_string)
                    if new_amount <= 0:
                        print("Amount must be positive.")
                        continue
                    break
                except ValueError:
                    print("Invalid number. Please enter a positive amount.")

            # Description
            current_description = (
                current_row['Description'] if pd.notna(current_row['Description']) else ""
            )
            new_description = input(f"Description [{current_description}]: ").strip()
            if not new_description:
                new_description = current_description

            # Beneficiary
            current_beneficiary = (
                current_row['Beneficiary'] if pd.notna(current_row['Beneficiary']) else ""
            )
            new_beneficiary = input(f"Beneficiary [{current_beneficiary}]: ").strip()
            if not new_beneficiary:
                new_beneficiary = current_beneficiary

            # Apply updates
            self.df.at[index, 'Date/Time'] = new_date
            self.df.at[index, 'Type'] = new_type
            self.df.at[index, 'Category'] = new_category
            self.df.at[index, 'Channel'] = new_channel
            self.df.at[index, 'Amount'] = new_amount
            self.df.at[index, 'Description'] = new_description
            self.df.at[index, 'Beneficiary'] = new_beneficiary

            self._recompute_balances()
            self.save_data()
            print("Transaction updated successfully and balances recomputed.")

        except ValueError:
            print("Invalid input. Please enter a valid number for the index.")
        except Exception as error:
            print(f"Unexpected error during edit: {error}")

    def delete_transaction(self):
        """Delete a transaction by its index after confirmation."""
        if self.df.empty:
            print("No transactions to delete.")
            return

        self.view_transactions(show_index=True)
        try:
            index_input = input("Enter the index of the transaction to delete: ").strip()
            if not index_input:
                print("No index entered. Operation cancelled.")
                return
            index = int(index_input)
            if index < 0 or index >= len(self.df):
                print("Index out of range.")
                return

            confirm = input(f"Delete transaction #{index}? (y/n): ").strip().lower()
            if confirm == 'y':
                self.df = self.df.drop(index).reset_index(drop=True)
                self._recompute_balances()
                self.save_data()
                print("Transaction deleted.")
            else:
                print("Deletion cancelled.")
        except ValueError:
            print("Invalid index. Please enter a number.")
        except Exception as error:
            print(f"Error deleting transaction: {error}")

    def view_transactions(self, show_index=False):
        """
        Display transactions with optional date, type, and category filters.

        Args:
            show_index (bool): If True, includes the DataFrame index in the output.
        """
        if self.df.empty:
            print("No transactions found.")
            return

        print("\n--- View Transactions ---")
        print("Apply filters (leave blank to skip):")
        start_date_string = input("Start date (DD-MM-YYYY): ").strip()
        end_date_string = input("End date (DD-MM-YYYY): ").strip()
        filter_type = input("Type (Income/Expense, or blank for both): ").strip().lower()
        filter_category = input("Category (or blank for all): ").strip()

        filtered_df = self.df.copy()
        try:
            if start_date_string:
                start_date = datetime.strptime(start_date_string, "%d-%m-%Y")
                filtered_df = filtered_df[filtered_df['Date/Time'] >= start_date]
            if end_date_string:
                end_date = datetime.strptime(end_date_string, "%d-%m-%Y")
                filtered_df = filtered_df[filtered_df['Date/Time'] <= end_date]
        except ValueError:
            print("Invalid date format. Please use DD-MM-YYYY.")
            return

        if filter_type:
            filtered_df = filtered_df[filtered_df['Type'].str.lower() == filter_type]
        if filter_category:
            filtered_df = filtered_df[filtered_df['Category'].str.lower() == filter_category.lower()]

        if filtered_df.empty:
            print("No transactions match the filters.")
            return

        display_df = filtered_df.copy()
        display_df['Date/Time'] = display_df['Date/Time'].dt.strftime("%d %B %Y %H:%M")
        if show_index:
            display_df.insert(0, 'Index', display_df.index)
        print(display_df.to_string(index=False))

    def upload_csv(self):
        """
        Upload a CSV file to replace all existing transactions.

        Validates the file structure, date format, amount positivity, and type values.
        Recomputes balances after successful upload.
        """
        if not self.df.empty:
            confirm = input(
                "WARNING: Existing transactions will be REPLACED. Continue? (y/n): "
            ).strip().lower()
            if confirm != 'y':
                print("Upload cancelled.")
                return

        file_path = input("Enter the path to the CSV file: ").strip()
        if not os.path.exists(file_path):
            print("File not found.")
            return

        try:
            # Quick validation: check first row's date format
            sample_df = pd.read_csv(file_path, nrows=1)
            if 'Date/Time' not in sample_df.columns:
                print("CSV missing 'Date/Time' column.")
                return

            sample_date = sample_df['Date/Time'].iloc[0]
            try:
                datetime.strptime(sample_date, "%d %B %Y %H:%M")
            except ValueError:
                print("Date/Time column does not match required format: '02 January 2025 10:42'")
                return

            # Read full CSV with date parsing
            uploaded_df = pd.read_csv(
                file_path,
                parse_dates=['Date/Time'],
                date_format='%d %B %Y %H:%M'
            )

            # Validate required columns
            required_columns = [
                'Date/Time', 'Type', 'Category', 'Channel', 'Amount',
                'Description', 'Beneficiary'
            ]
            for column in required_columns:
                if column not in uploaded_df.columns:
                    print(f"Missing required column: {column}")
                    return

            # Validate Amounts
            uploaded_df['Amount'] = pd.to_numeric(uploaded_df['Amount'], errors='coerce')
            if uploaded_df['Amount'].isnull().any():
                print("Some Amount values are invalid (non-numeric). Please fix the CSV.")
                return
            if (uploaded_df['Amount'] <= 0).any():
                print("All Amounts must be positive. Negative or zero values found.")
                return

            # Standardise Type values
            uploaded_df['Type'] = uploaded_df['Type'].str.capitalize()
            invalid_types = ~uploaded_df['Type'].isin(['Income', 'Expense'])
            if invalid_types.any():
                print("Some rows have invalid Type (must be Income/Expense).")
                return

            # Remove any existing Balance column – we will recompute
            if 'Balance' in uploaded_df.columns:
                uploaded_df = uploaded_df.drop(columns=['Balance'])

            self.df = uploaded_df.copy()
            self._recompute_balances()
            self.save_data()
            print(f"Successfully loaded {len(uploaded_df)} transactions from CSV.")

        except pd.errors.EmptyDataError:
            print("The CSV file is empty.")
        except Exception as error:
            print(f"Error reading CSV: {error}")

    # ------------------- Report Generation (Download CSV) -------------------

    def generate_report(self):
        """
        Generate a CSV report for a specified date range.

        The report includes summary information (total income, expenses, opening balance,
        current balance) and a detailed list of transactions within the range.
        """
        if self.df.empty:
            print("No transactions available. Add some first.")
            return

        # Build full name from stored parts
        name_parts = [self.first_name, self.middle_name, self.last_name]
        full_name = " ".join([part.capitalize() for part in name_parts if part]) or "Unknown User"

        print("\n--- Generate Report (CSV download) ---")

        # Get date range with validation
        while True:
            start_string = input("Start date (DD-MM-YYYY): ").strip()
            try:
                start_date = datetime.strptime(start_string, "%d-%m-%Y")
                break
            except ValueError:
                print("Invalid start date format. Please use DD-MM-YYYY.")

        while True:
            end_string = input("End date (DD-MM-YYYY): ").strip()
            try:
                end_date = datetime.strptime(end_string, "%d-%m-%Y")
                break
            except ValueError:
                print("Invalid end date format. Please use DD-MM-YYYY.")

        if start_date > end_date:
            print("Start date cannot be after end date. Swapping them.")
            start_date, end_date = end_date, start_date

        try:
            # Determine opening balance for the period (balance just before start_date)
            before_period = self.df['Date/Time'] < start_date
            if before_period.any():
                last_before = self.df[before_period].iloc[-1]
                period_opening_balance = last_before['Balance']
            else:
                period_opening_balance = self.starting_balance

            # Filter transactions inside the period
            period_mask = (self.df['Date/Time'] >= start_date) & (self.df['Date/Time'] <= end_date)
            period_df = self.df[period_mask].sort_values('Date/Time')

            if period_df.empty:
                total_income = 0.0
                total_expenses = 0.0
            else:
                total_income = period_df[period_df['Type'] == 'Income']['Amount'].sum()
                total_expenses = period_df[period_df['Type'] == 'Expense']['Amount'].sum()

            current_balance = period_opening_balance + total_income - total_expenses

            # Prepare safe filenames
            safe_start = start_date.strftime("%d%m%Y")
            safe_end = end_date.strftime("%d%m%Y")
            filename = (
                f"report_{self.first_name}_{self.last_name}_"
                f"{self.current_year}_{safe_start}_to_{safe_end}.csv"
            )
            filepath = os.path.join(self.reports_dir, filename)

            # Write the CSV report
            with open(filepath, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)

                # Summary section
                writer.writerow(["Field", "Value"])
                writer.writerow(["Name", full_name])
                writer.writerow([
                    "Date Range",
                    f"{start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}"
                ])
                writer.writerow(["Total Income", f"₦{total_income:,.2f}"])
                writer.writerow(["Total Expenses", f"₦{total_expenses:,.2f}"])
                writer.writerow(["Opening Balance", f"₦{period_opening_balance:,.2f}"])
                writer.writerow(["Current Balance", f"₦{current_balance:,.2f}"])
                writer.writerow([])  # Blank separator

                # Transaction details header
                headers = [
                    'Date/Time', 'Type', 'Category', 'Channel', 'Amount',
                    'Description', 'Beneficiary', 'Balance'
                ]
                writer.writerow(headers)

                # Write each transaction row
                for _, row in period_df.iterrows():
                    date_str = row['Date/Time'].strftime("%d %B %Y %H:%M")
                    writer.writerow([
                        date_str,
                        row['Type'],
                        row['Category'],
                        row['Channel'] if pd.notna(row['Channel']) else '',
                        row['Amount'],
                        row['Description'] if pd.notna(row['Description']) else '',
                        row['Beneficiary'] if pd.notna(row['Beneficiary']) else '',
                        row['Balance']
                    ])

            print(f"\nReport successfully saved to: {filepath}")

        except Exception as error:
            print(f"Error generating report: {error}")

    # ------------------- Summary Insights -------------------

    def generate_summary(self):
        """
        Display a yearly financial summary in the console.

        Includes:
        - Top 3 payment channels (by transaction count)
        - Highest income day
        - Highest expense day
        - Top 5 income transactions by amount
        - Top 5 expense transactions by amount
        - Top 5 beneficiaries (by total amount received)
        """
        if self.df.empty:
            print("No transactions available for the year. Add some first.")
            return

        name_parts = [self.first_name, self.middle_name, self.last_name]
        full_name = " ".join([part.capitalize() for part in name_parts if part]) or "Unknown User"

        print("\n" + "=" * 60)
        print(f"YEARLY FINANCIAL SUMMARY - {self.current_year}")
        print(f"User: {full_name}")
        print("=" * 60)

        try:
            # 1. Top 3 channels
            channel_counts = self.df['Channel'].value_counts().head(3)
            print("\n1. TOP 3 PAYMENT CHANNELS (by number of transactions):")
            if channel_counts.empty:
                print("   No channel data available.")
            else:
                for rank, (channel, count) in enumerate(channel_counts.items(), start=1):
                    print(f"   {rank}. {channel}: {count} transaction(s)")

            # 2. Highest income day
            income_df = self.df[self.df['Type'] == 'Income'].copy()
            if not income_df.empty:
                income_df['Date'] = income_df['Date/Time'].dt.date
                daily_income = income_df.groupby('Date')['Amount'].sum()
                max_income_date = daily_income.idxmax()
                max_income_amount = daily_income.max()
                print("\n2. HIGHEST INCOME DAY:")
                print(f"   Date: {max_income_date.strftime('%d-%m-%Y')} "
                      f"| Amount: ₦{max_income_amount:,.2f}")
            else:
                print("\n2. HIGHEST INCOME DAY: No income transactions recorded.")

            # 3. Highest expense day
            expense_df = self.df[self.df['Type'] == 'Expense'].copy()
            if not expense_df.empty:
                expense_df['Date'] = expense_df['Date/Time'].dt.date
                daily_expense = expense_df.groupby('Date')['Amount'].sum()
                max_expense_date = daily_expense.idxmax()
                max_expense_amount = daily_expense.max()
                print("\n3. HIGHEST EXPENSE DAY:")
                print(f"   Date: {max_expense_date.strftime('%d-%m-%Y')} "
                      f"| Amount: ₦{max_expense_amount:,.2f}")
            else:
                print("\n3. HIGHEST EXPENSE DAY: No expense transactions recorded.")

            # 4. Top 5 income transactions
            if not income_df.empty:
                top_income = income_df.nlargest(5, 'Amount')[['Amount', 'Category', 'Date/Time']]
                print("\n4. TOP 5 INCOME TRANSACTIONS (by amount):")
                for i, row in top_income.iterrows():
                    date_str = row['Date/Time'].strftime('%d-%m-%Y')
                    print(f"   {i + 1}. ₦{row['Amount']:,.2f} - {row['Category']} (on {date_str})")
            else:
                print("\n4. TOP 5 INCOME TRANSACTIONS: None.")

            # 5. Top 5 expense transactions
            if not expense_df.empty:
                top_expense = expense_df.nlargest(5, 'Amount')[['Amount', 'Category', 'Date/Time']]
                print("\n5. TOP 5 EXPENSE TRANSACTIONS (by amount):")
                for i, row in top_expense.iterrows():
                    date_str = row['Date/Time'].strftime('%d-%m-%Y')
                    print(f"   {i + 1}. ₦{row['Amount']:,.2f} - {row['Category']} (on {date_str})")
            else:
                print("\n5. TOP 5 EXPENSE TRANSACTIONS: None.")

            # 6. Top 5 beneficiaries (total amount received, expense transactions only)
            beneficiaries = self.df[
                self.df['Beneficiary'].notna() & (self.df['Beneficiary'].str.strip() != '')
            ]
            if not beneficiaries.empty:
                expense_beneficiaries = beneficiaries[beneficiaries['Type'] == 'Expense']
                if not expense_beneficiaries.empty:
                    beneficiary_totals = (
                        expense_beneficiaries.groupby('Beneficiary')['Amount']
                        .sum()
                        .sort_values(ascending=False)
                        .head(5)
                    )
                    print("\n6. TOP 5 BENEFICIARIES (by total amount received):")
                    for rank, (beneficiary, amount) in enumerate(beneficiary_totals.items(), start=1):
                        print(f"   {rank}. {beneficiary}: ₦{amount:,.2f}")
                else:
                    print("\n6. TOP 5 BENEFICIARIES: No expense transactions with beneficiaries.")
            else:
                print("\n6. TOP 5 BENEFICIARIES: No beneficiary data available.")

        except Exception as error:
            print(f"Error generating summary: {error}")

        print("\n" + "=" * 60)

    # ------------------- User/Year Management -------------------

    def set_user_year(self):
        """
        Set or change the current user and year.

        Prompts for first name (mandatory), middle name (optional), last name (mandatory),
        and a valid year. Then loads the corresponding data and ensures a starting balance.
        """
        print("\n--- Set User & Year ---")

        # First name (cannot be empty)
        while True:
            first = input("First name: ").strip().lower()
            if first:
                self.first_name = first
                break
            print("First name cannot be empty. Please enter a valid name.")

        # Middle name (optional – may be empty)
        middle = input("Middle name: ").strip().lower()
        self.middle_name = middle if middle else ""

        # Last name (cannot be empty)
        while True:
            last = input("Last name: ").strip().lower()
            if last:
                self.last_name = last
                break
            print("Last name cannot be empty. Please enter a valid name.")

        # Year (must be numeric)
        while True:
            try:
                self.current_year = int(input("Enter year (e.g., 2025): ").strip())
                break
            except ValueError:
                print("Please enter a valid year (numeric).")

        self.load_data()
        self._ensure_starting_balance()
        print(f"Loaded data for {self.first_name} {self.middle_name} {self.last_name}, "
              f"year {self.current_year}")

    def set_starting_balance(self):
        """
        Edit the starting balance for the current user/year.

        Shows the current balance, asks for confirmation, then prompts for a new positive balance.
        After changing, recomputes all transaction balances.
        """
        print(f"\nCurrent starting balance for {self.first_name} {self.middle_name} "
              f"{self.last_name}, year {self.current_year}: ₦{self.starting_balance:,.2f}")
        change = input("Do you want to change it? (y/n): ").strip().lower()
        if change != 'y':
            print("No changes made.")
            return

        if not self.df.empty:
            confirm = input(
                "WARNING: Changing the starting balance will affect the 'Balance' column "
                "of all transactions. Continue? (y/n): "
            ).strip().lower()
            if confirm != 'y':
                print("Operation cancelled.")
                return

        while True:
            try:
                new_balance = float(input("Enter new starting balance for the year (must be > 0): "))
                if new_balance <= 0:
                    print("Starting balance must be greater than zero.")
                    continue
                self.starting_balance = new_balance
                self._save_starting_balance()
                self._recompute_balances()
                self.save_data()
                print(f"Starting balance updated to ₦{new_balance:,.2f} "
                      "and all transaction balances recomputed.")
                break
            except ValueError:
                print("Invalid number. Please enter a numeric value.")

    # ------------------- Main Menu -------------------

    def run(self):
        """
        Launch the interactive main menu.

        Displays available options and dispatches to the appropriate methods.
        Loops until the user chooses to exit.
        """
        print("=== Personal Finance Tracker ===")
        self.set_user_year()

        while True:
            print("\n--- MAIN MENU ---")
            print("1. Add transaction (manual)")
            print("2. Edit transaction")
            print("3. Delete transaction")
            print("4. View transactions")
            print("5. Upload CSV")
            print("6. Download report (CSV)")
            print("7. Generate summary")
            print("8. Switch user/year")
            print("9. Edit starting balance for this year")
            print("0. Exit")

            choice = input("Select an option: ").strip()

            if choice == '1':
                self.add_transaction()
            elif choice == '2':
                self.edit_transaction()
            elif choice == '3':
                self.delete_transaction()
            elif choice == '4':
                self.view_transactions()
            elif choice == '5':
                self.upload_csv()
            elif choice == '6':
                self.generate_report()
            elif choice == '7':
                self.generate_summary()
            elif choice == '8':
                self.set_user_year()
            elif choice == '9':
                self.set_starting_balance()
            elif choice == '0':
                print("Goodbye!")
                sys.exit(0)
            else:
                print("Invalid option. Please enter a number between 0 and 9.")


if __name__ == "__main__":
    tracker = FinanceTracker()
    tracker.run()