from .base_validation import BaseValidation

class CasketValueValidation(BaseValidation):
    def validate(self):
        if not self.casket_mode():
            return None

        if self.rule.get("match_array_length"):
            expected_length = len(self.circle_values.get("C2", [])) if isinstance(self.circle_values.get("C2"), list) else 1
            actual_length = len(self.value) if isinstance(self.value, list) else 0
            if not isinstance(self.value, list):
                return f"En coffret, {self.code} doit être un tableau de {expected_length} éléments."
            if actual_length != expected_length:
                return f"En coffret, {self.code} doit être un tableau de {expected_length} élément(s) (taille reçue : {actual_length})."
        else:
            allowed = self.rule.get("allowed_values", [])
            values = self.value if isinstance(self.value, list) else [self.value]
            violating = [v for v in values if v not in allowed]
            if violating:
                return f"En coffret, {self.code} doit être égal à {', '.join(allowed)} (valeur reçue : '{', '.join(violating)}')."
        return None

    def default_error_message(self, code=None):
        return f"Erreur de casket_value sur {code or self.code}."
