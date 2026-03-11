import json
from cryptography.fernet import Fernet
import base64
import os

class PasswordManager:
    def __init__(self, key_file="secret.key"):
        """
        Inicializa el administrador de contraseñas.
        key_file: archivo donde se guardará la clave de encriptación
        """
        self.key_file = key_file
        # Carga o genera la clave de encriptación
        self.key = self.load_or_generate_key()
        # Crea el encriptador
        self.cipher = Fernet(self.key)

    def load_or_generate_key(self):
        """Carga la clave existente o genera una nueva si no existe"""
        if os.path.exists(self.key_file):
            # Si existe el archivo, lee la clave
            with open(self.key_file, "rb") as key_file:
                return key_file.read()
        else:
            # Si no existe, genera una nueva clave
            key = Fernet.generate_key()
            # Guarda la clave en el archivo
            with open(self.key_file, "wb") as key_file:
                key_file.write(key)
            return key

    def encrypt_password(self, password):
        """Encripta una contraseña"""
        return self.cipher.encrypt(password.encode()).decode()

    def decrypt_password(self, encrypted_password):
        """Desencripta una contraseña"""
        return self.cipher.decrypt(encrypted_password.encode()).decode()

def encrypt_config_file(input_file="config.json", output_file="config_encrypted.json"):
    """
    Lee el archivo de configuración, encripta las contraseñas y guarda en un nuevo archivo
    """
    # Crear el administrador de contraseñas
    password_manager = PasswordManager()

    # Leer el archivo de configuración
    with open(input_file, "r") as f:
        config = json.load(f)

    # Encriptar las contraseñas
    for system, system_data in config["systems"].items():
        for instance in system_data["instances"]:
            if "password" in instance:
                # Encriptar la contraseña
                encrypted_password = password_manager.encrypt_password(instance["password"])
                print(f'INFO: {system} - {instance["hostname"]} - Password encriptada')
                # Reemplazar la contraseña con la versión encriptada
                instance["encrypted_password"] = encrypted_password
                # Eliminar la contraseña en texto plano
                del instance["password"]

    # Guardar la nueva configuración
    with open(output_file, "w") as f:
        json.dump(config, f, indent=4)

# Ejemplo de uso
if __name__ == "__main__":
    # Encriptar el archivo de configuración
    encrypt_config_file()
    
    # Ejemplo de cómo usar el PasswordManager para desencriptar
    pm = PasswordManager()
    
    # Leer el archivo encriptado
    with open("config_encrypted.json", "r") as f:
        encrypted_config = json.load(f)
    
    # # Mostrar un ejemplo de desencriptación
    # for system, system_data in encrypted_config["systems"].items():
    #     for instance in system_data["instances"]:
    #         if "encrypted_password" in instance:
    #             # Desencriptar la contraseña
    #             original_password = pm.decrypt_password(instance["encrypted_password"])
    #             print(f'INFO: {system} - {instance["hostname"]} - Password encriptada')

