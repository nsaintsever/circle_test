import re
from .base_validation import BaseValidation

class MatchValueValidation(BaseValidation):
    def validate(self):
        pattern = self.rule.get("pattern", "")
        regex = re.compile(pattern)
        values = self.value if isinstance(self.value, list) else [self.value]
        for val in values:
            if not regex.match(str(val)):
                return f"L'URL de {self.code} doit commencer par 'https://', valeur reçue : '{val}'."
        return None

    def default_error_message(self, code=None):
        return f"Erreur de match_value sur {code or self.code}."
