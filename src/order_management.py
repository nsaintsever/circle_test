import uuid
import hashlib
import json # Added
from pathlib import Path # Added

from . import database # Use explicit relative import
# Assuming circle_validator.py is in the parent directory relative to src/ when running as module
# Or that PYTHONPATH is set up correctly for direct execution.
# For Streamlit apps, we'll need to ensure Python can find 'circle_validator'
try:
    from circle_validator import CircleValidatorService
except ImportError:
    # This is a fallback if running src.order_management directly and circle_validator isn't in path
    # This might happen if 'src' is not treated as part of a larger package.
    # For robust solution, project structure and PYTHONPATH needs to be well-defined.
    import sys
    sys.path.append(str(Path(__file__).resolve().parent.parent)) # Add repo root to path
    from circle_validator import CircleValidatorService


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "circle_validations.json"

# Global variable to cache the config
_circle_config_json_content = None

def load_circle_config():
    """Loads the CIRCLE validation configuration from the JSON file."""
    global _circle_config_json_content
    if _circle_config_json_content is None:
        try:
            print(f"Attempting to load CIRCLE config from: {CONFIG_PATH}")
            _circle_config_json_content = CONFIG_PATH.read_text(encoding="utf-8")
            json.loads(_circle_config_json_content) # Validate if it's valid JSON
            print("CIRCLE config loaded and parsed successfully.")
        except FileNotFoundError:
            print(f"ERROR: CIRCLE configuration file not found at {CONFIG_PATH}")
            _circle_config_json_content = "{}" # Use empty JSON if file not found
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse CIRCLE configuration file {CONFIG_PATH}: {e}")
            _circle_config_json_content = "{}" # Use empty JSON if parsing failed
        except Exception as e:
            print(f"An unexpected error occurred while loading CIRCLE config: {e}")
            _circle_config_json_content = "{}"
    return _circle_config_json_content

# Placeholder lookup functions, similar to test_validations.py
# These need to be implemented based on actual data sources (e.g., champs/ CSVs or a database)
def version_lookup(c0_value):
    """Simulates a version lookup for C0."""
    # In a real application, this might query a database or a configuration file.
    print(f"Performing version lookup for C0 value: {c0_value}")
    # For now, just return a simple dict if value exists, mimicking test_validations
    if c0_value:
        return {"value": c0_value, "description": f"Version object for {c0_value}"}
    return None

def allowed_values_lookup(code, version):
    """Simulates a lookup of allowed values, potentially from 'champs/' CSVs."""
    # This is a critical function that would interact with your champs CSVs.
    # The structure of fake_db should mirror how your CSV data is organized.
    print(f"Performing allowed values lookup for code: {code}, version: {version}")
    fake_db = {
        "C0": ["11", "12"], # Example: Allowed versions
        "C1": ["A0", "B0"], # Example: Allowed document types
        "C10": ["PRODUCT_A", "PRODUCT_B", "BORDEAUX_SUPERIEUR_2022"], # Example product codes
        "C11": ["2020", "2021", "2022", "2023"], # Example vintages
        "C40": [], # No specific list, might be validated by type (e.g., integer)
        "C41": ["75CL", "150CL", "37.5CL"] # Example packaging
        # Add more codes and their allowed values as needed for testing
    }
    # This logic is simplistic. A real implementation would load CSVs from 'champs/'
    # and filter based on 'code' and potentially 'version'.
    return fake_db.get(code, [])


def generate_cle(data: dict) -> str:
    """
    Generates a unique order key (CLE).
    Current implementation: A simple UUID based on a hash of some data.
    This should be refined based on the specific requirements for CLE generation,
    which might involve specific fields from the 'data' (e.g. C0, C1, C10).
    """
    # Using a few common fields that might contribute to uniqueness, if they exist.
    # This is a placeholder and should be defined by business logic.
    key_fields = [str(data.get(f)) for f in ["C0", "C1", "C10", "C11"] if data.get(f)]
    if not key_fields:
        # If no key fields are present, use a random UUID to ensure some uniqueness.
        # This might happen if an order is truly blank initially.
        return str(uuid.uuid4())

    # Create a stable string representation
    key_string = "-".join(sorted(key_fields))
    # Hash the string to get a consistent CLE
    # Using SHA256 and then truncating for a manageable length, or use UUID5.
    # uuid.uuid5(uuid.NAMESPACE_DNS, key_string) could also be an option.
    hasher = hashlib.sha256(key_string.encode('utf-8'))
    # Taking a prefix of the hash for the CLE.
    # This length can be adjusted. Consider potential for collisions if too short.
    return f"CLE-{hasher.hexdigest()[:16].upper()}"


