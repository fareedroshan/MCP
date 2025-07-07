# Security Manager Module
import os
from cryptography.fernet import Fernet # For potential credential encryption

# For simplicity, this manager will initially focus on retrieving credentials.
# A real SecurityManager would handle key management, RBAC, LLM safety filters, etc.

class SecurityManager:
    def __init__(self, credential_store_path=None, encryption_key=None):
        """
        Initializes the SecurityManager.
        :param credential_store_path: Path to a file or system for storing credentials (e.g., YAML, Vault).
        :param encryption_key: Key for encrypting/decrypting credentials (if stored locally).
        """
        self.credential_store_path = credential_store_path
        self.credentials = {} # In-memory cache of decrypted credentials

        # Basic encryption setup (example, consider more robust solutions like HashiCorp Vault)
        # If no key is provided, generate one. In a real app, this key must be securely managed.
        self.key = encryption_key or os.getenv("AI_AGENT_ENCRYPTION_KEY") or Fernet.generate_key().decode()
        if not os.getenv("AI_AGENT_ENCRYPTION_KEY") and not encryption_key:
            print(f"Warning: New encryption key generated: {self.key}. Store this key securely for persistent encrypted credentials.")
        self.cipher_suite = Fernet(self.key.encode())

        if self.credential_store_path:
            self._load_credentials()

    def _load_credentials(self):
        """
        Loads and decrypts credentials from the store.
        Placeholder: Assumes a simple encrypted JSON file for now.
        """
        # This is a very basic example. Use a proper secrets management tool in production.
        try:
            if os.path.exists(self.credential_store_path):
                with open(self.credential_store_path, 'rb') as f:
                    encrypted_data = f.read()
                decrypted_data = self.cipher_suite.decrypt(encrypted_data)
                import json
                self.credentials = json.loads(decrypted_data.decode())
                print(f"Credentials loaded from {self.credential_store_path}")
            else:
                print(f"Credential store {self.credential_store_path} not found. Initializing empty store.")
                self.credentials = {} # e.g., {"device_label": {"username": "user", "password": "encrypted_pass"}}
        except Exception as e:
            print(f"Error loading credentials: {e}. Initializing empty credential store.")
            self.credentials = {}


    def _save_credentials(self):
        """
        Encrypts and saves credentials to the store.
        """
        if not self.credential_store_path:
            print("No credential store path configured. Cannot save credentials.")
            return
        try:
            import json
            data_to_encrypt = json.dumps(self.credentials).encode()
            encrypted_data = self.cipher_suite.encrypt(data_to_encrypt)
            with open(self.credential_store_path, 'wb') as f:
                f.write(encrypted_data)
            print(f"Credentials saved to {self.credential_store_path}")
        except Exception as e:
            print(f"Error saving credentials: {e}")


    def get_device_credentials(self, device_identifier):
        """
        Retrieves credentials for a given device.
        :param device_identifier: A unique name or IP for the device.
        :return: dict with 'username', 'password', or None if not found.
        """
        creds = self.credentials.get(device_identifier)
        if creds and "password_encrypted" in creds: # Assuming password is the encrypted part
            try:
                # This part is simplified. In a real scenario, you'd decrypt only when needed
                # and not store decrypted passwords long-term in memory unless necessary.
                # For this example, we assume they are already "decrypted" at load time or managed externally.
                # Let's refine to decrypt on demand.
                # For now, if password_encrypted exists, it means it's stored encrypted.
                # The actual DeviceConnector would need the decrypted password.
                # This function should return the decrypted password.
                # This example is NOT decrypting here, it assumes the _load_credentials handled it.
                # This needs a more robust design for actual encryption/decryption per credential.
                # For now, let's assume 'password' field holds the actual password for DeviceConnector
                # and 'password_encrypted' is just a marker or where an encrypted one *would* be.
                # A better model: self.credentials stores raw forms, and this method decrypts.
                # Simplified: if 'password' field exists, use it.
                if 'password' in creds:
                    return creds
                else: # Placeholder for actual decryption logic if passwords were individually encrypted
                    print(f"Credentials for {device_identifier} found but missing 'password' field.")
                    return None
            except Exception as e:
                print(f"Error processing credentials for {device_identifier}: {e}")
                return None
        elif creds: # If no 'password_encrypted' field, assume it's already in usable form or no password needed
            return creds

        print(f"No credentials found for device: {device_identifier}")
        print("Please ensure credentials are set using set_device_credentials or environment variables.")
        # Fallback to environment variables (example pattern)
        env_user = os.getenv(f"{device_identifier.upper()}_USERNAME")
        env_pass = os.getenv(f"{device_identifier.upper()}_PASSWORD")
        if env_user and env_pass:
            print(f"Using credentials from environment variables for {device_identifier}")
            return {"username": env_user, "password": env_pass}

        return None

    def set_device_credentials(self, device_identifier, username, password, save=True):
        """
        Sets or updates credentials for a device.
        For this example, password is stored as-is in the in-memory dict.
        If saving, it would be encrypted.
        """
        # In a real system, the password would be encrypted before storing, even in memory if long-lived.
        # For this example, we'll store it directly in self.credentials for simplicity,
        # and the _save_credentials method handles encryption to disk.
        self.credentials[device_identifier] = {
            "username": username,
            "password": password # Storing plain for now, encryption happens on save
        }
        print(f"Credentials set for {device_identifier}.")
        if save:
            self._save_credentials() # Encrypts the whole credential store and saves

    # Placeholder for LLM safety filters
    def filter_llm_query(self, query):
        """Apply safety filters to an LLM query."""
        # e.g., check for prompts asking for sensitive info, policy violations
        print(f"Filtering LLM query (placeholder): {query}")
        return query # No filtering implemented yet

    def filter_llm_response(self, response_commands):
        """Apply safety filters to commands from LLM."""
        # e.g., ensure commands don't violate security policies, double-check against destructive patterns
        print(f"Filtering LLM response commands (placeholder): {response_commands}")
        # This could also integrate with CommandValidator for an additional check
        return response_commands # No filtering implemented yet

