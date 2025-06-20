from .base_validation import BaseValidation

class ForbiddenValueValidation(BaseValidation):
    def validate(self):
        forbidden = self.rule.get("forbidden_values", [])
        values = self.value if isinstance(self.value, list) else [self.value]
        violating = [v for v in values if v in forbidden]
        if violating:
            return f"La valeur '{', '.join(violating)}' présente pour {self.code} n'est pas autorisée."
        return None

    def default_error_message(self, code=None):
        return f"Erreur de forbidden_value sur {code or self.code}."
