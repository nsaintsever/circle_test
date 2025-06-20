import streamlit as st
import pandas as pd
from streamlit_utils import (
    get_allowed_values_for_champ,
    get_circle_code_from_display_value, # For parsing C10
    create_new_order_api,
    get_orders_for_actor_api,
    CHAMPS_CSV_DIR
)
import os
import json
import re

# --- Configuration ---
BROKER_ID = "Broker_X1" # Simulate a logged-in broker

# --- Helper Functions ---
def sort_key_for_champ_code(item_tuple):
    code = item_tuple[0]
    match = re.match(r"C(\d+)([A-Z]*)", code)
    if match:
        numeric_part = int(match.group(1))
        alpha_part = match.group(2) if match.group(2) else ""
        return (numeric_part, alpha_part)
    return (float('inf'), code)

def get_all_champ_codes_and_names_broker():
    """Scans the champs_csv directory to get all C-codes and their descriptive names."""
    champs = {}
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__)) # Path relative to this script
        effective_csv_dir = os.path.join(script_dir, CHAMPS_CSV_DIR)

        if not os.path.isdir(effective_csv_dir):
            # Fallback for environments where __file__ might not be as expected (e.g. some Streamlit cloud setups)
            # or if the script is not at the root with champs_csv as a direct subdir.
            effective_csv_dir = os.path.join(os.getcwd(), CHAMPS_CSV_DIR)
            if not os.path.isdir(effective_csv_dir):
                st.error(f"Champs CSV directory not found. Looked in: {os.path.join(script_dir, CHAMPS_CSV_DIR)} and {os.path.join(os.getcwd(), CHAMPS_CSV_DIR)}")
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
        st.error(f"Error scanning champs_csv directory ('{effective_csv_dir}'): {e}")
        return {}

    if not champs:
        st.warning("No champ CSV files found or parsed. Ensure 'champs_csv' directory is present and populated correctly relative to the application.")
        return {}

    sorted_champs = dict(sorted(champs.items(), key=sort_key_for_champ_code))
    return sorted_champs

ALL_CHAMPS_INFO = get_all_champ_codes_and_names_broker()

def display_order_form(existing_order_data=None):
    """Displays the form for creating or editing an order, making all fields editable."""
    if existing_order_data is None:
        existing_order_data = {}

    st.subheader("Order Details (CIRCLE Fields)")
    order_inputs = {}

    validation_config = {}
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "config", "circle_validations.json")
        if not os.path.exists(config_path):
             config_path = os.path.join(os.getcwd(), "config", "circle_validations.json") # Fallback

        with open(config_path, 'r', encoding='utf-8') as f_config:
            validation_config = json.load(f_config)
    except FileNotFoundError:
        st.warning(f"config/circle_validations.json not found. Using default field names.")
    except json.JSONDecodeError:
        st.warning("Error decoding config/circle_validations.json. Using default field names.")

    cols = st.columns(2)
    field_idx = 0

    for code, auto_generated_name_with_code in ALL_CHAMPS_INFO.items():
        descriptive_name = validation_config.get(code, {}).get("name", auto_generated_name_with_code.split(" - ", 1)[-1])
        field_label = f"{code}: {descriptive_name}"

        current_val_for_field = str(existing_order_data.get(code, ""))
        allowed_vals = get_allowed_values_for_champ(code) # from streamlit_utils

        with cols[field_idx % 2]:
            if allowed_vals:
                idx = 0
                # For C10, current_val_for_field might be just the code, but allowed_vals are formatted
                if code == "C10" and current_val_for_field:
                    # Find the formatted string that starts with the current_val_for_field (CircleCode)
                    found_formatted_val = next((fv for fv in allowed_vals if fv.startswith(current_val_for_field + " - ")), None)
                    if found_formatted_val and found_formatted_val in allowed_vals:
                        idx = allowed_vals.index(found_formatted_val)
                    elif not current_val_for_field and allowed_vals: # If current val is empty, default to first option
                        idx = 0
                elif current_val_for_field and current_val_for_field in allowed_vals:
                    idx = allowed_vals.index(current_val_for_field)
                elif allowed_vals: # Default to first option if current_val is not in list or empty
                    idx = 0

                if allowed_vals:
                    order_inputs[code] = st.selectbox(field_label, options=allowed_vals, index=idx, key=f"form_{code}")
                else: # Fallback if allowed_vals list is empty (should not happen if CSV has data)
                    order_inputs[code] = st.text_input(field_label, value=current_val_for_field, key=f"form_{code}")
            else:
                default_text_value = current_val_for_field
                if code == "C11" and not current_val_for_field: # Default for Vintage if empty
                    default_text_value = "NV"
                order_inputs[code] = st.text_input(field_label, value=default_text_value, key=f"form_{code}")
        field_idx += 1

    receiver_castle_id = st.text_input("Send to Castle ID", value="Castle_Main_A", key="receiver_id")
    return order_inputs, receiver_castle_id