def create_new_order(initial_order_data: dict, creator_id: str, broker_id: str):
    """
    Creates a new order after validation.
    Args:
        initial_order_data: Dict containing the initial CIRCLE fields.
        creator_id: Identifier of the user/system creating the order.
        broker_id: Identifier of the broker this order is associated with.
    Returns:
        The CLE of the created order, or None if creation failed.
    """
    config_json_content = load_circle_config()
    validator = CircleValidatorService(
        circle_values=initial_order_data,
        config_json=config_json_content,
        version_lookup=version_lookup,
        allowed_values_lookup=allowed_values_lookup
    )
    errors = validator.validate()

    if errors:
        print(f"Validation errors: {errors}")
        # Consider returning errors structured for UI display
        return None # Indicate failure

    cle = generate_cle(initial_order_data) # generate_cle should ideally be called *after* validation
                                          # if CLE depends on validated fields.
                                          # Or, if CLE is based on raw input, its current position is fine.

    # Store in database
    # Initial holder is the broker, status can be 'draft' or 'new_draft'
    created_cle = database.create_order(
        cle=cle,
        initial_data=initial_order_data,
        creator=creator_id,
        holder=broker_id, # Order starts with the broker
        status="new_draft"
    )
    if created_cle:
        print(f"Order {created_cle} created successfully by {creator_id} for broker {broker_id}.")
        return created_cle
    else:
        print(f"Failed to create order with generated CLE {cle} in database.")
        return None

def get_order_details(cle: str):
    """Retrieves full details of an order."""
    return database.get_order_by_cle(cle)

def update_order_details(cle: str, new_order_data: dict, modifier_id: str):
    """
    Updates the details of an existing order after validation.
    Args:
        cle: The CLE of the order to update.
        new_order_data: Dict containing the new CIRCLE fields.
        modifier_id: Identifier of the user/system modifying the order.
    Returns:
        True if update was successful, False otherwise.
    """
    validator = CircleValidatorService(new_order_data, config_json_path="config/circle_validations.json")
    errors = validator.validate()

    if errors:
        print(f"Validation errors on update: {errors}")
        return False

    config_json_content = load_circle_config()
    validator = CircleValidatorService(
        circle_values=new_order_data,
        config_json=config_json_content,
        version_lookup=version_lookup,
        allowed_values_lookup=allowed_values_lookup
    )
    errors = validator.validate()

    if errors:
        print(f"Validation errors on update: {errors}")
        return False # Indicate failure

    if database.update_order_data(cle, new_order_data, modifier_id):
        print(f"Order {cle} data updated by {modifier_id}.")
        return True
    else:
        print(f"Failed to update order {cle} data in database.")
        return False

def transition_order_status(cle: str, new_status: str, new_holder_id: str, modifier_id: str):
    """
    Transitions an order to a new status and assigns it to a new holder.
    (No validation here as typically status transitions don't change the core data,
     but this could be added if certain data states are required for status changes).
    """
    # Potentially, before changing status, one might want to re-validate the data
    # or check if the current data state allows such a transition.
    # For now, we directly update status.

    order = database.get_order_by_cle(cle)
    if not order:
        print(f"Order {cle} not found for status transition.")
        return False

    # Optional: Validate data before status transition if needed
    # validator = CircleValidatorService(order['circle_data'], config_json_path="config/circle_validations.json")
    # errors = validator.validate()
    # if errors:
    #     print(f"Order {cle} is not valid for status transition. Errors: {errors}")
    #     return False

    if database.update_order_status(cle, new_status, new_holder_id, modifier_id):
        print(f"Order {cle} status transitioned to '{new_status}' for holder '{new_holder_id}' by {modifier_id}.")
        return True
    else:
        print(f"Failed to update status for order {cle} in database.")
        return False

def get_orders_for_actor(actor_id: str, status: str = None):
    """Retrieves orders for a specific actor, optionally filtered by status."""
    return database.get_orders_for_holder(actor_id, status_filter=status)


