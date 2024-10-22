import streamlit as st
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, date
import pandas as pd
import matplotlib.pyplot as plt
st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide")

client = MongoClient("mongodb+srv://santhosh2k01:san2001@cluster0.qksjljg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client.expense_tracker

def add_expense(user_id, amount, category, date_input):
    if isinstance(date_input, date):
        date_input = datetime.combine(date_input, datetime.min.time())
    
    expense = {
        "user_id": user_id,
        "amount": amount,
        "category": category,
        "date": date_input
    }
    db.expenses.insert_one(expense)

def get_expenses(user_id, start_date=None, end_date=None):
    query = {"user_id": user_id}
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}
    return list(db.expenses.find(query))

def edit_expense(expense_id, amount, category, date_input):
    update_data = {
        "amount": amount,
        "category": category,
        "date": datetime.combine(date_input, datetime.min.time()) if isinstance(date_input, date) else date_input
    }
    try:
        db.expenses.update_one(
            {"_id": ObjectId(expense_id)},  # Ensure ObjectId format
            {"$set": update_data}
        )
    except Exception as e:
        st.error(f"Failed to update expense: {e}")

def delete_expense(expense_id):
    try:
        db.expenses.delete_one({"_id": ObjectId(expense_id)})  # Ensure ObjectId format
    except Exception as e:
        st.error(f"Failed to delete expense: {e}")

def register_user(username, password):
    user = {
        "username": username,
        "password": password
    }
    db.users.insert_one(user)

def get_user(username):
    return db.users.find_one({"username": username})

def set_budget(user_id, budget):
    db.budgets.update_one(
        {"user_id": user_id},
        {"$set": {"budget": budget, "month": datetime.now().strftime("%Y-%m")}},
        upsert=True
    )

def get_budget(user_id):
    return db.budgets.find_one({"user_id": user_id, "month": datetime.now().strftime("%Y-%m")})

def get_monthly_expense(user_id):
    expenses = get_expenses(user_id)
    total_expense = sum(expense['amount'] for expense in expenses)
    return total_expense

def main():
    st.sidebar.header("Login/Register")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    option = st.sidebar.selectbox("Select", ["Login", "Register"])

    if option == "Register":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Register"):
            if get_user(username):
                st.error("Username already exists", icon="❌")
            else:
                register_user(username, password)
                st.success("User registered successfully!", icon="✅")
    elif option == "Login":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            user = get_user(username)
            if user and user["password"] == password:
                st.session_state.logged_in = True
                st.session_state.user_id = user["_id"]
                st.session_state.username = username
                st.success("Logged in successfully!", icon="✅")
            else:
                st.error("Invalid credentials", icon="❌")

    if st.session_state.logged_in:
        user_id = st.session_state.user_id
        st.header(f"Welcome, {st.session_state.username}!")

        # Set monthly budget
        st.subheader("Set Monthly Budget")
        budget = st.number_input("Set Budget for the month", min_value=0.0, format="%.2f", step=0.01)
        if st.button("Set Budget"):
            set_budget(user_id, budget)
            st.success("Budget set successfully!", icon="✅")

        # Display current budget
        user_budget = get_budget(user_id)
        if user_budget:
            st.write(f"Current Budget for {user_budget['month']}: {user_budget['budget']:.2f}")

        # Add expense
        st.subheader("Add Expense")
        amount = st.number_input("Amount", min_value=0.0, format="%.2f", step=0.01)
        category = st.selectbox("Category", ["Food", "Travel", "Medical", "Education", "Shopping"])
        date_input = st.date_input("Date")

        if st.button("Add Expense", key="add-expense"):
            add_expense(user_id, amount, category, date_input)
            st.success("Expense added successfully!", icon="✅")

        # Check if total expenses exceed the budget
        total_expense = get_monthly_expense(user_id)
        if user_budget and total_expense > user_budget['budget']:
            st.warning(f"Total expenses of {total_expense:.2f} exceed the budget of {user_budget['budget']:.2f}!", icon="⚠️")

        # Filter expenses section
        st.subheader("Filter Expenses")
        start_date = st.date_input("Start Date", key="start-date")
        end_date = st.date_input("End Date", key="end-date")

        if st.button("Filter Expenses", key="filter-expenses"):
            expenses = get_expenses(user_id, datetime.combine(start_date, datetime.min.time()), datetime.combine(end_date, datetime.min.time()))
        else:
            expenses = get_expenses(user_id)

        if expenses:
            df = pd.DataFrame(expenses)
            df['date'] = pd.to_datetime(df['date'])
            df['_id'] = df['_id'].astype(str)  # Convert ObjectId to string for display
            df.drop(columns=["user_id"], inplace=True)  # Drop unnecessary columns
            st.write(df)

            # Edit expense
            st.subheader("Edit Expense")
            expense_id = st.text_input("Expense ID to edit")
            new_amount = st.number_input("New Amount", min_value=0.0, format="%.2f", step=0.01)
            new_category = st.selectbox("New Category", ["Food", "Travel", "Medical", "Education", "Shopping"])
            new_date = st.date_input("New Date")
            if st.button("Edit Expense", key="edit-expense"):
                edit_expense(expense_id, new_amount, new_category, new_date)
                st.success("Expense updated successfully!", icon="✅")

            # Delete expense
            st.subheader("Delete Expense")
            delete_id = st.text_input("Expense ID to delete")
            if st.button("Delete Expense", key="delete-expense"):
                delete_expense(delete_id)
                st.success("Expense deleted successfully!", icon="✅")

        # Display monthly expenses graph
        if not expenses:
            st.warning("No expenses to display.")
        else:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            monthly_expenses = df.resample('M')['amount'].sum()

            st.subheader("Monthly Expense Summary")
            fig, ax = plt.subplots()
            monthly_expenses.plot(kind='bar', color='skyblue', edgecolor='black', ax=ax)
            ax.set_title("Monthly Expenses")
            ax.set_xlabel("Month")
            ax.set_ylabel("Total Amount")
            st.pyplot(fig)

if __name__ == "__main__":
    main()