if __name__ == '__main__':
    print("SecurityManager module placeholder execution.")
    # Example:
    # Use a temporary file for this example. In production, use a secure, persistent path.
    temp_cred_file = "temp_creds.enc"
    # Generate a new key for this test run, or use one from env if you set it for testing.
    # test_key = Fernet.generate_key().decode()
    # print(f"Using temporary encryption key for test: {test_key}")

    # manager = SecurityManager(credential_store_path=temp_cred_file, encryption_key=test_key)
    manager = SecurityManager(credential_store_path=temp_cred_file)


    # Set credentials for a device
    manager.set_device_credentials("my_linux_server", "testuser", "testpass123")
    manager.set_device_credentials("my_cisco_router", "cisco_admin", "cisco_pass", save=True) # Save after this one

    # Retrieve credentials
    creds_server = manager.get_device_credentials("my_linux_server")
    if creds_server:
        print(f"Retrieved for my_linux_server: Username - {creds_server['username']}") # Don't print password!
    else:
        print("Failed to retrieve creds for my_linux_server")

    creds_router = manager.get_device_credentials("my_cisco_router")
    if creds_router:
        print(f"Retrieved for my_cisco_router: Username - {creds_router['username']}")
    else:
        print("Failed to retrieve creds for my_cisco_router")

    creds_unknown = manager.get_device_credentials("unknown_device")
    if not creds_unknown:
        print("Correctly failed to retrieve creds for unknown_device")

    # Test loading from the saved file (by creating a new manager instance)
    print("\nTesting credential loading from file...")
    # manager_loaded = SecurityManager(credential_store_path=temp_cred_file, encryption_key=test_key)
    manager_loaded = SecurityManager(credential_store_path=temp_cred_file, encryption_key=manager.key) # Use the same key

    loaded_creds_router = manager_loaded.get_device_credentials("my_cisco_router")
    if loaded_creds_router and loaded_creds_router['username'] == "cisco_admin":
        print(f"Successfully loaded and decrypted credentials for my_cisco_router: User {loaded_creds_router['username']}")
    else:
        print(f"Failed to load or verify credentials for my_cisco_router from file. Got: {loaded_creds_router}")

    # Clean up the temporary credential file
    if os.path.exists(temp_cred_file):
        os.remove(temp_cred_file)
        print(f"\nCleaned up {temp_cred_file}")

    # Example for env var fallback
    # To test this, run:
    # MY_ENV_DEVICE_USERNAME=env_user MY_ENV_DEVICE_PASSWORD=env_pass python your_script.py
    # os.environ["MY_ENV_DEVICE_USERNAME"] = "env_user_test" # Simulate env var
    # os.environ["MY_ENV_DEVICE_PASSWORD"] = "env_pass_test"
    # creds_env = manager.get_device_credentials("my_env_device")
    # if creds_env and creds_env["username"] == "env_user_test":
    #     print(f"Successfully retrieved credentials from env vars for my_env_device.")
    # else:
    #     print(f"Failed to retrieve credentials from env vars for my_env_device. Got: {creds_env}")
    # if "MY_ENV_DEVICE_USERNAME" in os.environ: del os.environ["MY_ENV_DEVICE_USERNAME"]
    # if "MY_ENV_DEVICE_PASSWORD" in os.environ: del os.environ["MY_ENV_DEVICE_PASSWORD"]