if __name__ == '__main__':
    # This requires database.py to be in the same directory or Python path configured.
    # For direct execution, ensure src/ is in PYTHONPATH or run as a module from parent dir.
    # Example: python -m src.order_management (after ensuring circle_validator is findable)

    # Initialize DB first (if not already done)
    database.initialize_database()
    print("Order Management System - Basic Test with Real Validator (if config loads)")

    # Load config at the start of the test
    load_circle_config()
    print(f"Current config content for test: '{_circle_config_json_content[:100]}...'") # Print start of config

    # Sample data for a new order
    sample_order_data_1 = {
        "C0": "11", # Version
        "C1": "A0", # Type of document
        "C10": "BORDEAUX_SUPERIEUR_2022", # Product Code
        "C11": "2022", # Vintage
        "C40": "1000"  # Quantity
    }
    creator = "user_broker_alice"
    broker = "broker_prime_wines"

    # 1. Create a new order
    print("\n1. Attempting to create a new order...")
    new_cle = create_new_order(sample_order_data_1, creator, broker)
    if new_cle:
        print(f"SUCCESS: New order created with CLE: {new_cle}")
    else:
        print(f"FAILURE: Could not create new order.")
        # exit() # Stop if creation fails for a clean test run

    # 2. Retrieve the order
    if new_cle:
        print(f"\n2. Retrieving order {new_cle}...")
        retrieved_order = get_order_details(new_cle)
        if retrieved_order:
            print(f"SUCCESS: Retrieved order: {retrieved_order}")
            assert retrieved_order["circle_data"]["C10"] == "BORDEAUX_SUPERIEUR_2022"
            assert retrieved_order["current_holder"] == broker
            assert retrieved_order["status"] == "new_draft"
        else:
            print(f"FAILURE: Could not retrieve order {new_cle}.")

    # 3. Update the order details
    if new_cle:
        print(f"\n3. Updating order {new_cle}...")
        updated_order_data = sample_order_data_1.copy()
        updated_order_data["C40"] = "1200" # Change quantity
        updated_order_data["C41"] = "75CL" # Add packaging

        modifier = "user_broker_alice"
        if update_order_details(new_cle, updated_order_data, modifier):
            print(f"SUCCESS: Order {new_cle} updated.")
            updated_retrieved_order = get_order_details(new_cle)
            assert updated_retrieved_order["circle_data"]["C40"] == "1200"
            assert updated_retrieved_order["circle_data"]["C41"] == "75CL"
        else:
            print(f"FAILURE: Could not update order {new_cle}.")

    # 4. Transition the order status (e.g., Broker sends to Castle)
    if new_cle:
        print(f"\n4. Transitioning status for order {new_cle}...")
        new_status = "pending_castle_review"
        new_holder = "castle_chateau_x"
        transition_modifier = "user_broker_alice"
        if transition_order_status(new_cle, new_status, new_holder, transition_modifier):
            print(f"SUCCESS: Order {new_cle} transitioned to '{new_status}' for '{new_holder}'.")
            status_updated_order = get_order_details(new_cle)
            assert status_updated_order["status"] == new_status
            assert status_updated_order["current_holder"] == new_holder
        else:
            print(f"FAILURE: Could not transition status for order {new_cle}.")

    # 5. Get orders for an actor
    print(f"\n5. Getting orders for holder '{new_holder}'...")
    actor_orders = get_orders_for_actor(new_holder)
    if actor_orders:
        print(f"SUCCESS: Found {len(actor_orders)} order(s) for {new_holder}.")
        assert any(order["cle"] == new_cle for order in actor_orders)
    else:
        print(f"INFO: No orders found for {new_holder} (or test setup issue).")

    # Test with data that might fail real validation if config is loaded and specific
    # For now, this test relies on the mock lookups and the actual structure of circle_validations.json
    print("\n6. Attempting to create an order that might fail validation (depends on actual config)...")
    # This data is valid according to the mock lookups for C0, C10, C11
    # but might fail other rules in a real config (e.g. dependency, format)
    potentially_problematic_data = {
        "C0": "11", # Version - present in mock allowed_values
        "C10": "MY_NEW_PRODUCT", # Product Code - not in mock allowed_values, so InDatabaseValidation might fail if used
        "C11": "2024", # Vintage - not in mock allowed_values
        "C_UNKNOWN": "some_value" # An unknown field, validator should ignore or flag based on config
    }
    # If circle_validations.json is empty, this will use "{}" and likely pass if no rules are defined.
    # If it's populated, this will use the real rules.

    print(f"Test Data for validation: {potentially_problematic_data}")

    # We need to ensure allowed_values_lookup provides values for C0 and C10 if they are required by config
    # For this test, let's assume C0 and C10 are mandatory and C10 needs to be in the "database"
    # The current allowed_values_lookup is a mock.
    # If the actual config expects C10 to be validated by InDatabaseValidation, it will fail
    # unless "MY_NEW_PRODUCT" is added to allowed_values_lookup for C10.

    failed_cle = create_new_order(potentially_problematic_data, creator, broker)
    if not failed_cle:
        print("Order creation failed validation, as expected or due to config issues.")
    else:
        print(f"Order created with CLE: {failed_cle}. This might be unexpected if config is strict.")
        # To properly test failure, we'd need to know specific rules from circle_validations.json
        # and ensure our mock allowed_values_lookup reflects a state that causes a rule to fail.
        # For example, if C1 requires "A0", and we provide "Z9".

    print("\nOrder Management System - Basic Test Completed.")
