import sqlite3
import json
import datetime

DATABASE_NAME = 'orders.db'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def initialize_database():
    """Initializes the database and creates the Orders table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Orders (
            cle TEXT PRIMARY KEY,
            current_holder TEXT,
            status TEXT,
            created_by TEXT,
            last_modified_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            circle_data TEXT -- Stores CIRCLE fields as a JSON string
        )
    ''')
    # Create a trigger to automatically update updated_at timestamp
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_orders_updated_at
        AFTER UPDATE ON Orders
        FOR EACH ROW
        BEGIN
            UPDATE Orders SET updated_at = CURRENT_TIMESTAMP WHERE cle = OLD.cle;
        END;
    ''')
    conn.commit()
    conn.close()

def create_order(cle: str, initial_data: dict, creator: str, holder: str, status: str = "new_draft"):
    """Creates a new order in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO Orders (cle, current_holder, status, created_by, last_modified_by, circle_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (cle, holder, status, creator, creator, json.dumps(initial_data)))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Error: Order with CLE {cle} already exists.")
        return None
    finally:
        conn.close()
    return cle

def get_order_by_cle(cle: str):
    """Retrieves an order by its CLE."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Orders WHERE cle = ?", (cle,))
    order_row = cursor.fetchone()
    conn.close()
    if order_row:
        order = dict(order_row)
        order['circle_data'] = json.loads(order['circle_data']) if order['circle_data'] else {}
        return order
    return None

def update_order_data(cle: str, new_data: dict, modifier: str):
    """Updates the circle_data of an existing order."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE Orders
            SET circle_data = ?, last_modified_by = ?
            WHERE cle = ?
        ''', (json.dumps(new_data), modifier, cle))
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Error: Order with CLE {cle} not found for update.")
            return False
    finally:
        conn.close()
    return True

def update_order_status(cle: str, new_status: str, new_holder: str, modifier: str):
    """Updates the status and holder of an order."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE Orders
            SET status = ?, current_holder = ?, last_modified_by = ?
            WHERE cle = ?
        ''', (new_status, new_holder, modifier, cle))
        conn.commit()
        if cursor.rowcount == 0:
            print(f"Error: Order with CLE {cle} not found for status update.")
            return False
    finally:
        conn.close()
    return True

def get_orders_for_holder(holder_id: str, status_filter: str = None):
    """Retrieves all orders for a specific holder, optionally filtered by status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM Orders WHERE current_holder = ?"
    params = [holder_id]
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    cursor.execute(query, tuple(params))
    orders_rows = cursor.fetchall()
    conn.close()

    orders = []
    for row in orders_rows:
        order = dict(row)
        order['circle_data'] = json.loads(order['circle_data']) if order['circle_data'] else {}
        orders.append(order)
    return orders

if __name__ == '__main__':
    # Example Usage & Basic Test
    initialize_database()

    print("Database initialized.")

    # Test creating an order
    sample_data_1 = {"C0": "11", "C1": "A0", "C10": "WINE001"}
    cle_1 = "ORDER123"
    if create_order(cle_1, sample_data_1, "BrokerX", "BrokerX", "draft"):
        print(f"Order {cle_1} created.")

    # Test retrieving an order
    retrieved_order = get_order_by_cle(cle_1)
    if retrieved_order:
        print(f"Retrieved order {cle_1}: {retrieved_order['circle_data']}")
        assert retrieved_order['circle_data']['C10'] == "WINE001"

    # Test updating order data
    updated_data_1 = {"C0": "11", "C1": "A0", "C10": "WINE001_MODIFIED", "C11": "2023"}
    if update_order_data(cle_1, updated_data_1, "BrokerX"):
        print(f"Order {cle_1} data updated.")
        retrieved_order_after_update = get_order_by_cle(cle_1)
        if retrieved_order_after_update:
            print(f"Retrieved order {cle_1} after data update: {retrieved_order_after_update['circle_data']}")
            assert retrieved_order_after_update['circle_data']['C10'] == "WINE001_MODIFIED"

    # Test updating order status
    if update_order_status(cle_1, "pending_castle", "CastleY", "BrokerX"):
        print(f"Order {cle_1} status updated.")
        retrieved_order_after_status_update = get_order_by_cle(cle_1)
        if retrieved_order_after_status_update:
            assert retrieved_order_after_status_update['status'] == "pending_castle"
            assert retrieved_order_after_status_update['current_holder'] == "CastleY"

    # Test getting orders for a holder
    sample_data_2 = {"C0": "12", "C1": "B1", "C10": "WINE002"}
    cle_2 = "ORDER456"
    create_order(cle_2, sample_data_2, "BrokerZ", "CastleY", "pending_castle")

    castle_y_orders = get_orders_for_holder("CastleY")
    print(f"Orders for CastleY: {len(castle_y_orders)}")
    assert len(castle_y_orders) >= 2 # Could be more if tests run multiple times

    castle_y_pending_orders = get_orders_for_holder("CastleY", status_filter="pending_castle")
    print(f"Pending orders for CastleY: {len(castle_y_pending_orders)}")
    assert len(castle_y_pending_orders) >= 2

    print("Basic database tests completed.")

    # Example of trying to create a duplicate order
    print("\nAttempting to create a duplicate order (should fail gracefully):")
    create_order(cle_1, sample_data_1, "BrokerX", "BrokerX", "draft")

    print("\nAttempting to update non-existent order:")
    update_order_data("NONEXISTENTCLE", {}, "System")
    update_order_status("NONEXISTENTCLE", "pending", "Someone", "System")

    print("\nAll example operations executed.")
