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

# --- Configuration ---
BROKER_ID = "Broker_X1" # Simulate a logged-in broker

# --- Helper Functions ---
def get_all_champ_codes_and_names():
    """
    Scans the champs_csv directory to get all C-codes and their names from config.
    This is a simplified way to get the names; ideally, they come from circle_validations.json.
    """
    # For now, let's load names from the config file if possible, or derive from filenames.
    # This is a placeholder as we don't have direct access to config/circle_validations.json from here easily
    # without duplicating loading logic or making streamlit_utils more complex.
    # We'll make a simple list for now based on common fields.

    # A more robust way would be to have a utility to parse circle_validations.json
    # For this iteration, we'll manually list some important fields.
    # Or, list files and try to infer champ codes.
    champ_files = os.listdir(CHAMPS_CSV_DIR)
    champs = {}
    for f in champ_files:
        if f.startswith("C") and f.endswith(".csv"):
            code = f.split('_')[0]
            # Try to get a more descriptive name, placeholder for now
            name = f.replace(".csv", "").replace("_", " ").title()
            champs[code] = name
    # Sort by C-number
    sorted_champs = dict(sorted(champs.items(), key=lambda item: int(item[0][1:])))
    return sorted_champs

# Load field configurations (a simplified version for UI)
# In a real app, this would be more sophisticated, possibly loading from circle_validations.json
ALL_CHAMPS_INFO = get_all_champ_codes_and_names()

# Define the initial 5-10 fields a broker might fill, plus others for completeness
# These are examples; the actual UI might allow selecting from all 80
INITIAL_FIELDS_TO_DISPLAY = {
    "C0": "Version", # Version
    "C10": "Product", # Product
    "C11": "Vintage", # Vintage
    "C13": "Bottle Size", # BottleSize
    "C1": "Case Type", # Case
    "C2": "Packing Size", # PackingSize (Colisage)
    "C14": "Traffic Rights", # TrafficRight (Droits de circulation)
    "C31": "Volume", # Volume (Total volume of the order, e.g., in Liters or HL)
    "C66": "In Bond", # InBond status (Sous douane)
    # Potentially quantity fields - these are not explicit C-codes but would be part of an order.
    # For now, we assume quantity is handled implicitly or via a non-CIRCLE field initially.
}


def display_order_form(existing_order_data=None):
    """Displays the form for creating or editing an order."""
    if existing_order_data is None:
        existing_order_data = {}

    st.subheader("Order Details (CIRCLE Fields)")

    # Store inputs in a dictionary
    order_inputs = {}

    # For simplicity, we'll iterate through a defined set of fields for the form
    # A more dynamic form could be built from ALL_CHAMPS_INFO

    cols = st.columns(2)
    col_idx = 0

    # Prioritize C10 and C11 as they are crucial for CLE and API
    order_inputs['C10'] = cols[col_idx].selectbox(
        f"C10: Product",
        options=get_allowed_values_for_champ("C10"),
        index=0 if not existing_order_data.get("C10") else get_allowed_values_for_champ("C10").index(existing_order_data.get("C10", "")),
        key="form_C10"
    )
    col_idx = (col_idx + 1) % 2

    # C11 - Vintage (Manual input for now, could be dropdown if C11_vintages.csv is simple)
    order_inputs['C11'] = cols[col_idx].text_input(
        f"C11: Vintage (Year)",
        value=existing_order_data.get("C11", "2023"),
        key="form_C11"
    )
    col_idx = (col_idx + 1) % 2

    # Display other fields from INITIAL_FIELDS_TO_DISPLAY (excluding C10, C11 already handled)
    for code, name in INITIAL_FIELDS_TO_DISPLAY.items():
        if code in ["C10", "C11"]: # Already handled
            continue

        default_val = existing_order_data.get(code, "")
        allowed_vals = get_allowed_values_for_champ(code)

        with cols[col_idx]:
            if allowed_vals: # If we have a list of allowed values, use a selectbox
                try:
                    idx = allowed_vals.index(default_val) if default_val and default_val in allowed_vals else 0
                    order_inputs[code] = st.selectbox(f"{code}: {name}", options=allowed_vals, index=idx, key=f"form_{code}")
                except ValueError: # If default_val is not in options (e.g. from old data)
                    order_inputs[code] = st.selectbox(f"{code}: {name}", options=allowed_vals, index=0,  key=f"form_{code}")
            else: # Otherwise, use a text input
                order_inputs[code] = st.text_input(f"{code}: {name}", value=default_val, key=f"form_{code}")
        col_idx = (col_idx + 1) % 2

    # Add a generic way to input other C-fields for completeness, though not the primary focus for broker
    st.markdown("---")
    st.subheader("Additional CIRCLE Fields (Optional)")
    num_additional_fields = st.number_input("Number of additional fields to specify", min_value=0, max_value=20, value=0, key="num_add_fields")

    additional_inputs = {}
    if num_additional_fields > 0:
        cols_add = st.columns(2)
        for i in range(num_additional_fields):
            with cols_add[i % 2]:
                champ_code_add = st.selectbox(f"Field Code {i+1}", options=list(ALL_CHAMPS_INFO.keys()), index=0, key=f"add_code_{i}")
                champ_val_add = st.text_input(f"Value for {champ_code_add}", key=f"add_val_{i}")
                if champ_code_add and champ_val_add: # Only add if both are specified
                    additional_inputs[champ_code_add] = champ_val_add

    order_inputs.update(additional_inputs)

    # Simulate receiver (Castle for broker's initial order)
    # In a real app, this would be a selection or based on workflow rules
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
