from .base_validation import BaseValidation

class InDatabaseValidation(BaseValidation):
    def validate(self):
        allowed = self.allowed_values()
        values = self.value if isinstance(self.value, list) else [self.value]
        for v in values:
            if v not in allowed:
                return f"La valeur '{v}' de {self.code} n'existe pas en base."
        return None

    def default_error_message(self, code=None):
        return f"Erreur in_database sur {code or self.code}."
