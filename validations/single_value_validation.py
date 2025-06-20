from .base_validation import BaseValidation

class SingleValueValidation(BaseValidation):
    def validate(self):
        if self.casket_mode():
            return None
        if isinstance(self.value, list) and len(self.value) != 1:
            return self.default_error_message()
        return None

    def default_error_message(self, code=None):
        return f"Le champ {code or self.code} doit contenir une seule valeur."
