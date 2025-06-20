from .base_validation import BaseValidation
from datetime import datetime

class ProductValidation(BaseValidation):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = self.find_product()

    def validate(self):
        vintage = self.circle_values.get("C11")
        if not vintage:
            return None
        if not self.product:
            return None

        start = self.product.starting_vintage.value
        end = self.product.late_vintage.value
        excluded = [v.value for v in self.product.excluded_vintages]

        if vintage in excluded:
            return self._fail(vintage)
        if start != "ND" and vintage < start:
            return self._fail(vintage)
        if end != "ND" and vintage > end:
            return self._fail(vintage)
        if vintage > str(datetime.today().year):
            return self._fail(vintage)
        return None

    def _fail(self, vintage):
        return f"Le millésime {vintage} n'existe pas pour le produit {self.product.value}."

    def find_product(self):
        # Use the utility function from streamlit_utils to find product details
        from streamlit_utils import find_product_details_by_circle_code

        product_code_value = self.circle_values.get("C10")
        if not product_code_value:
            return None # Or raise an error if C10 is mandatory for this validation to run

        # find_product_details_by_circle_code returns a pandas Series or None
        product_series = find_product_details_by_circle_code(product_code_value)

        if product_series is not None:
            # The validator expects an object with attributes like .value, .starting_vintage, etc.
            # We can create a simple class or a Pydantic model on the fly if needed,
            # or adapt the validator to use Series directly.
            # For now, let's assume the Series itself (or its .to_dict()) can be used
            # if the validator accesses it like product['StartingVintage'] or product.get('StartingVintage').
            # The original code seemed to expect objects with direct attribute access (e.g. product.starting_vintage.value)
            # This might require a small wrapper or adjustment.
            # Let's try returning the series and see if test_validations needs adjustment or if this works.
            # The original placeholder `return {"value": c0_value}` in tests was simple.
            # A pandas Series can be accessed with series['ColumnName']
            # For compatibility with `product.starting_vintage.value`, we might need to wrap it.
            # For now, returning the series directly. This will likely require adjustment
            # in how `start`, `end`, and `excluded` are accessed below if they expect nested objects.

            # Simplification: Let's assume the ProductValidation will be adapted to directly use
            # the pandas Series, or we create a simple object-like structure.
            # For direct compatibility with `product.starting_vintage.value`, etc.,
            # it's better if `find_product_details_by_circle_code` returns an object or dict
            # that the validation logic can easily use.
            # The current ProductValidation expects something like:
            # self.product.starting_vintage.value -> series['StartingVintage']
            # self.product.late_vintage.value -> series['LateVintage']
            # self.product.excluded_vintages (list of objects with .value) -> series['ExcludedVintage'].split(',')
            # self.product.value -> series['CircleCode'] (or whatever represents the product's own code)

            # Let's make it return a dictionary for easier access in the validator.
            return product_series # The validator will need to handle this Series
        return None

    def validate(self):
        vintage_str = self.circle_values.get("C11")
        if not vintage_str: # Vintage might not be provided
            return None

        # Ensure product is loaded. If not, can't validate vintage against it.
        if not self.product: # self.product is set in __init__
            # This could be an error if C10 was provided but not found,
            # or None if C10 wasn't provided (though find_product handles that).
            # If C10 is present but product not found by find_product_details_by_circle_code,
            # that's an issue for InDatabaseValidation of C10, not this rule.
            # So, if self.product is None here, it means C10 was likely not found or not provided.
            return None

        # Accessing pandas Series elements:
        # The product Series has columns like 'StartingVintage', 'LateVintage', 'ExcludedVintage', 'CircleCode'
        start_vintage_val = self.product.get('StartingVintage')
        late_vintage_val = self.product.get('LateVintage')
        excluded_vintages_str = self.product.get('ExcludedVintage', "")
        product_circle_code = self.product.get('CircleCode')

        # Convert vintage to string for comparison, as CSVs are read as strings
        current_vintage_val = str(vintage_str)

        if excluded_vintages_str and excluded_vintages_str != "ND":
            excluded_list = [v.strip() for v in excluded_vintages_str.split(',')]
            if current_vintage_val in excluded_list:
                return self._fail(current_vintage_val, product_circle_code)

        if start_vintage_val != "ND" and current_vintage_val < start_vintage_val:
            return self._fail(current_vintage_val, product_circle_code)

        if late_vintage_val != "ND" and current_vintage_val > late_vintage_val:
            return self._fail(current_vintage_val, product_circle_code)

        # Check if vintage is in the future
        try:
            if int(current_vintage_val) > datetime.today().year:
                 return self._fail(current_vintage_val, product_circle_code, message_suffix=" (cannot be in the future)")
        except ValueError:
            # If vintage_str is not a valid year like "ND" or "SA" (Sans Année)
            # This specific check might need refinement based on C11_vintages.csv actual values.
            # For now, if it's not "ND" and not convertible to int, it's an issue for C11's own validation.
            pass


        return None

    def _fail(self, vintage_val, product_val, message_suffix=""):
        return f"Le millésime {vintage_val} n'est pas valide pour le produit {product_val}{message_suffix}."

    def default_error_message(self, code=None):
        return f"Erreur product_validation sur {code or self.code}."
