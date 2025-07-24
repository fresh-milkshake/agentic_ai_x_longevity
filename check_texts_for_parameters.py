import re
from pathlib import Path

params_patterns = [
    # Kd = 10 nM / Kd < 10 nM / Kd > 10 nM
    ("classic", r"(?P<param>Kd|IC50|Ki|C50)\s*[=<>]?\s*(?P<value>\d+\.?\d*)\s*(?P<unit>nM|μM|mM)"),
    # Kd (10 nM)
    ("brackets", r"(?P<param>Kd|IC50|Ki|C50)\s*\(\s*(?P<value>\d+\.?\d*)\s*(?P<unit>nM|μM|mM)\s*\)"),
    # Kd: 10 nM / Kd, 10 nM
    ("colon_or_comma", r"(?P<param>Kd|IC50|Ki|C50)\s*[:|,]\s*(?P<value>\d+\.?\d*)\s*(?P<unit>nM|μM|mM)"),
    # 10 nM
    ("value_only", r"(?P<value>\d+\.?\d*)\s*(?P<unit>nM|μM|mM)")
]

def extract_params(text: str):
    any_found = False
    for name, pattern in params_patterns:
        found = False
        for match in re.finditer(pattern, text):
            found = True
            any_found = True
            print(f"Паттерн '{name}': найден параметр взаимодействия:")
            print(f"  Полное совпадение: {match.group(0)}")
            print(f"  Детали: {match.groupdict()}")
            print(f"  Позиция в тексте: {match.start()} - {match.end()}")
            print("-" * 40)
        if not found:
            print(f"Паттерн '{name}': параметры не найдены.")
    if not any_found:
        print("Параметры взаимодействия не найдены ни одним паттерном.")

if __name__ == "__main__":
    patents_txts = Path("results/raw")
    for txt_file in patents_txts.glob("*.txt"):
        print(f"\nФайл: {txt_file.name}")
        with open(txt_file, "r", encoding="utf-8") as f:
            text = f.read()
        extract_params(text)