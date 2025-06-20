from .base_validation import BaseValidation

class DependencyValidation(BaseValidation):
    def validate(self):
        source_code = self.rule.get("source_code")
        source_value = self.rule.get("source_value")
        target_value = self.rule.get("target_value")

        src_values = self.circle_values.get(source_code, [])
        src_values = src_values if isinstance(src_values, list) else [src_values]
        tgt_values = self.value if isinstance(self.value, list) else [self.value]

        if source_value in src_values and target_value not in tgt_values:
            return f"Si {source_code} vaut '{source_value}', alors {self.code} doit être '{target_value}' (valeur reçue : '{self.value}')."
        return None

    def default_error_message(self, code=None):
        return f"Erreur de dependency sur {code or self.code}."
