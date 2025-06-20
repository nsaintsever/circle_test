# CIRCLE Language Multi-Actor Order Management System

This project implements a prototype system for managing wine orders between different actors in the wine industry (Brokers, Castles, Merchants, Warehouses) using a defined "CIRCLE language" for data exchange. The system uses multiple Streamlit web applications that interact with a central SQLite database.

## Project Goal

The primary goal is to demonstrate how such a system can streamline communication and reduce reliance on emails by providing a structured workflow for creating, amending, and approving orders.

## Core Components

1.  **CIRCLE Language & Validator:**
    *   The definition of order fields and validation rules is intended to be in `config/circle_validations.json`.
    *   The `circle_validator.py` script, along with validation classes in the `validations/` directory, is responsible for ensuring data conforms to these rules.
    *   The `champs/` directory (if present and populated) would contain CSV files for lookup values used in validation (e.g., allowed product codes, regions, etc.). The `allowed_values_lookup` function in `src/order_management.py` is a placeholder for this logic.

2.  **Database (`src/database.py`):**
    *   Uses SQLite (`orders.db` created in the root directory).
    *   Stores order information, including current status, holder, and all CIRCLE field data (as a JSON blob in the `circle_data` column).

3.  **Order Management Logic (`src/order_management.py`):**
    *   Provides functions to create, retrieve, update, and transition orders.
    *   Integrates with the `CircleValidatorService` to validate data before database operations.
    *   Includes placeholder functions for `generate_cle` (order key generation), `version_lookup`, and `allowed_values_lookup`.

4.  **Streamlit Applications:**
    *   `streamlit_broker.py`: For Brokers to create new orders, manage their orders, and send them to Castles.
    *   `streamlit_castle.py`: For Castles to review orders from Brokers, amend them, send them back to Brokers, or forward them to Merchants.
    *   `streamlit_merchant.py`: For Merchants to review orders from Castles, accept them (sending to Logistics/Warehouse), or send them back to Castles for amendment.
    *   `streamlit_warehouse.py`: (Basic Scaffolding) For Warehouse/Logistics personnel to view orders that have been approved by Merchants and are ready for processing.

## Project Structure

```
.
├── config/
│   └── circle_validations.json   # Defines CIRCLE fields and validation rules (CRITICAL)
├── src/
│   ├── __init__.py
│   ├── database.py               # SQLite database setup and CRUD operations
│   └── order_management.py       # Core logic for order handling and validation
├── validations/                  # Contains different validation rule implementations
│   ├── *.py
├── circle_validator.py           # Main validator service class
├── streamlit_broker.py           # Streamlit app for Brokers
├── streamlit_castle.py           # Streamlit app for Castles
├── streamlit_merchant.py         # Streamlit app for Merchants
├── streamlit_warehouse.py        # Streamlit app for Warehouses
├── test_validations.py           # Example test script for validator (may need adjustment)
└── README.md                     # This file
```
*(Note: The `champs/` directory for CSV lookup data is assumed but not explicitly created by the agent currently).*

## Setup and Running

1.  **Prerequisites:**
    *   Python 3.7+
    *   Pip (Python package installer)

2.  **Installation:**
    *   Clone the repository.
    *   Install required packages:
        ```bash
        pip install streamlit pandas
        ```
    *   (No other external packages are used by the core logic created so far, but individual validation classes might have other dependencies if they were more complex).

3.  **Database Initialization:**
    *   The database `orders.db` and its tables are automatically created/initialized when any of the Streamlit apps are run for the first time, or when `src/database.py` or `src/order_management.py` are run directly (due to their `if __name__ == '__main__':` blocks).

4.  **Running the Streamlit Applications:**
    *   Open separate terminal windows for each actor's application.
    *   Navigate to the root directory of the project in each terminal.
    *   Run the apps using Streamlit CLI:
        ```bash
        streamlit run streamlit_broker.py
        streamlit run streamlit_castle.py
        streamlit run streamlit_merchant.py
        streamlit run streamlit_warehouse.py
        ```
    *   Each application will open in a new browser tab. You can interact with them to simulate the order workflow.

    *   **PYTHONPATH Note:** The Streamlit apps and `src/order_management.py` attempt to import `circle_validator.py` from the root directory and modules from the `src/` directory. Running `streamlit run` from the project root directory should generally make these imports work. If you encounter import errors, ensure your `PYTHONPATH` is set up to include the project root or that you are running the commands from the project root.

## Important Considerations / Current Limitations

*   **`config/circle_validations.json` Content:** The functionality of the `CircleValidatorService` heavily depends on the content of this file. If it's empty or inaccessible, validation will be minimal (based on fallback logic in `src/order_management.py` which uses an empty JSON `"{}"` for rules).
*   **`allowed_values_lookup` & `version_lookup`:** The functions `allowed_values_lookup` and `version_lookup` in `src/order_management.py` are currently mock implementations. For real validation based on external lists (e.g., from `champs/` CSVs), these need to be fully implemented.
*   **User Interface (UI):** The Streamlit apps are functional prototypes.
    *   Forms for creating/editing orders use a few hardcoded example fields. Ideally, these should be dynamically generated based on `config/circle_validations.json`.
    *   Display of CIRCLE order data is often raw JSON. This should be parsed and presented in a user-friendly way.
*   **Error Handling:** Basic error messages are in place. More sophisticated error display and feedback, especially for validation errors, would be beneficial.
*   **No User Authentication/Authorization:** The apps use simple text inputs for Actor IDs (Broker, Castle, Merchant, Warehouse). There's no actual login or permission system.
*   **State Management in Streamlit:** The apps use `st.experimental_rerun()` for refreshing. More advanced Streamlit state management (e.g., callbacks) could optimize performance and user experience for more complex apps.
*   **Notification System:** The problem description mentioned "notifications." Currently, actors need to refresh their app or periodically check to see new orders assigned to them. A real-time notification system is not implemented.

## Workflow Example

1.  **Broker (`streamlit_broker.py`):**
    *   Sets their Broker ID.
    *   Creates a new order, filling in initial CIRCLE fields.
    *   Can edit the order.
    *   Sends the order to a specific Castle ID (e.g., `castle_one`).
2.  **Castle (`streamlit_castle.py`):**
    *   Sets their Castle ID (e.g., `castle_one`).
    *   Sees the order from the Broker.
    *   Reviews and can edit the order (e.g., add logistic info, confirm quantities).
    *   Can send it back to the Broker for amendments OR send it to a Merchant ID (e.g., `merchant_alpha`).
3.  **Merchant (`streamlit_merchant.py`):**
    *   Sets their Merchant ID (e.g., `merchant_alpha`).
    *   Sees the order from the Castle.
    *   Reviews and can add their own notes/confirmations.
    *   Can send it back to the Castle for amendments OR "Accept" the order (which then sends it to a generic `logistics_department`).
4.  **Warehouse (`streamlit_warehouse.py`):**
    *   Sets their Warehouse/Logistics ID (e.g., `logistics_department`).
    *   Sees orders approved by Merchants.
    *   (Currently view-only).

This simulates a basic lifecycle of an order passing through different actors.
