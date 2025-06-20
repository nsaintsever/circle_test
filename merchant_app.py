import streamlit as st
import pandas as pd
from streamlit_utils import (
    get_allowed_values_for_champ,
    get_champ_details,
    update_order_api,
    get_orders_for_actor_api,
    get_order_details_api,
    circle_allowed_values_lookup,
    CHAMPS_CSV_DIR
)
from circle_validator import CircleValidatorService
import os
import json
from typing import Dict, Any

# --- Configuration ---
MERCHANT_ID = "Merchant_GlobalWines" # Simulate a logged-in Merchant user
# Define fields typically editable by Merchant (example)
MERCHANT_EDITABLE_FIELDS = [
    "C14", # Traffic Rights (Droits de circulation)
    "C38", "C39D", # Case barcode info
    "C66", # In Bond status
    # Potentially pricing, delivery terms, etc., if they were CIRCLE fields
    # For now, keeping it to existing logistic-focused fields
]


# --- Helper Functions ---
def get_all_champ_codes_and_names():
    """ Placeholder: Scans the champs_csv directory to get all C-codes and their names."""
    champ_files = os.listdir(CHAMPS_CSV_DIR)
    champs = {}
    for f in champ_files:
        if f.startswith("C") and f.endswith(".csv"):
            code = f.split('_')[0]
            name = f.replace(".csv", "").replace("_", " ").title()
            champs[code] = name
    sorted_champs = dict(sorted(champs.items(), key=lambda item: int(item[0][1:] if item[0][1:].isdigit() else 999)))
    return sorted_champs

ALL_CHAMPS_INFO = get_all_champ_codes_and_names()

