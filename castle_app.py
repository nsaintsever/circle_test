import streamlit as st
import pandas as pd
from streamlit_utils import (
    get_allowed_values_for_champ,
    get_champ_details,
    update_order_api,
    get_orders_for_actor_api,
    get_order_details_api, # To fetch full order details including history
    circle_allowed_values_lookup,
    CHAMPS_CSV_DIR
)
from circle_validator import CircleValidatorService # For validation
import os
import json
import re

# --- Configuration ---
CASTLE_ID = "Castle_Main_A" # Simulate a logged-in Castle user

# --- Helper Functions ---
# CHAMPS_CSV_DIR is imported from streamlit_utils

def sort_key_for_champ_code(item_tuple):
    code = item_tuple[0]
    match = re.match(r"C(\d+)([A-Z]*)", code)
    if match:
        numeric_part = int(match.group(1))
        alpha_part = match.group(2) if match.group(2) else ""
        return (numeric_part, alpha_part)
    return (float('inf'), code)

def get_all_champ_codes_and_names_castle(): # Renamed for clarity
    """Scans the champs_csv directory to get all C-codes and their descriptive names."""
    champs = {}
    try:
        script_dir = os.path.dirname(__file__)
        effective_csv_dir = os.path.join(script_dir, CHAMPS_CSV_DIR)
        if not os.path.isdir(effective_csv_dir):
            effective_csv_dir = os.path.join(os.getcwd(), CHAMPS_CSV_DIR)
            if not os.path.isdir(effective_csv_dir):
                st.error(f"Champs CSV directory not found at {CHAMPS_CSV_DIR} or {effective_csv_dir}.")
                return {}

        for f in os.listdir(effective_csv_dir):
            if f.startswith("C") and f.endswith(".csv"):
                code_match = re.match(r"(C\d+[A-Z]*)_", f)
                if not code_match:
                    code_match = re.match(r"(C\d+)_", f)

                if code_match:
                    code = code_match.group(1)
                    name_part = f[len(code)+1:].replace(".csv", "").replace("_", " ").title()
                    champs[code] = f"{code} - {name_part}"
    except Exception as e:
        st.error(f"Error scanning champs_csv directory: {e}")
        return {}

    if not champs:
        st.warning("No champ CSV files found or parsed in Castle App.")
        return {}

    sorted_champs = dict(sorted(champs.items(), key=sort_key_for_champ_code))
    return sorted_champs

ALL_CHAMPS_INFO = get_all_champ_codes_and_names_castle()

# Define fields typically editable by Castle (example, can be expanded)
CASTLE_EDITABLE_FIELDS = [
    "C11", "C12", "C15", "C16", "C17", "C18", "C19", # Vintage, Degree, Bottle Weights/Dimensions
    "C32A", "C33B", "C34", "C35", # Batch numbers, Harvest/Bottling dates
    "C48", # Sulphites
    # Add more as per actual business logic for Castles
]


