import streamlit as st
import pandas as pd
from streamlit_utils import (
    get_allowed_values_for_champ,
    get_champ_details,
    create_new_order_api,
    get_orders_for_actor_api,
    CHAMPS_CSV_DIR # For constructing descriptions or listing all champs
)
import os
import json
import re

# --- Configuration ---
BROKER_ID = "Broker_X1" # Simulate a logged-in broker

# --- Helper Functions ---
# CHAMPS_CSV_DIR is already imported from streamlit_utils, no need to redefine unless path is different for this specific app

def sort_key_for_champ_code(item_tuple): # item_tuple is like ('C10', 'Product Name')
    code = item_tuple[0]
    match = re.match(r"C(\d+)([A-Z]*)", code) # Match from the start of the string
    if match:
        numeric_part = int(match.group(1))
        alpha_part = match.group(2) if match.group(2) else "" # Ensure alpha_part is always a string
        return (numeric_part, alpha_part)
    # Fallback for any codes not matching C<digits><optional_letters>
    return (float('inf'), code)

def get_all_champ_codes_and_names_broker(): # Renamed to avoid conflict if streamlit_utils also has one
    """Scans the champs_csv directory to get all C-codes and their descriptive names."""
    champs = {}
    # Use a more robust path relative to this script file for CHAMPS_CSV_DIR
    # This assumes streamlit_utils.CHAMPS_CSV_DIR is correctly set up if we used it directly
    # For direct use in this app file:
    try:
        # Construct path relative to this file
        # current_script_path = os.path.dirname(os.path.abspath(__file__)) # This might not work well in Streamlit's execution model
        # effective_csv_dir = os.path.join(current_script_path, CHAMPS_CSV_DIR)

        # Given streamlit_utils.CHAMPS_CSV_DIR is "champs_csv", assume it's relative to CWD when script runs
        # Or, if streamlit_utils.py is in the same dir as broker_app.py, this is fine.
        # Let's rely on the pathing within streamlit_utils.load_champ_csv which tries to be robust.
        # For this specific function, if it's only for names, we can listdir directly.

        # Simplification: Assume CHAMPS_CSV_DIR is accessible from CWD or correctly pathed by streamlit_utils
        # If this function is only for names and ALL_CHAMPS_INFO, direct access is fine.

        # Path relative to the current script file
        script_dir = os.path.dirname(__file__)
        effective_csv_dir = os.path.join(script_dir, CHAMPS_CSV_DIR)

        if not os.path.isdir(effective_csv_dir):
             # Fallback: if not found relative to script, try relative to CWD
            effective_csv_dir = os.path.join(os.getcwd(), CHAMPS_CSV_DIR)
            if not os.path.isdir(effective_csv_dir):
                st.error(f"Champs CSV directory not found at {CHAMPS_CSV_DIR} or {effective_csv_dir}. Please ensure it's in the correct location.")
                return {}

        for f in os.listdir(effective_csv_dir):
            if f.startswith("C") and f.endswith(".csv"):
                # Try to extract code like C1, C10, C52E from filenames like C1_cases.csv, C52E_specific_back_label_bats.csv
                code_match = re.match(r"(C\d+[A-Z]*)_", f)
                if not code_match: # Try simple C<number> if the first regex fails
                    code_match = re.match(r"(C\d+)_", f)

                if code_match:
                    code = code_match.group(1)
                    name_part = f[len(code)+1:].replace(".csv", "").replace("_", " ").title()
                    champs[code] = f"{code} - {name_part}" # Store descriptive name
    except Exception as e:
        st.error(f"Error scanning champs_csv directory: {e}")
        return {}

    if not champs:
        st.warning("No champ CSV files found or parsed. Ensure 'champs_csv' directory is present and populated.")
        return {}

    sorted_champs = dict(sorted(champs.items(), key=sort_key_for_champ_code))
    return sorted_champs

ALL_CHAMPS_INFO = get_all_champ_codes_and_names_broker()

# Define a smaller subset of fields that are primary for broker input
BROKER_PRIMARY_EDITABLE_FIELDS = ["C10", "C11", "C0", "C13", "C1", "C2", "C14", "C31", "C66"]
# Plus any quantity or specific order fields not in C-codes yet

