import streamlit as st
import pandas as pd
from src import order_management
from src import database

# Initialize database (ensure tables are created)
database.initialize_database()
# Load CIRCLE config (important for validation)
# This will print errors if config is not found/valid, but app will try to run.
order_management.load_circle_config()

# --- App State Management ---
if 'selected_order_cle' not in st.session_state:
    st.session_state.selected_order_cle = None
if 'broker_id' not in st.session_state:
    st.session_state.broker_id = "broker_default_user" # Simple default for now

st.set_page_config(layout="wide")
st.title("Broker Wine Order Management")

st.sidebar.header("Broker Actions")
current_broker_id = st.sidebar.text_input("Your Broker ID", value=st.session_state.broker_id)
st.session_state.broker_id = current_broker_id

# --- Helper Functions ---
def refresh_orders():
    """Force rerun to refresh order lists."""
    st.experimental_rerun()

def display_order_details(order_cle):
    order = order_management.get_order_details(order_cle)
    if order:
        st.subheader(f"Order Details: {order['cle']}")
        col1, col2 = st.columns(2)
        with col1:
            st.text(f"Status: {order['status']}")
            st.text(f"Current Holder: {order['current_holder']}")
            st.text(f"Created By: {order['created_by']}")
            st.text(f"Last Modified By: {order['last_modified_by']}")
            st.text(f"Created At: {order['created_at']}")
            st.text(f"Updated At: {order['updated_at']}")

        with col2:
            st.write("CIRCLE Data:")
            # For now, just display the JSON. A real app would have specific widgets.
            st.json(order['circle_data'])

        # --- Edit Order Section (Simplified) ---
        st.subheader("Edit Order Data (Simplified)")
        # In a real app, this would be a dynamic form based on circle_validations.json
        # For now, we'll allow editing a few sample fields.
        # This is highly simplified. A robust solution needs dynamic form generation.

        editable_data = order['circle_data'].copy()

        # Example: Allow editing C40 (Quantity) and a new field C_BROKER_NOTE
        editable_data['C40'] = st.text_input("Quantity (C40)", value=editable_data.get('C40', ''))
        editable_data['C_BROKER_NOTE'] = st.text_area("Broker Note", value=editable_data.get('C_BROKER_NOTE', ''))

        if st.button("Save Changes", key=f"save_{order_cle}"):
            if order_management.update_order_details(order_cle, editable_data, st.session_state.broker_id):
                st.success(f"Order {order_cle} updated successfully.")
                refresh_orders()
            else:
                st.error(f"Failed to update order {order_cle}. Potential validation errors or other issues. Check the application console for more details.")

        # --- Actions for this order ---
        st.subheader("Order Actions")
        if order['current_holder'] == st.session_state.broker_id: # Only if broker currently owns it
            if order['status'] in ["new_draft", "castle_amended"]: # Example statuses allowing send to castle
                target_castle_id = st.text_input("Target Castle ID", value="castle_default_id", key=f"target_castle_{order_cle}")
                if st.button("Send to Castle", key=f"send_castle_{order_cle}"):
                    if not target_castle_id.strip():
                        st.warning("Please enter a Target Castle ID.")
                    else:
                        if order_management.transition_order_status(order_cle, "pending_castle_review", target_castle_id, st.session_state.broker_id):
                            st.success(f"Order {order_cle} sent to Castle {target_castle_id}.")
                            st.session_state.selected_order_cle = None # Clear selection
                            refresh_orders()
                        else:
                            st.error(f"Failed to send order {order_cle} to Castle. Check console for details.")
            else:
                st.info(f"Order status '{order['status']}' does not allow sending to Castle directly by Broker.")
        else:
            st.info(f"Order is currently with {order['current_holder']}. Broker cannot take action.")

    else:
        st.error(f"Order with CLE {order_cle} not found.")

# --- Main Page Layout ---

