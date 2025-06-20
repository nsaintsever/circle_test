import streamlit as st
import pandas as pd
from src import order_management
from src import database

# Initialize database (ensure tables are created)
database.initialize_database()
# Load CIRCLE config (important for validation)
order_management.load_circle_config()

# --- App State Management ---
if 'selected_order_cle_castle' not in st.session_state:
    st.session_state.selected_order_cle_castle = None
if 'castle_id' not in st.session_state:
    st.session_state.castle_id = "castle_default_id" # Simple default for now

st.set_page_config(layout="wide")
st.title("Castle Wine Order Management")

st.sidebar.header("Castle Actions")
current_castle_id = st.sidebar.text_input("Your Castle ID", value=st.session_state.castle_id)
st.session_state.castle_id = current_castle_id

# --- Helper Functions ---
def refresh_orders_castle():
    """Force rerun to refresh order lists."""
    st.experimental_rerun()

def display_castle_order_details(order_cle):
    order = order_management.get_order_details(order_cle)
    if order:
        st.subheader(f"Order Details: {order['cle']}")
        col1, col2 = st.columns(2)
        with col1:
            st.text(f"Status: {order['status']}")
            st.text(f"Current Holder: {order['current_holder']}")
            st.text(f"Broker (Creator): {order['created_by']}") # Assuming created_by is the broker
            st.text(f"Last Modified By: {order['last_modified_by']}")
            st.text(f"Created At: {order['created_at']}")
            st.text(f"Updated At: {order['updated_at']}")

        with col2:
            st.write("CIRCLE Data:")
            st.json(order['circle_data'])

        # --- Edit Order Section (Simplified by Castle) ---
        st.subheader("Edit Order Data (Castle)")
        # This is highly simplified. A robust solution needs dynamic form generation based on circle_validations.json
        # and field-level permissions/editability rules for Castle.

        editable_data = order['circle_data'].copy()

        # Example: Castle might confirm/adjust C11 (Vintage) or C40 (Quantity)
        # and add a C_CASTLE_NOTE
        editable_data['C11'] = st.text_input("Vintage (C11)", value=editable_data.get('C11', ''), key=f"edit_c11_{order_cle}")
        editable_data['C40'] = st.text_input("Quantity (C40)", value=editable_data.get('C40', ''), key=f"edit_c40_{order_cle}")
        editable_data['C_CASTLE_LOGISTIC_INFO'] = st.text_area("Castle Logistic Info / Notes",
                                                              value=editable_data.get('C_CASTLE_LOGISTIC_INFO', ''),
                                                              key=f"edit_clogistic_{order_cle}")

        if st.button("Save Changes by Castle", key=f"save_castle_{order_cle}"):
            if order_management.update_order_details(order_cle, editable_data, st.session_state.castle_id):
                st.success(f"Order {order_cle} updated successfully by Castle.")
                refresh_orders_castle()
            else:
                st.error(f"Failed to update order {order_cle}. Potential validation errors or other issues. Check the application console for more details.")

        # --- Actions for this order by Castle ---
        st.subheader("Castle Order Actions")
        if order['current_holder'] == st.session_state.castle_id:
            # Option 1: Send to Merchant
            if order['status'] in ["pending_castle_review", "merchant_amended"]: # Statuses where Castle can send to Merchant
                target_merchant_id = st.text_input("Target Merchant ID", value="merchant_default_id", key=f"target_merchant_{order_cle}")
                if st.button("Send to Merchant", key=f"send_merchant_{order_cle}"):
                    if not target_merchant_id.strip():
                        st.warning("Please enter a Target Merchant ID.")
                    else:
                        # Potentially re-validate before sending
                        # For now, direct transition
                        if order_management.transition_order_status(order_cle, "pending_merchant_approval", target_merchant_id, st.session_state.castle_id):
                            st.success(f"Order {order_cle} sent to Merchant {target_merchant_id}.")
                            st.session_state.selected_order_cle_castle = None # Clear selection
                            refresh_orders_castle()
                        else:
                            st.error(f"Failed to send order {order_cle} to Merchant. Check console for details.")

            # Option 2: Amend and Send Back to Broker
            # Typically if status is 'pending_castle_review'
            if order['status'] == "pending_castle_review":
                # The broker ID is assumed to be stored in 'created_by' for this workflow
                broker_to_return_to = order.get('created_by')
                if broker_to_return_to:
                    if st.button("Amend and Send Back to Broker", key=f"send_broker_{order_cle}"):
                        if order_management.transition_order_status(order_cle, "castle_amended", broker_to_return_to, st.session_state.castle_id):
                            st.success(f"Order {order_cle} amended and sent back to Broker {broker_to_return_to}.")
                            st.session_state.selected_order_cle_castle = None # Clear selection
                            refresh_orders_castle()
                        else:
                            st.error(f"Failed to send order {order_cle} back to Broker. Check console for details.")
                else:
                    st.warning("Broker ID (created_by) not found for this order, cannot send back.")

            if not (order['status'] in ["pending_castle_review", "merchant_amended"]):
                 st.info(f"Order status '{order['status']}' may not allow further actions by Castle without prior changes.")

        else: # Should not happen if list filtering is correct
            st.error(f"Order is currently with {order['current_holder']}. Castle cannot take action (this message indicates a potential app logic issue).")

    else:
        st.error(f"Order with CLE {order_cle} not found.")


