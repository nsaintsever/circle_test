import re
from .base_validation import BaseValidation

class ExcludedCombinationsValidation(BaseValidation):
    def validate(self):
        combinations = self.rule.get("excluded_combinations", [])
        values = self.value if isinstance(self.value, list) else [self.value]

        for combination in combinations:
            matched = self.get_matched_values(combination, values)
            if matched:
                return f"La combinaison {self.format_matched_values(matched)} n'est pas autorisée pour le code {self.code}."
        return None

    def get_matched_values(self, combination, values):
        matched = []
        available_values = values[:]

        for pattern in combination:
            for i, val in enumerate(available_values):
                if self.matches(pattern, val):
                    matched.append(val)
                    del available_values[i]
                    break
            else:
                return None
        return matched

    def matches(self, pattern, value):
        if isinstance(pattern, str) and pattern.startswith("/") and pattern.endswith("/"):
            regex = re.compile(pattern[1:-1])
            return regex.match(str(value)) is not None
        return pattern == value

    def format_matched_values(self, matched):
        return " + ".join(str(m) for m in matched)

    def default_error_message(self, code=None):
        return f"Erreur d'excluded_combinations sur {code or self.code}."