# Section 1: Create New Order
st.header("Create New Wine Order")
with st.expander("New Order Form", expanded=False):
    # These are placeholder fields. A real app would derive this from config.
    st.write("Enter initial order information (example fields):")
    new_order_data = {}
    col1, col2 = st.columns(2)
    with col1:
        new_order_data['C0'] = st.text_input("Version (C0)", "11") # Example default
        new_order_data['C1'] = st.text_input("Document Type (C1)", "A0") # Example default
        new_order_data['C10'] = st.text_input("Product Code (C10)", placeholder="e.g., BORDEAUX_SUPERIEUR_2022")
    with col2:
        new_order_data['C11'] = st.text_input("Vintage (C11)", placeholder="e.g., 2022")
        new_order_data['C40'] = st.text_input("Quantity (C40)", placeholder="e.g., 1200")
        # Add more fields as needed for initial creation
        # For example, buyer/seller info might be part of CIRCLE or app-level metadata

    # Forcing broker ID for creation
    creator_id = st.session_state.broker_id

    if st.button("Create New Order"):
        if not all([new_order_data.get('C0'), new_order_data.get('C1'), new_order_data.get('C10'), new_order_data.get('C11'), new_order_data.get('C40')]):
            st.warning("Please fill in all example fields.")
        else:
            st.write("Attempting to create order with data:", new_order_data) # Debug
            created_cle = order_management.create_new_order(
                initial_order_data=new_order_data,
                creator_id=creator_id,
                broker_id=st.session_state.broker_id # The broker themselves is the initial holder
            )
            if created_cle:
                st.success(f"New order created successfully! CLE: {created_cle}")
                st.session_state.selected_order_cle = created_cle # Select the new order
                refresh_orders()
            else:
                st.error("Failed to create new order. Potential validation errors or other issues. Check the application console for more details.")

# Section 2: List of Orders
st.header("Your Orders")
# For simplicity, showing all orders. Could be filtered by `created_by` or `current_holder` == broker_id
# Let's filter for orders relevant to this broker (either created by them or currently held by them)
my_orders = order_management.get_orders_for_actor(st.session_state.broker_id)
created_by_me = [o for o in database.get_orders_for_holder(holder_id=None) if o['created_by'] == st.session_state.broker_id] # Crude way to get all orders by creator
combined_orders_dict = {o['cle']: o for o in my_orders}
for o in created_by_me:
    if o['cle'] not in combined_orders_dict:
        combined_orders_dict[o['cle']] = o

all_relevant_orders = sorted(list(combined_orders_dict.values()), key=lambda x: x['created_at'], reverse=True)


if not all_relevant_orders:
    st.info("No orders found for this Broker ID or created by this Broker ID.")
else:
    # Create a DataFrame for display
    display_data = []
    for order in all_relevant_orders:
        display_data.append({
            "CLE": order['cle'],
            "Status": order['status'],
            "Holder": order['current_holder'],
            "Product (C10)": order['circle_data'].get('C10', 'N/A'),
            "Vintage (C11)": order['circle_data'].get('C11', 'N/A'),
            "Qty (C40)": order['circle_data'].get('C40', 'N/A'),
            "Created At": order['created_at']
        })
    df = pd.DataFrame(display_data)

    st.dataframe(df, use_container_width=True)

    selected_cle_from_list = st.selectbox(
        "Select Order CLE from list to view/edit details:",
        options=[""] + [o['cle'] for o in all_relevant_orders],
        index=0, # Default to no selection
        key="selectbox_cle"
    )
    if selected_cle_from_list:
        st.session_state.selected_order_cle = selected_cle_from_list


# Section 3: Selected Order Details (if any)
if st.session_state.selected_order_cle:
    display_order_details(st.session_state.selected_order_cle)

st.sidebar.markdown("---")
if st.sidebar.button("Refresh Orders List"):
    refresh_orders()

# To run this app: streamlit run streamlit_broker.py
# Ensure src/ is in PYTHONPATH or accessible.
# Running from the repo root usually works if src/ is a direct subdirectory.
# The CircleValidatorService might print errors to console if config/circle_validations.json is not found or empty.
# The allowed_values_lookup and version_lookup in order_management.py are currently mocks.
# Real validation will depend on the content of circle_validations.json and proper implementation of those lookups.
print(f"Broker App Refreshed. Selected CLE: {st.session_state.selected_order_cle}")
print(f"Current Broker ID: {st.session_state.broker_id}")

# A note on `st.experimental_rerun()`:
# It's generally better to use callbacks or other state management techniques to avoid full reruns if possible,
# but for simplicity in this initial version, it's used to refresh data displays.
# Consider Streamlit's callback features for more complex interactions.
# (e.g., on_click for buttons that modify state and then parts of UI update reactively)
