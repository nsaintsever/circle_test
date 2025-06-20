import streamlit as st
import pandas as pd
from streamlit_utils import (
    get_orders_for_actor_api,
    get_order_details_api, # To display full order details
    CHAMPS_CSV_DIR # For constructing descriptions or listing all champs
)
import os
import json
import re

# --- Configuration ---
WAREHOUSE_ID = "Warehouse_Alpha" # Simulate a logged-in Warehouse user

# --- Helper Functions ---
# CHAMPS_CSV_DIR is imported from streamlit_utils

def sort_key_for_champ_code(item_tuple): # item_tuple is like ('C10', 'Product Name')
    code = item_tuple[0]
    match = re.match(r"C(\d+)([A-Z]*)", code) # Match from the start of the string
    if match:
        numeric_part = int(match.group(1))
        alpha_part = match.group(2) if match.group(2) else "" # Ensure alpha_part is always a string
        return (numeric_part, alpha_part)
    # Fallback for any codes not matching C<digits><optional_letters>
    return (float('inf'), code)

def get_all_champ_codes_and_names_warehouse(): # Renamed for clarity
    """Scans the champs_csv directory to get all C-codes and their descriptive names."""
    champs = {}
    try:
        # Path relative to the current script file
        script_dir = os.path.dirname(__file__)
        effective_csv_dir = os.path.join(script_dir, CHAMPS_CSV_DIR)

        if not os.path.isdir(effective_csv_dir):
             # Fallback: if not found relative to script, try relative to CWD
            effective_csv_dir = os.path.join(os.getcwd(), CHAMPS_CSV_DIR)
            if not os.path.isdir(effective_csv_dir):
                st.error(f"Champs CSV directory not found at {CHAMPS_CSV_DIR} or {effective_csv_dir}.")
                return {}

        for f in os.listdir(effective_csv_dir):
            if f.startswith("C") and f.endswith(".csv"):
                # Try to extract code like C1, C10, C52E from filenames like C1_cases.csv, C52E_specific_back_label_bats.csv
                code_match = re.match(r"(C\d+[A-Z]*)_", f)
                if not code_match: # Try simple C<number> if the first regex fails
                    code_match = re.match(r"(C\d+)_",f)

                if code_match:
                    code = code_match.group(1)
                    name_part = f[len(code)+1:].replace(".csv", "").replace("_", " ").title()
                    champs[code] = f"{code} - {name_part}" # Store descriptive name
    except Exception as e:
        st.error(f"Error scanning champs_csv directory: {e}")
        return {}

    if not champs:
        st.warning("No champ CSV files found or parsed in Warehouse App.")
        return {}

    sorted_champs = dict(sorted(champs.items(), key=sort_key_for_champ_code))
    return sorted_champs

ALL_CHAMPS_INFO = get_all_champ_codes_and_names_warehouse()

def display_warehouse_order_details(order_data: dict):
    """Displays the order details for Warehouse (read-only)."""
    st.subheader(f"Viewing Order CLE: {st.session_state.selected_order_cle_warehouse}")

    config_path = os.path.join(os.path.dirname(__file__), "config", "circle_validations.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            validation_config = json.load(f)
    except Exception:
        validation_config = {}

    cols = st.columns(2)
    col_idx = 0

    sorted_codes = sorted(order_data.keys(), key=lambda x: int(x[1:]) if x[0]=='C' and x[1:].isdigit() else 999)

    for code in sorted_codes:
        name = ALL_CHAMPS_INFO.get(code, code) # Fallback to code if name not in our simple map
        field_label = f"{code}: {validation_config.get(code, {}).get('name', name)}"
        current_value = order_data.get(code, "")

        with cols[col_idx % 2]:
            st.text_input(field_label, value=str(current_value), disabled=True, key=f"form_wh_{code}")
        col_idx += 1

# --- Main App Logic ---
st.set_page_config(layout="wide")
st.title(f"Warehouse App ({WAREHOUSE_ID})")

# Initialize session state variables
if 'warehouse_orders_list' not in st.session_state:
    st.session_state.warehouse_orders_list = None
if 'selected_order_cle_warehouse' not in st.session_state:
    st.session_state.selected_order_cle_warehouse = None
if 'selected_order_data_warehouse' not in st.session_state:
    st.session_state.selected_order_data_warehouse = None
if 'full_selected_order_warehouse' not in st.session_state:
    st.session_state.full_selected_order_warehouse = None


# --- Order List and Selection ---
st.sidebar.header("Incoming Orders for Warehouse")
if st.sidebar.button("Refresh Orders", key="refresh_warehouse_orders"):
    st.session_state.warehouse_orders_list = get_orders_for_actor_api(WAREHOUSE_ID)
    st.session_state.selected_order_cle_warehouse = None # Reset selection
    st.session_state.selected_order_data_warehouse = None
    st.experimental_rerun()

if st.session_state.warehouse_orders_list is None:
    st.session_state.warehouse_orders_list = get_orders_for_actor_api(WAREHOUSE_ID)

if st.session_state.warehouse_orders_list:
    order_options_warehouse = {
        order["cle"]: f"{order['cle']} (Status: {order['status']}, From: {order.get('sender', 'N/A')})"
        for order in st.session_state.warehouse_orders_list
    }

    selected_cle_disp_warehouse = st.sidebar.selectbox(
        "Select an order to view:",
        options=list(order_options_warehouse.keys()),
        format_func=lambda x: order_options_warehouse[x],
        index=None,
        key="warehouse_order_selector"
    )

    if selected_cle_disp_warehouse and selected_cle_disp_warehouse != st.session_state.selected_order_cle_warehouse:
        st.session_state.selected_order_cle_warehouse = selected_cle_disp_warehouse
        full_details = get_order_details_api(st.session_state.selected_order_cle_warehouse)
        if full_details:
            st.session_state.selected_order_data_warehouse = full_details.get("data", {})
            st.session_state.full_selected_order_warehouse = full_details # Store whole response for history etc.
        else:
            st.session_state.selected_order_data_warehouse = {}
            st.error("Could not fetch details for the selected order.")
        st.experimental_rerun()

elif isinstance(st.session_state.warehouse_orders_list, list) and not st.session_state.warehouse_orders_list:
    st.sidebar.info("No orders currently assigned to this Warehouse.")
else:
    st.sidebar.error("Could not retrieve orders from API for Warehouse.")


# --- Order Display ---
if st.session_state.selected_order_cle_warehouse and st.session_state.selected_order_data_warehouse:
    st.header("View Order Details")
    display_warehouse_order_details(st.session_state.selected_order_data_warehouse)

    # Display order history
    if st.session_state.get('full_selected_order_warehouse') and 'history' in st.session_state.full_selected_order_warehouse:
        st.subheader("Order History")
        history_df = pd.DataFrame(st.session_state.full_selected_order_warehouse['history'])
        if not history_df.empty:
            history_df = history_df.sort_values(by="timestamp", ascending=False)
            st.dataframe(history_df[["timestamp", "actor", "action"]])
            # Optional: expander for full changed_data for each history entry
            # for idx, entry in history_df.iterrows():
            #     with st.expander(f"{entry['timestamp']} - {entry['actor']} - {entry['action']}"):
            #         st.json(entry['changed_data'] if entry['changed_data'] else {})
        else:
            st.write("No history found for this order.")
else:
    st.info("Select an order from the sidebar to view.")

st.sidebar.info("This is a prototype Warehouse application for the CIRCLE Wine Language project.")
