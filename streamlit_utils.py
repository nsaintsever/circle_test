import pandas as pd
import os
import json
from typing import List, Dict, Any
import requests # To call the FastAPI backend

# --- CSV Data Loading and Access ---
CHAMPS_CSV_DIR = "champs_csv"
_CHAMPS_DATA_CACHE = {} # Cache for loaded CSV data
_PRODUCT_DATA_CACHE = None # Cache for C10_products.csv

def load_champ_csv(champ_code: str) -> pd.DataFrame | None:
    """Loads a specific champ CSV file into a pandas DataFrame."""
    if champ_code in _CHAMPS_DATA_CACHE:
        return _CHAMPS_DATA_CACHE[champ_code]

    filename_pattern = f"{champ_code}_"
    try:
        # Ensure the directory exists
        if not os.path.isdir(CHAMPS_CSV_DIR):
            print(f"Champs CSV directory not found: {CHAMPS_CSV_DIR}")
            # Attempt to use an absolute path if it's a common sandbox issue
            abs_path_dir = os.path.join(os.getcwd(), CHAMPS_CSV_DIR)
            if not os.path.isdir(abs_path_dir):
                 _CHAMPS_DATA_CACHE[champ_code] = None # Cache failure
                 return None
            # If absolute path works, use it for listing files
            effective_csv_dir = abs_path_dir
        else:
            effective_csv_dir = CHAMPS_CSV_DIR

        for f in os.listdir(effective_csv_dir):
            if f.startswith(filename_pattern) and f.endswith(".csv"):
                filepath = os.path.join(effective_csv_dir, f)
                try:
                    df = pd.read_csv(filepath, dtype=str).fillna('') # Read all as string, fill NA with empty
                    _CHAMPS_DATA_CACHE[champ_code] = df
                    return df
                except Exception as e:
                    print(f"Error loading CSV {filepath}: {e}")
                    return None
        print(f"CSV file for champ code {champ_code} not found in {effective_csv_dir}")
        _CHAMPS_DATA_CACHE[champ_code] = None # Cache miss
        return None
    except FileNotFoundError: # This might be redundant if isdir check is done
        print(f"Champs CSV directory not found on initial attempt: {CHAMPS_CSV_DIR}")
        _CHAMPS_DATA_CACHE[champ_code] = None
        return None


def get_allowed_values_for_champ(champ_code: str, version: Any = None) -> List[str]:
    """
    Retrieves the list of allowed 'CircleCode' values for a given champ_code.
    'version' is not used yet but kept for compatibility with CircleValidatorService.
    """
    df = load_champ_csv(champ_code)
    if df is not None and "CircleCode" in df.columns:
        return df["CircleCode"].unique().tolist()
    return []

def get_champ_details(champ_code: str, circle_code_value: str) -> Dict[str, Any] | None:
    """Retrieves all details for a specific CircleCode within a champ."""
    df = load_champ_csv(champ_code)
    if df is not None and "CircleCode" in df.columns:
        row = df[df["CircleCode"] == circle_code_value]
        if not row.empty:
            return row.iloc[0].to_dict()
    return None

# --- Product Data Specific Functions ---
def load_product_data() -> pd.DataFrame | None:
    """Loads C10_products.csv specifically."""
    global _PRODUCT_DATA_CACHE
    if _PRODUCT_DATA_CACHE is not None: # and isinstance(_PRODUCT_DATA_CACHE, pd.DataFrame): # Check if it's already a loaded DataFrame
        return _PRODUCT_DATA_CACHE

    df = load_champ_csv("C10") # C10 is for products
    _PRODUCT_DATA_CACHE = df
    return df

def find_product_details_by_circle_code(product_circle_code: str) -> pd.Series | None:
    """
    Finds product details from C10_products.csv given its CircleCode.
    Returns a pandas Series (representing the row) or None if not found.
    """
    products_df = load_product_data()
    if products_df is None:
        print(f"Product data (C10_products.csv) could not be loaded.")
        return None

    product_row = products_df[products_df["CircleCode"] == product_circle_code]
    if not product_row.empty:
        return product_row.iloc[0]
    print(f"Product with CircleCode {product_circle_code} not found in C10_products.csv.")
    return None


# --- `allowed_values_lookup` for CircleValidatorService ---
def circle_allowed_values_lookup(champ_code: str, version: Any) -> List[str]:
    """
    Lookup function for CircleValidatorService to get allowed values for a champ.
    'version' parameter is present for compatibility but not actively used in this basic CSV lookup.
    """
    return get_allowed_values_for_champ(champ_code, version)


# --- FastAPI Backend Interaction ---
API_BASE_URL = "http://localhost:8000"

def create_new_order_api(order_data: Dict[str, Any], c10_val: str, c11_val: str, sender: str, receiver: str) -> Dict[str, Any] | None:
    payload = {
        "C10": c10_val,
        "C11": c11_val,
        "circle_data": order_data,
        "sender_id": sender,
        "receiver_id": receiver
    }
    try:
        response = requests.post(f"{API_BASE_URL}/order", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error (create_new_order): {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

def get_order_details_api(cle: str) -> Dict[str, Any] | None:
    try:
        response = requests.get(f"{API_BASE_URL}/order/{cle}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error (get_order_details for {cle}): {e}")
        return None

def update_order_api(cle: str, updated_data: Dict[str, Any], sender: str, new_current_actor: str, new_status: str, action_desc: str) -> Dict[str, Any] | None:
    payload = {
        "updated_data": updated_data,
        "sender_id": sender,
        "new_current_actor": new_current_actor,
        "new_status": new_status,
        "action_description": action_desc
    }
    try:
        response = requests.put(f"{API_BASE_URL}/order/{cle}", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error (update_order for {cle}): {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

def get_orders_for_actor_api(actor_name: str) -> List[Dict[str, Any]] | None:
    try:
        response = requests.get(f"{API_BASE_URL}/orders/actor/{actor_name}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API Error (get_orders_for_actor for {actor_name}): {e}")
        return None

if __name__ == '__main__':
    print("Streamlit utils loaded.")
    # Example usage (can be uncommented for direct testing if needed)
    # print("Testing CSV loading for C0 (Versions)...")
    # c0_values = get_allowed_values_for_champ("C0")
    # print(f"Allowed C0 values: {c0_values[:5]}...") # Print first 5
    # if c0_values:
    #     print(f"Details for C0 value '{c0_values[0]}': {get_champ_details('C0', c0_values[0])}")

    # print("\nTesting product data loading (C10)...")
    # product_df = load_product_data()
    # if product_df is not None and not product_df.empty:
    #     example_product_code = product_df["CircleCode"].iloc[0]
    #     print(f"Details for product {example_product_code}:")
    #     print(find_product_details_by_circle_code(example_product_code))
    # else:
    #     print("C10_products.csv could not be loaded or is empty.")

    # print(f"\nTesting allowed_values_lookup for C1 (Cases): {circle_allowed_values_lookup('C1', None)[:5]}...")
    pass
