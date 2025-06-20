import json
from validations import VALIDATION_CLASSES

class CircleValidatorService:
    def __init__(self, circle_values, config_json, version_lookup=None, allowed_values_lookup=None):
        self.circle_values = circle_values
        self.config = json.loads(config_json)
        self.errors = {}
        self.version = None
        self.version_lookup = version_lookup or (lambda v: None)
        self.allowed_values_lookup = allowed_values_lookup or (lambda code, version: [])

        self.version = self.version_lookup(circle_values.get("C0"))

    def validate(self):
        for code, settings in self.config.items():
            value = self.circle_values.get(code)
            if value is None:
                continue
            for rule in settings.get("validations", []):
                validation_type = rule.get("type")
                validation_class = VALIDATION_CLASSES.get(validation_type)
                if not validation_class:
                    continue
                validator = validation_class(
                    code=code,
                    value=value,
                    rule=rule,
                    version=self.version,
                    circle_values=self.circle_values,
                    allowed_values_lookup=self.allowed_values_lookup
                )
                error = validator.validate()
                if error:
                    self.errors.setdefault(code, []).append(error)
        return self.errors