# --- Main Page Layout ---

# Section 1: Orders for Castle Review/Action
st.header(f"Orders for Castle: {st.session_state.castle_id}")

# Filter orders for the current castle that require action
# Statuses: 'pending_castle_review', 'merchant_amended' (when merchant sends back to castle)
orders_for_castle_pending_review = order_management.get_orders_for_actor(st.session_state.castle_id, status="pending_castle_review")
orders_for_castle_merchant_amended = order_management.get_orders_for_actor(st.session_state.castle_id, status="merchant_amended")
all_castle_orders = sorted(orders_for_castle_pending_review + orders_for_castle_merchant_amended, key=lambda x: x['updated_at'], reverse=True)


if not all_castle_orders:
    st.info(f"No orders currently require your attention, Castle {st.session_state.castle_id}.")
else:
    st.write(f"Found {len(all_castle_orders)} order(s) requiring your attention:")
    display_data = []
    for order in all_castle_orders:
        display_data.append({
            "CLE": order['cle'],
            "Status": order['status'],
            "Broker (Creator)": order.get('created_by', 'N/A'),
            "Product (C10)": order['circle_data'].get('C10', 'N/A'),
            "Vintage (C11)": order['circle_data'].get('C11', 'N/A'),
            "Qty (C40)": order['circle_data'].get('C40', 'N/A'),
            "Last Modified": order['updated_at']
        })
    df_castle = pd.DataFrame(display_data)

    st.dataframe(df_castle, use_container_width=True)

    selected_cle_from_list_castle = st.selectbox(
        "Select Order CLE from list to view/edit details:",
        options=[""] + [o['cle'] for o in all_castle_orders],
        index=0, # Default to no selection
        key="selectbox_cle_castle"
    )
    if selected_cle_from_list_castle:
        st.session_state.selected_order_cle_castle = selected_cle_from_list_castle


# Section 2: Selected Order Details (if any)
if st.session_state.selected_order_cle_castle:
    display_castle_order_details(st.session_state.selected_order_cle_castle)

st.sidebar.markdown("---")
if st.sidebar.button("Refresh Orders List (Castle)"):
    refresh_orders_castle()

# To run: streamlit run streamlit_castle.py
print(f"Castle App Refreshed. Selected CLE: {st.session_state.selected_order_cle_castle}")
print(f"Current Castle ID: {st.session_state.castle_id}")
