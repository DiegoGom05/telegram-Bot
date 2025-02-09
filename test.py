import os

file_path = os.path.abspath("template.html")

print(f"Ruta absoluta: {file_path}")
print(f"Existe: {os.path.exists(file_path)}")