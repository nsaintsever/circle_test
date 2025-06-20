from .base_validation import BaseValidation

class DuplicateValueValidation(BaseValidation):
    def validate(self):
        if isinstance(self.value, list) and len(self.value) != len(set(self.value)):
            return f"{self.code} ne doit pas contenir de doublons (valeurs : {', '.join(map(str, self.value))})."
        return None

    def default_error_message(self, code=None):
        return f"Erreur de duplicate_value sur {code or self.code}."