def display_order_form(existing_order_data=None):
    """Displays the form for creating or editing an order, showing all fields."""
    if existing_order_data is None:
        existing_order_data = {}

    st.subheader("Order Details (CIRCLE Fields)")
    order_inputs = {}

    # Load full names from config/circle_validations.json for better descriptions
    # This should ideally be a shared utility.
    validation_config = {}
    try:
        script_dir = os.path.dirname(__file__)
        config_path = os.path.join(script_dir, "config", "circle_validations.json")
        with open(config_path, 'r', encoding='utf-8') as f_config:
            validation_config = json.load(f_config)
    except FileNotFoundError:
        st.warning("config/circle_validations.json not found. Using default field names.")
    except json.JSONDecodeError:
        st.warning("Error decoding config/circle_validations.json. Using default field names.")


    cols = st.columns(2) # Two columns for the form

    # Iterate through ALL_CHAMPS_INFO (sorted) to display all fields
    # Make BROKER_PRIMARY_EDITABLE_FIELDS editable, others will be visible but perhaps not primary input

    field_idx = 0
    for code, auto_generated_name in ALL_CHAMPS_INFO.items():
        # Use name from validation_config if available, else default to auto-generated
        descriptive_name = validation_config.get(code, {}).get("name", auto_generated_name.split(" - ", 1)[-1])
        field_label = f"{code}: {descriptive_name}"

        current_val_for_field = existing_order_data.get(code, "")
        allowed_vals = get_allowed_values_for_champ(code) # From streamlit_utils
        is_editable = code in BROKER_PRIMARY_EDITABLE_FIELDS

        with cols[field_idx % 2]:
            if is_editable:
                if allowed_vals:
                    # Ensure index is valid
                    idx = 0
                    if current_val_for_field and current_val_for_field in allowed_vals:
                        idx = allowed_vals.index(current_val_for_field)
                    elif allowed_vals: # If there are options, default to first if current_val_for_field is not among them
                        idx = 0

                    if allowed_vals: # Check again in case it became empty after filtering or something
                         order_inputs[code] = st.selectbox(field_label, options=allowed_vals, index=idx, key=f"form_{code}")
                    else: # Fallback if allowed_vals is unexpectedly empty for an editable field
                         order_inputs[code] = st.text_input(field_label, value=current_val_for_field, key=f"form_{code}")

                elif code == "C11": # Specific handling for Vintage as text input (common primary field)
                     order_inputs[code] = st.text_input(field_label, value=current_val_for_field if current_val_for_field else "2023", key=f"form_{code}")
                else: # Other primary editable fields without predefined allowed values
                    order_inputs[code] = st.text_input(field_label, value=current_val_for_field, key=f"form_{code}")
            else:
                # For non-primary fields, display them as disabled.
                # They are part of the full view but not for initial broker input.
                # We don't add them to order_inputs unless they had existing_order_data
                # This means only primarily editable fields and fields with pre-existing data are sent.
                st.text_input(field_label, value=str(current_val_for_field), disabled=True, key=f"form_{code}_readonly")
                if current_val_for_field: # If it has a value (e.g. from a loaded template), include it
                    order_inputs[code] = current_val_for_field


        field_idx += 1

    # Ensure C10 and C11 (mandatory for API) are present in order_inputs, even if they were not marked editable
    # or were somehow missed in the loop. (This is a safeguard).
    if 'C10' not in order_inputs:
        order_inputs['C10'] = st.session_state.broker_form_data.get('C10', get_allowed_values_for_champ("C10")[0] if get_allowed_values_for_champ("C10") else "")
    if 'C11' not in order_inputs:
        order_inputs['C11'] = st.session_state.broker_form_data.get('C11', "2023")


    receiver_castle_id = st.text_input("Send to Castle ID", value="Castle_Main_A", key="receiver_id")
    return order_inputs, receiver_castle_id


# --- Main App Logic ---
st.set_page_config(layout="wide")
st.title(f"Broker App ({BROKER_ID})")

tab1, tab2 = st.tabs(["Create New Order", "My Sent Orders"])

