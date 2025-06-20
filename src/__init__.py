# This file makes Python treat the 'src' directory as a package.
# This helps in organizing imports and allows for relative imports within the package.

# You can also define what gets imported when someone does 'from src import *'
# For example:
# from .database import initialize_database, create_order
# from .order_management import create_new_order, get_order_details

# However, for now, we'll keep it empty and use explicit imports like:
# from src import database
# from src import order_management
# or
# from src.database import ...
# from src.order_management import ...

print("src package initialized.")
