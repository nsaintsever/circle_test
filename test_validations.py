import json
from pathlib import Path
from circle_validator import CircleValidatorService

# Exemple de données circle_values à valider
circle_values = {
    "C0": "11",
    "C1": "A0",
    "C2": "6",
    "C10": "1111A0",
    "C11": "2026",
    "C21": ["00", "A2"],
    "C23": ["120"],
    "C26": "00",
    "C27": "A3",
    "C38": ["A2", "A1"],
    "C50": ["00", "A2"],
    "C53F": "https://example.com",
    "C78": ["A6", "A9", "B1", "B3"],
    "C79": [["A0", "6", "A1"]],
    "C80": [
        "A5", "6", "A1", "A0", ["A2", "B0"], "A6", "A2", ["A0", "A5", "B1"], "A1", "A1"
    ]
}

# Chemin vers le fichier JSON de configuration
config_path = Path(__file__).parent / "config" / "circle_validations.json"
config_json = config_path.read_text(encoding="utf-8")

# Simule une lookup "version" pour C0 (à adapter selon ton appli)
def version_lookup(c0_value):
    # Ici on retourne simplement la valeur comme objet pour test
    return {"value": c0_value}

# Simule une lookup de valeurs autorisées en base
def allowed_values_lookup(code, version):
    # En vrai, ça dépendra d'une base de données ou d'un fichier
    fake_db = {
        "C0": ["11"],
        "C1": ["A0"],
        "C2": ["6"],
        "C10": ["1111A0"],
        "C11": ["2020", "2021", "2022", "2023", "2024", "2025", "2026"],
        "C21": ["00", "A2"],
        "C26": ["00"],
        "C27": ["A3", "00"],
        "C38": ["A1", "A2"],
        "C50": ["00", "A2"],
        "C53F": ["https://example.com"],
        # Ajoute les codes nécessaires à ton jeu de test
    }
    return fake_db.get(code, [])

# Initialise et exécute le validateur
validator = CircleValidatorService(
    circle_values,
    config_json,
    version_lookup=version_lookup,
    allowed_values_lookup=allowed_values_lookup
)

errors = validator.validate()

# Affiche le résultat
if not errors:
    print("✅ Validation OK")
else:
    print("❌ Erreurs de validation :")
    for code, msgs in errors.items():
        for msg in msgs:
            print(f"{code}: {msg}")
