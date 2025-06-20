class BaseValidation:
    def __init__(self, code, value, rule, version, circle_values, allowed_values_lookup):
        self.code = code
        self.value = value
        self.rule = rule
        self.version = version
        self.circle_values = circle_values
        self.allowed_values_lookup = allowed_values_lookup

    def casket_mode(self):
        return self.circle_values.get("C2") == "00"

    def allowed_values(self, code=None):
        code = code or self.code
        return self.allowed_values_lookup(code, self.version)

    def validate(self):
        raise NotImplementedError("Subclasses must implement this method.")

    def default_error_message(self, code=None):
        return f"Erreur de validation sur {code or self.code}."