def display_merchant_order_form(order_data: dict, original_order_data_for_diff: dict = None):
    """Displays the order form for Merchant, highlighting editable fields and changes."""
    st.subheader(f"Order CLE: {st.session_state.selected_order_cle_merchant}")

    config_path = os.path.join(os.path.dirname(__file__), "config", "circle_validations.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            validation_config = json.load(f)
    except Exception:
        validation_config = {}

    editable_order_inputs = {}
    cols = st.columns(2)
    col_idx = 0

    for i, code in enumerate(ALL_CHAMPS_INFO.keys()):
        name = ALL_CHAMPS_INFO.get(code, code)
        field_label = f"{code}: {validation_config.get(code, {}).get('name', name)}"
        current_value = order_data.get(code, "")
        original_value = original_order_data_for_diff.get(code, "") if original_order_data_for_diff else ""

        display_value = current_value
        if original_order_data_for_diff and current_value != original_value:
            field_label = f"{field_label} (Original: {original_value})" # Show original if changed

        with cols[col_idx % 2]:
            if code in MERCHANT_EDITABLE_FIELDS:
                allowed_vals = get_allowed_values_for_champ(code)
                if allowed_vals:
                    try:
                        idx = allowed_vals.index(display_value) if display_value and display_value in allowed_vals else 0
                        editable_order_inputs[code] = st.selectbox(field_label, options=allowed_vals, index=idx, key=f"form_merchant_{code}")
                    except ValueError:
                        editable_order_inputs[code] = st.selectbox(field_label, options=allowed_vals, index=0, key=f"form_merchant_{code}")
                else:
                    editable_order_inputs[code] = st.text_input(field_label, value=display_value, key=f"form_merchant_{code}")
            else:
                st.text_input(field_label, value=display_value, disabled=True, key=f"form_merchant_{code}_disabled")
                editable_order_inputs[code] = display_value # Keep original for non-editable
        col_idx +=1

    return editable_order_inputs


# --- Main App Logic ---
st.set_page_config(layout="wide")
st.title(f"Wine Merchant App ({MERCHANT_ID})")

# Initialize session state
if 'merchant_orders_list' not in st.session_state:
    st.session_state.merchant_orders_list = None
if 'selected_order_cle_merchant' not in st.session_state:
    st.session_state.selected_order_cle_merchant = None
if 'selected_order_data_merchant' not in st.session_state: # Current data being viewed/edited
    st.session_state.selected_order_data_merchant = None
if 'original_selected_order_data_merchant' not in st.session_state: # For diffing
    st.session_state.original_selected_order_data_merchant = None
if 'full_selected_order_merchant' not in st.session_state:
    st.session_state.full_selected_order_merchant = None
if 'validation_errors_merchant' not in st.session_state:
    st.session_state.validation_errors_merchant = {}


# --- Order List and Selection ---
st.sidebar.header("Pending Orders for Merchant")
if st.sidebar.button("Refresh Orders", key="refresh_merchant_orders"):
    st.session_state.merchant_orders_list = get_orders_for_actor_api(MERCHANT_ID)
    st.session_state.selected_order_cle_merchant = None
    st.session_state.selected_order_data_merchant = None
    st.session_state.original_selected_order_data_merchant = None
    st.experimental_rerun()

if st.session_state.merchant_orders_list is None:
    st.session_state.merchant_orders_list = get_orders_for_actor_api(MERCHANT_ID)

if st.session_state.merchant_orders_list:
    order_options_merchant = {
        order["cle"]: f"{order['cle']} (Status: {order['status']}, From: {order.get('sender', 'N/A')})"
        for order in st.session_state.merchant_orders_list
    }
    selected_cle_disp_merchant = st.sidebar.selectbox(
        "Select an order to process:",
        options=list(order_options_merchant.keys()),
        format_func=lambda x: order_options_merchant[x],
        index=None,
        key="merchant_order_selector"
    )

    if selected_cle_disp_merchant and selected_cle_disp_merchant != st.session_state.selected_order_cle_merchant:
        st.session_state.selected_order_cle_merchant = selected_cle_disp_merchant
        full_details = get_order_details_api(st.session_state.selected_order_cle_merchant)
        if full_details:
            st.session_state.selected_order_data_merchant = full_details.get("data", {})
            st.session_state.original_selected_order_data_merchant = full_details.get("data", {}).copy() # For diff
            st.session_state.full_selected_order_merchant = full_details
        else:
            st.session_state.selected_order_data_merchant = {}
            st.session_state.original_selected_order_data_merchant = {}
            st.error("Could not fetch details for the selected order.")
        st.experimental_rerun()

elif isinstance(st.session_state.merchant_orders_list, list) and not st.session_state.merchant_orders_list:
    st.sidebar.info("No orders currently assigned to this Merchant.")
else:
    st.sidebar.error("Could not retrieve orders from API for Merchant.")


# --- Order Processing Form and Actions ---
if st.session_state.selected_order_cle_merchant and st.session_state.selected_order_data_merchant:
    st.header("Process Order")

    config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "circle_validations.json")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f_config:
            circle_validations_json_str = f_config.read()
    except FileNotFoundError:
        st.error(f"Error: circle_validations.json not found at {config_file_path}")
        circle_validations_json_str = "{}"

    updated_inputs = display_merchant_order_form(st.session_state.selected_order_data_merchant, st.session_state.original_selected_order_data_merchant)

    form_actions_cols = st.columns(3)

    # Determine the sender of the current order to decide "Send Back" target
    sender_of_current_order = st.session_state.full_selected_order_merchant.get("sender", "Castle_Main_A") # Default to Castle

    if form_actions_cols[0].button("Send Amended Order Back to Castle", key="send_amended_to_castle"):
        if 'C0' not in updated_inputs or not updated_inputs['C0']: # Ensure C0 for validation
            updated_inputs['C0'] = st.session_state.selected_order_data_merchant.get('C0', '11')

        validator = CircleValidatorService(updated_inputs, circle_validations_json_str, allowed_values_lookup=circle_allowed_values_lookup)
        errors = validator.validate()
        st.session_state.validation_errors_merchant = errors

        if not errors:
            st.info(f"Validation successful. Sending amended order {st.session_state.selected_order_cle_merchant} back to {sender_of_current_order}...")
            api_response = update_order_api(
                cle=st.session_state.selected_order_cle_merchant,
                updated_data=updated_inputs,
                sender=MERCHANT_ID,
                new_current_actor=sender_of_current_order, # Send back to original sender (Castle)
                new_status="AmendedByMerchant",
                action_desc=f"Order amended by Merchant {MERCHANT_ID}"
            )
            if api_response and "cle" in api_response:
                st.success(f"Amended order {api_response['cle']} sent back to {sender_of_current_order}!")
                st.session_state.selected_order_cle_merchant = None # Reset
                st.session_state.merchant_orders_list = get_orders_for_actor_api(MERCHANT_ID)
                st.experimental_rerun()
            else:
                st.error(f"API Error sending amended order: {api_response.get('detail', 'Unknown error') if api_response else 'Connection error'}")
        else:
            st.error("Validation Failed for amendment!")
            # Errors will be displayed below

    if form_actions_cols[1].button("Accept Order", key="accept_order"):
        # For "Accept", we typically don't change data, but resubmit the current state
        # Or, the API could just update status without needing full data.
        # For consistency with update_order_api, we send the (potentially unchanged) data.
        current_data_for_acceptance = st.session_state.selected_order_data_merchant

        # Ensure C0 is present for potential implicit validation on API or if status change triggers something
        if 'C0' not in current_data_for_acceptance or not current_data_for_acceptance['C0']:
            current_data_for_acceptance['C0'] = st.session_state.original_selected_order_data_merchant.get('C0', '11')

        st.info(f"Accepting order {st.session_state.selected_order_cle_merchant}...")
        api_response = update_order_api(
            cle=st.session_state.selected_order_cle_merchant,
            updated_data=current_data_for_acceptance,
            sender=MERCHANT_ID,
            # Who is the next actor after merchant acceptance?
            # Based on description: "If it accepts, they can click on send again and it goes back to wine merchant." - this is confusing.
            # Let's assume "Accepted" means it's now for the Merchant to decide next step (e.g. send to warehouse)
            # So, current_actor remains Merchant but status changes.
            new_current_actor=MERCHANT_ID,
            new_status="AcceptedByMerchant",
            action_desc=f"Order accepted by Merchant {MERCHANT_ID}"
        )
        if api_response and "cle" in api_response:
            st.success(f"Order {api_response['cle']} accepted by Merchant!")
            st.session_state.selected_order_cle_merchant = None # Reset
            st.session_state.merchant_orders_list = get_orders_for_actor_api(MERCHANT_ID)
            st.experimental_rerun()
        else:
            st.error(f"API Error accepting order: {api_response.get('detail', 'Unknown error') if api_response else 'Connection error'}")

    warehouse_id_input = st.text_input("Warehouse ID for dispatch", value="Warehouse_Alpha", key="warehouse_id_dispatch")
    if form_actions_cols[2].button("Send Accepted Order to Warehouse", key="send_to_warehouse"):
        if st.session_state.full_selected_order_merchant.get("status") != "AcceptedByMerchant":
            st.warning("Order must be in 'AcceptedByMerchant' status to send to Warehouse.")
        elif not warehouse_id_input:
            st.error("Warehouse ID is required for dispatch.")
        else:
            current_data_for_dispatch = st.session_state.selected_order_data_merchant
            if 'C0' not in current_data_for_dispatch or not current_data_for_dispatch['C0']:
                 current_data_for_dispatch['C0'] = st.session_state.original_selected_order_data_merchant.get('C0', '11')

            st.info(f"Sending accepted order {st.session_state.selected_order_cle_merchant} to Warehouse {warehouse_id_input}...")
            api_response = update_order_api(
                cle=st.session_state.selected_order_cle_merchant,
                updated_data=current_data_for_dispatch, # Send current data
                sender=MERCHANT_ID,
                new_current_actor=warehouse_id_input,
                new_status="SentToWarehouse",
                action_desc=f"Order dispatched to Warehouse {warehouse_id_input} by Merchant {MERCHANT_ID}"
            )
            if api_response and "cle" in api_response:
                st.success(f"Order {api_response['cle']} sent to Warehouse {warehouse_id_input}!")
                st.session_state.selected_order_cle_merchant = None # Reset
                st.session_state.merchant_orders_list = get_orders_for_actor_api(MERCHANT_ID)
                st.experimental_rerun()
            else:
                 st.error(f"API Error sending to warehouse: {api_response.get('detail', 'Unknown error') if api_response else 'Connection error'}")

    # Display validation errors if any
    if st.session_state.validation_errors_merchant:
        st.subheader("Last Validation Attempt Errors:")
        for field, error_msgs in st.session_state.validation_errors_merchant.items():
            st.error(f"Field {field}: {', '.join(error_msgs)}")

    # Display order history
    if st.session_state.get('full_selected_order_merchant') and 'history' in st.session_state.full_selected_order_merchant:
        st.subheader("Order History")
        history_df = pd.DataFrame(st.session_state.full_selected_order_merchant['history'])
        if not history_df.empty:
            history_df = history_df.sort_values(by="timestamp", ascending=False)
            st.dataframe(history_df[["timestamp", "actor", "action"]])
        else:
            st.write("No history found.")
else:
    st.info("Select an order from the sidebar to process.")

st.sidebar.info("This is a prototype Merchant application for the CIRCLE Wine Language project.")
