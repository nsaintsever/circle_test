from .base_validation import BaseValidation

class InDatabaseCombinationValidation(BaseValidation):
    def validate(self):
        if isinstance(self.value, str) and self.value == "00":
            return None

        combination_codes = self.rule.get("combination_codes", [])
        mode = self.rule.get("combinaison_mode", "combined_codes")

        if mode == "combined_codes":
            if not isinstance(self.value, list):
                return f"La valeur de {self.code} doit être un array (mode combined_codes)."
            for combination in self.value:
                if not isinstance(combination, list):
                    return f"Chaque élément de {self.code} doit être un array (mode combined_codes). Reçu: {combination!r}"
                if combination and isinstance(combination[0], list):
                    for sub in combination:
                        err = self.check_ensemble(sub, combination_codes)
                        if err: return err
                else:
                    err = self.check_ensemble(combination, combination_codes)
                    if err: return err

        elif mode == "single_code":
            if not (isinstance(self.value, list) and len(self.value) == len(combination_codes)):
                return f"La valeur de {self.code} doit être un array de taille {len(combination_codes)} (mode single_code). Reçu: {self.value!r}"
            for idx, element in enumerate(self.value):
                current_code = combination_codes[idx]
                values = element if isinstance(element, list) else [element]
                for val in values:
                    if val not in self.allowed_values(current_code):
                        return f"La valeur '{val}' pour le code {current_code} n'existe pas en base."

        else:
            return f"Mode de combinaison inconnu pour {self.code}."

        return None

    def check_ensemble(self, ensemble, codes):
        if not isinstance(ensemble, list) or len(ensemble) != len(codes):
            return f"Un ensemble dans {self.code} doit être un array de taille {len(codes)} (reçu : {ensemble!r})."
        for i, val in enumerate(ensemble):
            code = codes[i]
            if val not in self.allowed_values(code):
                return f"La valeur '{val}' pour le code {code} n'existe pas en base."
        return None

    def default_error_message(self, code=None):
        return f"Erreur in_database_combination sur {code or self.code}."
