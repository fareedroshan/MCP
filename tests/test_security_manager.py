import unittest
from unittest.mock import patch, mock_open
import os
import json
from cryptography.fernet import Fernet

from src.ai_agent.security.security_manager import SecurityManager

class TestSecurityManager(unittest.TestCase):

    def setUp(self):
        self.test_cred_file = "test_creds.enc"
        self.test_key = Fernet.generate_key().decode()
        # Ensure no real file is left if a test fails
        if os.path.exists(self.test_cred_file):
            os.remove(self.test_cred_file)

    def tearDown(self):
        if os.path.exists(self.test_cred_file):
            os.remove(self.test_cred_file)

    def test_init_generate_key_if_none_provided(self):
        with patch.dict(os.environ, clear=True): # No env var for key
            manager = SecurityManager(self.test_cred_file) # No key argument
            self.assertIsNotNone(manager.key)
            self.assertIsInstance(manager.cipher_suite, Fernet)

    def test_init_use_provided_key(self):
        manager = SecurityManager(self.test_cred_file, encryption_key=self.test_key)
        self.assertEqual(manager.key, self.test_key)

    @patch.dict(os.environ, {"AI_AGENT_ENCRYPTION_KEY": "env_key_string_longer_than_32_bytes_for_fernet"})
    def test_init_use_env_var_key(self):
        # Key from env var must be Fernet-compatible (base64 encoded 32 bytes)
        env_fernet_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"AI_AGENT_ENCRYPTION_KEY": env_fernet_key}):
            manager = SecurityManager(self.test_cred_file)
            self.assertEqual(manager.key, env_fernet_key)

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_load_credentials_success(self, mock_exists, mock_file_open):
        key = Fernet.generate_key()
        cipher = Fernet(key)
        creds_data = {"dev1": {"username": "user1", "password": "pass1"}}
        encrypted_data = cipher.encrypt(json.dumps(creds_data).encode())

        mock_file_open.return_value.read.return_value = encrypted_data

        manager = SecurityManager(self.test_cred_file, encryption_key=key.decode())
        # _load_credentials is called in __init__

        self.assertEqual(manager.credentials, creds_data)
        mock_file_open.assert_called_once_with(self.test_cred_file, 'rb')

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_load_credentials_decryption_error(self, mock_exists, mock_file_open):
        # Simulate corrupted data or wrong key
        mock_file_open.return_value.read.return_value = b"not_really_encrypted_data_garbage_in"

        manager = SecurityManager(self.test_cred_file, encryption_key=self.test_key)
        self.assertEqual(manager.credentials, {}) # Should default to empty on error

    @patch("os.path.exists", return_value=False)
    def test_load_credentials_file_not_found(self, mock_exists):
        manager = SecurityManager(self.test_cred_file, encryption_key=self.test_key)
        self.assertEqual(manager.credentials, {})

    @patch("builtins.open", new_callable=mock_open)
    def test_save_credentials(self, mock_file_open):
        manager = SecurityManager(self.test_cred_file, encryption_key=self.test_key)
        manager.credentials = {"dev2": {"username": "user2", "password": "password2"}}
        manager._save_credentials()

        mock_file_open.assert_called_once_with(self.test_cred_file, 'wb')
        # Check that write was called with encrypted data
        written_data = mock_file_open.return_value.write.call_args[0][0]

        # Decrypt and verify
        cipher = Fernet(self.test_key.encode())
        decrypted_written_data = json.loads(cipher.decrypt(written_data).decode())
        self.assertEqual(decrypted_written_data, manager.credentials)

    def test_set_and_get_device_credentials_no_save(self):
        manager = SecurityManager(encryption_key=self.test_key) # No cred_store_path, so no load/save
        manager.set_device_credentials("dev3", "user3", "pass3", save=False)

        retrieved_creds = manager.get_device_credentials("dev3")
        self.assertIsNotNone(retrieved_creds)
        self.assertEqual(retrieved_creds["username"], "user3")
        self.assertEqual(retrieved_creds["password"], "pass3")

        self.assertIsNone(manager.get_device_credentials("nonexistent_dev"))

    @patch("src.ai_agent.security.security_manager.SecurityManager._save_credentials")
    def test_set_device_credentials_with_save(self, mock_save_creds):
        manager = SecurityManager(self.test_cred_file, encryption_key=self.test_key)
        manager.set_device_credentials("dev4", "user4", "pass4", save=True)
        mock_save_creds.assert_called_once()

    def test_get_device_credentials_fallback_to_env(self):
        manager = SecurityManager(encryption_key=self.test_key)
        device_id = "ENV_DEVICE"
        env_vars = {
            f"{device_id}_USERNAME": "env_user",
            f"{device_id}_PASSWORD": "env_pass"
        }
        with patch.dict(os.environ, env_vars):
            creds = manager.get_device_credentials(device_id)
            self.assertIsNotNone(creds)
            self.assertEqual(creds["username"], "env_user")
            self.assertEqual(creds["password"], "env_pass")

    def test_get_device_credentials_env_fallback_partial_missing(self):
        manager = SecurityManager(encryption_key=self.test_key)
        device_id = "PARTIAL_ENV_DEVICE"
        # Only username is set
        with patch.dict(os.environ, {f"{device_id}_USERNAME": "env_user_partial"}):
            creds = manager.get_device_credentials(device_id)
            self.assertIsNone(creds) # Both username and password must be present from env

    # Test persistence (actual file read/write)
    def test_credential_persistence_to_file(self):
        manager1 = SecurityManager(self.test_cred_file, encryption_key=self.test_key)
        manager1.set_device_credentials("persist_dev", "p_user", "p_pass", save=True)

        # Create a new manager instance to load from the file
        manager2 = SecurityManager(self.test_cred_file, encryption_key=self.test_key)
        retrieved_creds = manager2.get_device_credentials("persist_dev")

        self.assertIsNotNone(retrieved_creds)
        self.assertEqual(retrieved_creds["username"], "p_user")
        self.assertEqual(retrieved_creds["password"], "p_pass")

    def test_filter_llm_query_placeholder(self):
        manager = SecurityManager(encryption_key=self.test_key)
        query = "Test query"
        self.assertEqual(manager.filter_llm_query(query), query) # Placeholder returns as-is

    def test_filter_llm_response_placeholder(self):
        manager = SecurityManager(encryption_key=self.test_key)
        commands = "ls -l"
        self.assertEqual(manager.filter_llm_response(commands), commands) # Placeholder returns as-is

if __name__ == '__main__':
    unittest.main()
