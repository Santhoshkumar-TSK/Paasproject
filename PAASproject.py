import streamlit as st
from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime as dt, date
from dotenv import load_dotenv
import os
import uuid  # Import the uuid library

# Load environment variables
load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI"))
db = client['expense_tracker']

# Collections
users_collection = db['users']
expenses_collection = db['expenses']
budgets_collection = db['budgets']

# User Authentication
def signup(username, password):
    if users_collection.find_one({'username': username}):
        st.sidebar.error("Username already exists.")
    else:
        users_collection.insert_one({'username': username, 'password': password})
        st.sidebar.success("Signup successful! Please log in.")

def login(username, password):
    user = users_collection.find_one({'username': username})
    if user and user['password'] == password:
        st.session_state['logged_in'] = True
        st.session_state['username'] = username
        st.sidebar.success("Logged in successfully!")
    else:
        st.sidebar.error("Invalid username or password.")

# Add expense data
def add_expense(username, amount, category, date_input):
    datetime_date = dt.combine(date_input, dt.min.time())
    expense_id = str(uuid.uuid4())  # Generate a unique ID for the expense
    expenses_collection.insert_one({
        '_id': expense_id,  # Use the generated ID as the unique identifier
        'username': username,
        'amount': amount,
        'category': category,
        'date': datetime_date
    })
    st.success("Expense data added successfully!")

# Edit expense data
def edit_expense(expense_id, new_amount, new_category, new_date):
    datetime_date = dt.combine(new_date, dt.min.time())
    expenses_collection.update_one(
        {'_id': expense_id},
        {"$set": {'amount': new_amount, 'category': new_category, 'date': datetime_date}}
    )
    st.success("Expense updated successfully!")

# Delete expense data
def delete_expense(expense_id):
    expenses_collection.delete_one({'_id': expense_id})
    st.success("Expense deleted successfully!")

# Get user expense data
def get_user_expenses(username):
    return pd.DataFrame(list(expenses_collection.find({'username': username})))

# Streamlit UI
st.title("Expense Tracker")

# Sidebar: Sign-Up or Sign-In
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.sidebar.title("Authentication")
    auth_choice = st.sidebar.selectbox("Sign In or Sign Up", ["Sign In", "Sign Up"])
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")

    if auth_choice == "Sign Up":
        if st.sidebar.button("Sign Up"):
            signup(username, password)
    elif auth_choice == "Sign In":
        if st.sidebar.button("Sign In"):
            login(username, password)

# Main Page: Display Options if Logged In
if st.session_state['logged_in']:
    st.sidebar.success(f"Welcome, {st.session_state['username']}")
    st.sidebar.button("Logout", on_click=lambda: (st.session_state.update({'logged_in': False, 'username': None}), st.success("Logged out successfully.")))
    
    # Add Expense Section
    st.subheader("Add Expense")
    amount = st.number_input("Amount", min_value=0.01, step=0.01)
    category = st.selectbox("Category", ["Food", "Travel", "Medical", "Education", "Shopping"])
    date_input = st.date_input("Date", value=date.today())
    if st.button("Add Expense"):
        add_expense(st.session_state['username'], amount, category, date_input)

    # View and Manage Expenses
    st.write("### Your Expenses")
    user_expenses = get_user_expenses(st.session_state['username'])

    if not user_expenses.empty:
        user_expenses['date'] = pd.to_datetime(user_expenses['date'])
        st.dataframe(user_expenses[['amount', 'category', 'date', '_id']].set_index(user_expenses.index))

        # Bar chart of expenses by category
        plt.figure(figsize=(10, 5))
        user_expenses.groupby('category')['amount'].sum().plot(kind='bar', color='skyblue')
        plt.title('Total Expenses by Category')
        plt.xlabel('Category')
        plt.ylabel('Amount')
        st.pyplot(plt)

        # Filter Expenses Section
        st.subheader("Filter Expenses")

        # Date range input
        start_date = st.date_input("Start Date", value=date.today(), max_value=date.today())
        end_date = st.date_input("End Date", value=date.today(), min_value=start_date, max_value=date.today())

        # Category filter
        category_filter = st.selectbox("Select Category to Filter", ["All"] + ["Food", "Travel", "Medical", "Education", "Shopping"])

        # Filter user expenses based on selected criteria
        if category_filter != "All":
            filtered_expenses = user_expenses[(user_expenses['date'] >= pd.to_datetime(start_date)) &
                                               (user_expenses['date'] <= pd.to_datetime(end_date)) &
                                               (user_expenses['category'] == category_filter)]
        else:
            filtered_expenses = user_expenses[(user_expenses['date'] >= pd.to_datetime(start_date)) &
                                               (user_expenses['date'] <= pd.to_datetime(end_date))]

        # Display filtered expenses
        st.write("### Filtered Expenses")
        if not filtered_expenses.empty:
            st.dataframe(filtered_expenses[['amount', 'category', 'date', '_id']].set_index(filtered_expenses.index))

            # Bar chart of filtered expenses by category
            plt.figure(figsize=(10, 5))
            filtered_expenses.groupby('category')['amount'].sum().plot(kind='bar', color='skyblue')
            plt.title('Total Expenses by Category (Filtered)')
            plt.xlabel('Category')
            plt.ylabel('Amount')
            st.pyplot(plt)
        else:
            st.write("No expenses data available for the selected filters.")

        # Edit or Delete Expenses
        st.write("### Edit or Delete Expenses")
        expense_id = st.selectbox("Select Expense ID to Edit/Delete", user_expenses['_id'].values)
        selected_expense = user_expenses[user_expenses['_id'] == expense_id].iloc[0] if not user_expenses[user_expenses['_id'] == expense_id].empty else None

        if selected_expense is not None:
            new_amount = st.number_input("New Amount", value=selected_expense['amount'], step=0.01)
            new_category = st.selectbox("New Category", ["Food", "Travel", "Medical", "Education", "Shopping"], index=["Food", "Travel", "Medical", "Education", "Shopping"].index(selected_expense['category']))
            new_date = st.date_input("New Date", value=selected_expense['date'].date())

            if st.button("Update Expense"):
                edit_expense(selected_expense['_id'], new_amount, new_category, new_date)

            if st.button("Delete Expense"):
                delete_expense(selected_expense['_id'])
    else:
        st.write("No expenses data availale")
