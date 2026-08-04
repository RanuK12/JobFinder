#!/usr/bin/env python3
"""
Script para extraer los modelos de la base de datos desde app.py
"""

import re

# Leer el archivo app.py
with open('app.py', 'r') as f:
    content = f.read()

# Expresión regular para encontrar los modelos
model_pattern = r'class (\w+)\(.*?db\.Model.*?\):(.*?)(?=class \w+\(|$|\Z)'
matches = re.findall(model_pattern, content, re.DOTALL)

print("Modelos encontrados:")
for match in matches:
    model_name = match[0]
    model_content = match[1]
    print(f"- {model_name}")
    
    # Extraer las columnas
    columns = re.findall(r'(\w+)\s*=\s*db\.Column\([^)]+\)', model_content)
    print(f"  Columnas: {', '.join(columns)}")
    print()