# --- Main App Logic ---
st.set_page_config(layout="wide")
st.title(f"Broker App ({BROKER_ID})")

tab1, tab2 = st.tabs(["Create New Order", "My Sent Orders"])

with tab1:
    st.header("Create and Send New Wine Order")

    if 'broker_form_data' not in st.session_state:
        st.session_state.broker_form_data = {}

    current_inputs, receiver_id = display_order_form(st.session_state.broker_form_data)

    if st.button("Send Order to Castle", key="send_order"):
        # C10 and C11 are critical for the API payload structure
        c10_display_val = current_inputs.get("C10", "")
        c11_value_for_api = current_inputs.get("C11", "") # This is direct text input

        if not c10_display_val or not c11_value_for_api: # Basic check
            st.error("Product Code (C10) and Vintage (C11) are mandatory.")
        else:
            c10_code_for_api = get_circle_code_from_display_value(c10_display_val)

            # Prepare data for API
            # The API's CircleOrderData model expects C10 and C11 as separate top-level fields,
            # and the rest in `circle_data`.
            api_payload_circle_data = {}
            for key, value in current_inputs.items():
                if key not in ["C10", "C11"] and value: # Only include if value is not empty
                    api_payload_circle_data[key] = value

            # Add C10 and C11 to the main data dict if they are not already there (they might be if not primary editable)
            # However, the API structure takes them separately and then merges.
            # For clarity, ensure they are *not* in api_payload_circle_data if they are the primary C10/C11 from selectbox/text input.
            # The current_inputs already reflects the form state.

            # The `create_new_order_api` expects `order_data` (which is `circle_data`),
            # and separate `c10_val`, `c11_val`.
            # So, `current_inputs` should be filtered to not include C10/C11 for the `order_data` part.

            final_circle_data_for_api = {k: v for k, v in current_inputs.items() if k not in ['C10', 'C11'] and v}
            # Ensure C10 and C11 are not in this dict if they were captured by specific widgets.
            # The API will reconstruct the full data dict including the top-level C10, C11.

            st.info(f"Sending order with C10: {c10_code_for_api}, C11: {c11_value_for_api} to Castle ID: {receiver_id}...")

            api_response = create_new_order_api(
                order_data=final_circle_data_for_api,
                c10_val=c10_code_for_api,
                c11_val=c11_value_for_api,
                sender=BROKER_ID,
                receiver=receiver_id
            )

            if api_response and "cle" in api_response:
                st.success(f"Order created successfully! CLE: {api_response['cle']}")
                st.json(api_response)
                st.session_state.broker_form_data = {}
                st.experimental_rerun()
            elif api_response and "detail" in api_response:
                st.error(f"API Error: {api_response['detail']}")
            else:
                st.error("Failed to create order. Check API connection or logs.")

with tab2:
    st.header("My Sent Orders")
    st.info("This section will show orders initiated by this broker.")

    if st.button("Refresh Sent Orders"):
        st.session_state.broker_sent_orders = None

    if 'broker_sent_orders' not in st.session_state or st.session_state.broker_sent_orders is None:
        # Placeholder: Fetch orders sent by this broker.
        # Needs API endpoint like /orders/sender/{broker_id} or similar logic.
        # For now, simulate by fetching orders for Castle_Main_A and filtering.
        potential_orders = get_orders_for_actor_api("Castle_Main_A")
        if potential_orders is not None:
            st.session_state.broker_sent_orders = [
                order for order in potential_orders if order.get("sender") == BROKER_ID and order.get("status") == "New"
            ]
        else:
            st.session_state.broker_sent_orders = []

    if st.session_state.broker_sent_orders:
        for order in st.session_state.broker_sent_orders:
            with st.expander(f"Order CLE: {order['cle']} - Status: {order['status']} - To: {order['receiver']}"):
                st.json(order['data'])
                st.text(f"Last Updated: {order['last_updated']}")
    elif isinstance(st.session_state.broker_sent_orders, list) and not st.session_state.broker_sent_orders:
        st.write("No orders found that were recently sent by you to Castle_Main_A and are still 'New'.")
    else:
        st.error("Could not retrieve orders from API.")

st.sidebar.info("This is a prototype Broker application for the CIRCLE Wine Language project.")
