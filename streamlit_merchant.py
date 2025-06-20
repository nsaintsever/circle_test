import streamlit as st
import pandas as pd
from src import order_management
from src import database

# Initialize database (ensure tables are created)
database.initialize_database()
# Load CIRCLE config (important for validation)
order_management.load_circle_config()

# --- App State Management ---
if 'selected_order_cle_merchant' not in st.session_state:
    st.session_state.selected_order_cle_merchant = None
if 'merchant_id' not in st.session_state:
    st.session_state.merchant_id = "merchant_default_id" # Simple default for now

st.set_page_config(layout="wide")
st.title("Wine Merchant Order Management")

st.sidebar.header("Merchant Actions")
current_merchant_id = st.sidebar.text_input("Your Merchant ID", value=st.session_state.merchant_id)
st.session_state.merchant_id = current_merchant_id

# --- Helper Functions ---
def refresh_orders_merchant():
    """Force rerun to refresh order lists."""
    st.experimental_rerun()

def display_merchant_order_details(order_cle):
    order = order_management.get_order_details(order_cle)
    if order:
        st.subheader(f"Order Details: {order['cle']}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text(f"Status: {order['status']}")
            st.text(f"Current Holder: {order['current_holder']}")
        with col2:
            st.text(f"Broker (Creator): {order.get('created_by', 'N/A')}")
            st.text(f"Last Modified By: {order['last_modified_by']}")
        with col3:
            st.text(f"Created At: {order['created_at']}")
            st.text(f"Updated At: {order['updated_at']}")

        st.write("CIRCLE Data:")
        st.json(order['circle_data'])

        # --- Edit Order Section (Simplified by Merchant - e.g., adding notes) ---
        st.subheader("Merchant Review & Notes")
        # Merchants might not edit core data but add their own info or confirm.
        # This is highly simplified.

        editable_data = order['circle_data'].copy()

        editable_data['C_MERCHANT_NOTES'] = st.text_area("Merchant Internal Notes",
                                                         value=editable_data.get('C_MERCHANT_NOTES', ''),
                                                         key=f"edit_mnotes_{order_cle}")
        editable_data['C_MERCHANT_CONFIRMED_QTY'] = st.text_input("Merchant Confirmed Quantity (if different)",
                                                                  value=editable_data.get('C_MERCHANT_CONFIRMED_QTY', editable_data.get('C40','')),
                                                                  key=f"edit_mqty_{order_cle}")


        if st.button("Save Merchant Notes/Confirmations", key=f"save_merchant_notes_{order_cle}"):
            # Here, we use update_order_details. The validation rules in circle_validations.json
            # would determine if a merchant can change C40 or only add notes.
            # For now, our mock validator is permissive.
            if order_management.update_order_details(order_cle, editable_data, st.session_state.merchant_id):
                st.success(f"Merchant notes/confirmations for order {order_cle} saved.")
                refresh_orders_merchant()
            else:
                st.error(f"Failed to save merchant notes for order {order_cle}. Potential validation errors or other issues. Check the application console for more details.")

        # --- Actions for this order by Merchant ---
        st.subheader("Merchant Order Actions")
        if order['current_holder'] == st.session_state.merchant_id:
            if order['status'] == "pending_merchant_approval":
                # Option 1: Accept Order
                if st.button("✅ Accept Order", key=f"accept_order_{order_cle}"):
                    # Transition status to 'merchant_approved'. Holder could remain merchant or go to warehouse/logistics.
                    # For now, let's say it goes to a generic 'Logistics' holder.
                    logistics_id = "logistics_department" # Example next holder
                    if order_management.transition_order_status(order_cle, "merchant_approved", logistics_id, st.session_state.merchant_id):
                        st.success(f"Order {order_cle} ACCEPTED and sent to {logistics_id}.")
                        st.session_state.selected_order_cle_merchant = None # Clear selection
                        refresh_orders_merchant()
                    else:
                            st.error(f"Failed to accept order {order_cle}. Check console for details.")

                st.markdown("---") # Visual separator

                # Option 2: Amend and Send Back to Castle
                # The Castle ID would be the previous holder. We need to fetch it.
                # For simplicity, we assume the 'last_modified_by' before it came to merchant was the castle.
                # This is a simplification; a robust system would track the path or have designated return points.
                # Let's assume the castle that sent it is identifiable, e.g. from a field or previous holder history.
                # For this demo, we'll need a way to determine the castle.
                # We can't reliably use last_modified_by if merchant saved notes.
                # Let's just hardcode a castle ID to send back to for now, or require input.

                castle_to_return_to_input = st.text_input("Castle ID to Send Back To (if amending)", value=order.get('last_modified_by', 'castle_default_id'), key=f"return_castle_{order_cle}")
                reason_for_return = st.text_area("Reason for sending back to Castle", key=f"reason_return_{order_cle}")

                if st.button("⚠️ Amend and Send Back to Castle", key=f"send_back_castle_{order_cle}"):
                    if not castle_to_return_to_input.strip():
                        st.warning("Please specify the Castle ID to return the order to.")
                    elif not reason_for_return.strip():
                        st.warning("Please provide a reason for sending the order back to the Castle.")
                    else:
                        # Add reason to order data? Could be a specific CIRCLE field or a temporary note.
                        # For now, the reason is just for the UI.
                        updated_data_for_return = order['circle_data'].copy()
                        updated_data_for_return['C_MERCHANT_RETURN_REASON'] = reason_for_return

                        # First, save any changes including the return reason
                        order_management.update_order_details(order_cle, updated_data_for_return, st.session_state.merchant_id)

                        # Then, transition
                        if order_management.transition_order_status(order_cle, "merchant_amended", castle_to_return_to_input, st.session_state.merchant_id):
                            st.success(f"Order {order_cle} amended and sent back to Castle {castle_to_return_to_input}.")
                            st.session_state.selected_order_cle_merchant = None # Clear selection
                            refresh_orders_merchant()
                        else:
                            st.error(f"Failed to send order {order_cle} back to Castle. Check console for details.")
            else:
                st.info(f"Order status is '{order['status']}'. No direct actions available for Merchant at this stage.")
        else: # Should not happen
            st.error(f"Order is currently with {order['current_holder']}. Merchant cannot take action (this message indicates a potential app logic issue).")
    else:
        st.error(f"Order with CLE {order_cle} not found.")

# --- Main Page Layout ---

# Section 1: Orders for Merchant Review/Action
st.header(f"Orders for Merchant: {st.session_state.merchant_id}")

# Filter orders for the current merchant that require action
# Status: 'pending_merchant_approval'
orders_for_merchant = order_management.get_orders_for_actor(st.session_state.merchant_id, status="pending_merchant_approval")
all_merchant_orders = sorted(orders_for_merchant, key=lambda x: x['updated_at'], reverse=True)


if not all_merchant_orders:
    st.info(f"No orders currently require your approval, Merchant {st.session_state.merchant_id}.")
else:
    st.write(f"Found {len(all_merchant_orders)} order(s) requiring your approval:")
    display_data = []
    for order in all_merchant_orders:
        display_data.append({
            "CLE": order['cle'],
            "Status": order['status'],
            "Broker (Creator)": order.get('created_by', 'N/A'),
            "Castle (Prev Holder?)": order.get('last_modified_by', 'N/A'), # Simplification
            "Product (C10)": order['circle_data'].get('C10', 'N/A'),
            "Qty (C40)": order['circle_data'].get('C40', 'N/A'),
            "Last Modified": order['updated_at']
        })
    df_merchant = pd.DataFrame(display_data)

    st.dataframe(df_merchant, use_container_width=True)

    selected_cle_from_list_merchant = st.selectbox(
        "Select Order CLE from list to view/action:",
        options=[""] + [o['cle'] for o in all_merchant_orders],
        index=0, # Default to no selection
        key="selectbox_cle_merchant"
    )
    if selected_cle_from_list_merchant:
        st.session_state.selected_order_cle_merchant = selected_cle_from_list_merchant

# Section 2: Selected Order Details (if any)
if st.session_state.selected_order_cle_merchant:
    display_merchant_order_details(st.session_state.selected_order_cle_merchant)

st.sidebar.markdown("---")
if st.sidebar.button("Refresh Orders List (Merchant)"):
    refresh_orders_merchant()

# To run: streamlit run streamlit_merchant.py
print(f"Merchant App Refreshed. Selected CLE: {st.session_state.selected_order_cle_merchant}")
print(f"Current Merchant ID: {st.session_state.merchant_id}")