def display_castle_order_form(order_data: dict):
    """Displays the order form for Castle, highlighting editable fields."""
    st.subheader(f"Order CLE: {st.session_state.selected_order_cle}")

    # Simulate loading circle_validations.json for field names (as in validator)
    # This path might need adjustment depending on execution context
    config_path = os.path.join(os.path.dirname(__file__), "config", "circle_validations.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            validation_config = json.load(f)
    except Exception as e:
        st.error(f"Could not load validation config: {e}")
        validation_config = {}


    editable_order_inputs = {}

    cols = st.columns(2)
    col_idx = 0

    # Display all fields, making some editable
    for i, code in enumerate(ALL_CHAMPS_INFO.keys()):
        name = ALL_CHAMPS_INFO.get(code, code) # Fallback to code if name not found
        field_label = f"{code}: {validation_config.get(code, {}).get('name', name)}" # Use name from config if available
        current_value = order_data.get(code, "")

        with cols[col_idx % 2]:
            if code in CASTLE_EDITABLE_FIELDS:
                allowed_vals = get_allowed_values_for_champ(code)
                if allowed_vals:
                    try:
                        idx = allowed_vals.index(current_value) if current_value and current_value in allowed_vals else 0
                        editable_order_inputs[code] = st.selectbox(field_label, options=allowed_vals, index=idx, key=f"form_castle_{code}")
                    except ValueError:
                        editable_order_inputs[code] = st.selectbox(field_label, options=allowed_vals, index=0, key=f"form_castle_{code}")
                else:
                    editable_order_inputs[code] = st.text_input(field_label, value=current_value, key=f"form_castle_{code}")
            else:
                # Display as non-editable (text or disabled widget)
                st.text_input(field_label, value=current_value, disabled=True, key=f"form_castle_{code}_disabled")
                editable_order_inputs[code] = current_value # Keep original value for non-editable fields
        col_idx += 1

    merchant_id = st.text_input("Send to Merchant ID", value="Merchant_GlobalWines", key="merchant_receiver_id")
    return editable_order_inputs, merchant_id


# --- Main App Logic ---
st.set_page_config(layout="wide")
st.title(f"Castle App ({CASTLE_ID})")

# Initialize session state variables
if 'castle_orders_list' not in st.session_state:
    st.session_state.castle_orders_list = None
if 'selected_order_cle' not in st.session_state:
    st.session_state.selected_order_cle = None
if 'selected_order_data' not in st.session_state:
    st.session_state.selected_order_data = None
if 'validation_errors_castle' not in st.session_state:
    st.session_state.validation_errors_castle = {}

# --- Order List and Selection ---
st.sidebar.header("Pending Orders")
if st.sidebar.button("Refresh Orders", key="refresh_castle_orders"):
    st.session_state.castle_orders_list = get_orders_for_actor_api(CASTLE_ID)
    st.session_state.selected_order_cle = None # Reset selection on refresh
    st.session_state.selected_order_data = None
    st.experimental_rerun()

if st.session_state.castle_orders_list is None:
    st.session_state.castle_orders_list = get_orders_for_actor_api(CASTLE_ID)

if st.session_state.castle_orders_list:
    order_options = {order["cle"]: f"{order['cle']} (Status: {order['status']}, From: {order.get('sender', 'N/A')})"
                     for order in st.session_state.castle_orders_list}

    selected_cle_display = st.sidebar.selectbox(
        "Select an order to process:",
        options=list(order_options.keys()),
        format_func=lambda x: order_options[x],
        index=None, # No default selection
        key="castle_order_selector"
    )

    if selected_cle_display and selected_cle_display != st.session_state.selected_order_cle :
        st.session_state.selected_order_cle = selected_cle_display
        # Fetch full order details when an order is selected
        full_order_details = get_order_details_api(st.session_state.selected_order_cle)
        if full_order_details:
            st.session_state.selected_order_data = full_order_details.get("data", {}) # The dict of C-fields
            st.session_state.full_selected_order = full_order_details # Store the whole response
        else:
            st.session_state.selected_order_data = {}
            st.error("Could not fetch details for the selected order.")
        st.experimental_rerun()

elif isinstance(st.session_state.castle_orders_list, list) and not st.session_state.castle_orders_list:
    st.sidebar.info("No orders currently assigned to this Castle.")
else:
    st.sidebar.error("Could not retrieve orders from API.")


# --- Order Processing Form ---
if st.session_state.selected_order_cle and st.session_state.selected_order_data:
    st.header("Process Order")

    # Load circle_validations.json for the validator
    # This path might be fragile if script location changes relative to config
    config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "circle_validations.json")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f_config:
            circle_validations_json_str = f_config.read()
    except FileNotFoundError:
        st.error(f"Error: circle_validations.json not found at {config_file_path}")
        circle_validations_json_str = "{}" # Empty config as fallback

    # Display form with current order data
    updated_inputs, merchant_receiver_id = display_castle_order_form(st.session_state.selected_order_data)

    if st.button("Validate and Send to Merchant", key="send_to_merchant"):
        # Basic check for receiver ID
        if not merchant_receiver_id:
            st.error("Merchant ID is required.")
        else:
            # --- Perform Validation ---
            # Ensure C0 is present for the validator
            if 'C0' not in updated_inputs or not updated_inputs['C0']:
                original_c0 = st.session_state.selected_order_data.get('C0', '11') # Get from original or default
                updated_inputs['C0'] = original_c0 if original_c0 else '11'


            validator = CircleValidatorService(
                circle_values=updated_inputs,
                config_json=circle_validations_json_str,
                allowed_values_lookup=circle_allowed_values_lookup
                # version_lookup could be added if C0 has specific versions impacting other lookups
            )
            errors = validator.validate()
            st.session_state.validation_errors_castle = errors

            if not errors:
                st.info(f"Validation successful. Sending order {st.session_state.selected_order_cle} to Merchant ID: {merchant_receiver_id}...")
                api_response = update_order_api(
                    cle=st.session_state.selected_order_cle,
                    updated_data=updated_inputs,
                    sender=CASTLE_ID,
                    new_current_actor=merchant_receiver_id,
                    new_status="PendingMerchantApproval", # Or "AmendedByCastle" if that's more appropriate first
                    action_desc=f"Order amended/processed by Castle {CASTLE_ID}"
                )
                if api_response and "cle" in api_response:
                    st.success(f"Order {api_response['cle']} sent to Merchant {merchant_receiver_id} successfully!")
                    st.json(api_response)
                    # Reset selection and refresh list
                    st.session_state.selected_order_cle = None
                    st.session_state.selected_order_data = None
                    st.session_state.castle_orders_list = get_orders_for_actor_api(CASTLE_ID) # Refresh list
                    st.experimental_rerun()
                elif api_response and "detail" in api_response:
                     st.error(f"API Error: {api_response['detail']}")
                else:
                    st.error("Failed to send order. Check API connection or logs.")
            else:
                st.error("Validation Failed!")
                for field, error_msgs in errors.items():
                    for msg in error_msgs:
                        st.warning(f"Field {field}: {msg}")

    # Display validation errors if any from a previous attempt
    if st.session_state.validation_errors_castle:
        st.subheader("Last Validation Attempt Errors:")
        for field, error_msgs in st.session_state.validation_errors_castle.items():
            st.error(f"Field {field}: {', '.join(error_msgs)}")


    # Display order history (if available in full_selected_order)
    if st.session_state.get('full_selected_order') and 'history' in st.session_state.full_selected_order:
        st.subheader("Order History")
        history_df = pd.DataFrame(st.session_state.full_selected_order['history'])
        if not history_df.empty:
            history_df = history_df.sort_values(by="timestamp", ascending=False)
            st.dataframe(history_df[["timestamp", "actor", "action"]])
            for idx, entry in history_df.iterrows():
                with st.expander(f"{entry['timestamp']} - {entry['actor']} - {entry['action']}"):
                    st.json(entry['changed_data'] if entry['changed_data'] else {})
        else:
            st.write("No history found for this order.")

else:
    st.info("Select an order from the sidebar to process.")

st.sidebar.info("This is a prototype Castle application for the CIRCLE Wine Language project.")
