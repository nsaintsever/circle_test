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
        # À adapter selon l’intégration. Ici, retour simulé attendu.
        return None

    def default_error_message(self, code=None):
        return f"Erreur product_validation sur {code or self.code}."
