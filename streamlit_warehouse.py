import streamlit as st
import pandas as pd
from src import order_management
from src import database

# Initialize database (ensure tables are created)
database.initialize_database()
# Load CIRCLE config (important for validation, though not actively used for editing here yet)
order_management.load_circle_config()

# --- App State Management ---
if 'selected_order_cle_warehouse' not in st.session_state:
    st.session_state.selected_order_cle_warehouse = None
if 'warehouse_id' not in st.session_state:
    # Warehouses might be identified by a specific ID or a general role like 'logistics_department'
    st.session_state.warehouse_id = "logistics_department"
                                    # This aligns with where Merchant app sends approved orders.
                                    # Or, could be a specific warehouse ID e.g., "warehouse_bordeaux_main"

st.set_page_config(layout="wide")
st.title("Warehouse Order View")

st.sidebar.header("Warehouse Info")
current_warehouse_id = st.sidebar.text_input("Your Warehouse/Logistics ID", value=st.session_state.warehouse_id)
st.session_state.warehouse_id = current_warehouse_id

# --- Helper Functions ---
def refresh_orders_warehouse():
    """Force rerun to refresh order lists."""
    st.experimental_rerun()

def display_warehouse_order_details(order_cle):
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

        st.write("CIRCLE Data (Full):")
        st.json(order['circle_data'])

        # --- Warehouse Specific View (Placeholder) ---
        st.subheader("Key Logistical Information (Example)")
        # In a real app, this would show specific fields relevant to warehouse operations
        # e.g., C40 (Quantity), C41 (Packaging), Delivery Address fields, etc.
        # These would be extracted from order['circle_data'] based on circle_validations.json

        logistics_info = {
            "Product Code (C10)": order['circle_data'].get('C10'),
            "Vintage (C11)": order['circle_data'].get('C11'),
            "Quantity (C40)": order['circle_data'].get('C40'),
            "Packaging (C41)": order['circle_data'].get('C41', 'N/A'), # Example field
            "Merchant Confirmed Qty": order['circle_data'].get('C_MERCHANT_CONFIRMED_QTY'),
            "Castle Logistic Info": order['circle_data'].get('C_CASTLE_LOGISTIC_INFO'),
            "Delivery Info (Placeholder)": "To be defined from CIRCLE fields"
        }
        st.table(pd.DataFrame([logistics_info]).T.rename(columns={0:"Value"}))

        # No editing or actions in this basic scaffolding for Warehouse
        st.info("This is a view-only interface for warehouse personnel in its current version.")

    else:
        st.error(f"Order with CLE {order_cle} not found.")

# --- Main Page Layout ---

# Section 1: Orders for Warehouse
st.header(f"Orders for Warehouse/Logistics ID: {st.session_state.warehouse_id}")

# Filter orders for the current warehouse/logistics department
# Typically, these would be orders in a status like 'merchant_approved' or 'ready_for_dispatch'
# and held by the warehouse_id or a general logistics ID.
orders_for_warehouse = order_management.get_orders_for_actor(st.session_state.warehouse_id, status="merchant_approved")
# You might also include other statuses if the workflow dictates, e.g., "in_transit", "delivered"
# For now, just 'merchant_approved' as set by the Merchant App.

all_warehouse_orders = sorted(orders_for_warehouse, key=lambda x: x['updated_at'], reverse=True)


if not all_warehouse_orders:
    st.info(f"No orders currently assigned to {st.session_state.warehouse_id} with status 'merchant_approved'.")
else:
    st.write(f"Found {len(all_warehouse_orders)} order(s) for processing/viewing:")
    display_data = []
    for order in all_warehouse_orders:
        display_data.append({
            "CLE": order['cle'],
            "Status": order['status'],
            "Product (C10)": order['circle_data'].get('C10', 'N/A'),
            "Quantity (C40)": order['circle_data'].get('C40', 'N/A'),
            "Merchant Confirmed Qty": order['circle_data'].get('C_MERCHANT_CONFIRMED_QTY', 'N/A'),
            "Castle Logistic Info": order['circle_data'].get('C_CASTLE_LOGISTIC_INFO', 'N/A'),
            "Updated At": order['updated_at']
        })
    df_warehouse = pd.DataFrame(display_data)

    st.dataframe(df_warehouse, use_container_width=True)

    selected_cle_from_list_warehouse = st.selectbox(
        "Select Order CLE from list to view details:",
        options=[""] + [o['cle'] for o in all_warehouse_orders],
        index=0, # Default to no selection
        key="selectbox_cle_warehouse"
    )
    if selected_cle_from_list_warehouse:
        st.session_state.selected_order_cle_warehouse = selected_cle_from_list_warehouse

# Section 2: Selected Order Details (if any)
if st.session_state.selected_order_cle_warehouse:
    display_warehouse_order_details(st.session_state.selected_order_cle_warehouse)

st.sidebar.markdown("---")
if st.sidebar.button("Refresh Orders List (Warehouse)"):
    refresh_orders_warehouse()

# To run: streamlit run streamlit_warehouse.py
print(f"Warehouse App Refreshed. Selected CLE: {st.session_state.selected_order_cle_warehouse}")
print(f"Current Warehouse/Logistics ID: {st.session_state.warehouse_id}")
