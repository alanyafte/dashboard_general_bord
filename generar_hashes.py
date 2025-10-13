# generar_hashes.py (ejecutar una vez y luego borrar este archivo)
import hashlib

contraseñas_originales = {
    "produccion123": "🏭 Producción",
    "clima456": "👥 Clima Laboral", 
    "cliente789": "😊 Satisfacción Cliente",
}

print("=== COPIA ESTOS HASHES ===")
for contraseña, modulo in contraseñas_originales.items():
    hash_result = hashlib.sha256(contraseña.encode()).hexdigest()
    print(f'"{modulo}": "{hash_result}",')