with tab1:
    st.header("Create and Send New Wine Order")

    # Initialize session state for form data if it doesn't exist
    if 'broker_form_data' not in st.session_state:
        st.session_state.broker_form_data = {}

    # Pass current form data to the display function
    current_inputs, receiver_id = display_order_form(st.session_state.broker_form_data)

    if st.button("Send Order to Castle", key="send_order"):
        if not current_inputs.get("C10") or not current_inputs.get("C11"):
            st.error("Product Code (C10) and Vintage (C11) are mandatory.")
        else:
            # The CircleOrderData model in API expects C10 and C11 separately
            # and the rest in circle_data
            c10_value = current_inputs.pop("C10")
            c11_value = current_inputs.pop("C11")

            # Simple validation for vintage format (numeric year) for now
            if not c11_value.isdigit() or not (1900 <= int(c11_value) <= 2100):
                st.error("Vintage (C11) must be a valid year (e.g., 2023).")
            else:
                st.session_state.broker_form_data = current_inputs.copy() # Save current inputs
                st.session_state.broker_form_data['C10'] = c10_value # Add back for potential redisplay
                st.session_state.broker_form_data['C11'] = c11_value


                # Here, one would typically run the CircleValidatorService
                # For this iteration, we'll skip client-side validation and rely on API/later stages
                # Or add a simplified check

                st.info(f"Sending order to Castle ID: {receiver_id}...")

                # Ensure all required fields for the API are present
                # The API will put C10 and C11 into the main data dict
                api_response = create_new_order_api(
                    order_data=current_inputs,
                    c10_val=c10_value,
                    c11_val=c11_value,
                    sender=BROKER_ID,
                    receiver=receiver_id
                )

                if api_response and "cle" in api_response:
                    st.success(f"Order created successfully! CLE: {api_response['cle']}")
                    st.json(api_response)
                    # Clear form for next order by resetting relevant session state parts
                    st.session_state.broker_form_data = {}
                    # We need to trigger a rerun to clear inputs effectively if using st.empty or similar
                    # For now, direct key access in display_order_form handles this on next run.
                    st.experimental_rerun() # Rerun to clear form
                elif api_response and "detail" in api_response: # FastAPI error
                    st.error(f"API Error: {api_response['detail']}")
                else:
                    st.error("Failed to create order. Check API connection or logs.")

with tab2:
    st.header("My Sent Orders")
    st.info("This section will show orders initiated by this broker.")

    # For now, let's just fetch orders where this broker is the 'sender'
    # A more refined query might be needed based on status transitions

    # orders = get_orders_for_actor_api(BROKER_ID) # This gets orders *for* the broker
    # We need a different way to get "sent by broker" or implement that in API
    # For now, this tab is a placeholder.

    # Let's try to list all orders and filter by sender if possible, or assume Broker is first actor.
    # This is not ideal but a workaround for now.

    # A better approach: API endpoint like /orders/sender/{sender_id}
    # For now, let's assume orders with status "New" or "PendingCastle" and sender BROKER_ID are relevant.

    if st.button("Refresh Sent Orders"):
        st.session_state.broker_sent_orders = None # Force refresh

    if 'broker_sent_orders' not in st.session_state or st.session_state.broker_sent_orders is None:
        # This is a placeholder. Ideally, the API would have a /orders?sender_id={BROKER_ID}
        # For now, we'll just show orders currently with the Castle that were sent by this broker
        # This is still not quite right, as it shows orders FOR the castle.
        # We'll simulate by fetching all orders for a common castle and filtering client-side by our broker ID.
        # This is inefficient and for demonstration only.

        # A simpler temporary solution: Fetch orders for a known next actor (e.g. Castle_Main_A)
        # and then filter if the sender was this broker.
        potential_orders = get_orders_for_actor_api("Castle_Main_A") # Orders pending for a castle
        if potential_orders is not None:
            st.session_state.broker_sent_orders = [
                order for order in potential_orders if order.get("sender") == BROKER_ID and order.get("status") == "New"
            ] # Status "New" means it was just sent to Castle_Main_A by Broker
        else:
            st.session_state.broker_sent_orders = []

    if st.session_state.broker_sent_orders:
        for order in st.session_state.broker_sent_orders:
            with st.expander(f"Order CLE: {order['cle']} - Status: {order['status']} - To: {order['receiver']}"):
                st.json(order['data'])
                st.text(f"Last Updated: {order['last_updated']}")
    elif st.session_state.broker_sent_orders == []:
        st.write("No orders found that were recently sent by you to Castle_Main_A and are still 'New'.")
    else:
        st.error("Could not retrieve orders from API.")

st.sidebar.info("This is a prototype Broker application for the CIRCLE Wine Language project.")
