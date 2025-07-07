import unittest
from unittest.mock import patch, MagicMock

from src.ai_agent.connectors.device_connector import DeviceConnector

class TestDeviceConnector(unittest.TestCase):

    @patch('paramiko.SSHClient')
    def test_connect_success(self, mock_ssh_client_constructor):
        mock_ssh_instance = MagicMock()
        mock_ssh_client_constructor.return_value = mock_ssh_instance

        connector = DeviceConnector("testhost", "testuser", "testpass")
        result = connector.connect()

        self.assertTrue(result)
        mock_ssh_instance.set_missing_host_key_policy.assert_called_once_with(unittest.mock.ANY) # paramiko.AutoAddPolicy
        mock_ssh_instance.connect.assert_called_once_with("testhost", username="testuser", password="testpass")
        self.assertEqual(connector.client, mock_ssh_instance)

    @patch('paramiko.SSHClient')
    def test_connect_failure(self, mock_ssh_client_constructor):
        mock_ssh_instance = MagicMock()
        mock_ssh_instance.connect.side_effect = Exception("Connection failed")
        mock_ssh_client_constructor.return_value = mock_ssh_instance

        connector = DeviceConnector("testhost", "testuser", "testpass")
        result = connector.connect()

        self.assertFalse(result)
        self.assertIsNone(connector.client.close.call_count == 0) # Client should not be closed if connect fails this way

    def test_disconnect_no_client(self):
        connector = DeviceConnector("testhost", "testuser", "testpass")
        connector.disconnect() # Should not raise error

    @patch('paramiko.SSHClient')
    def test_disconnect_with_client(self, mock_ssh_client_constructor):
        mock_ssh_instance = MagicMock()
        mock_ssh_client_constructor.return_value = mock_ssh_instance

        connector = DeviceConnector("testhost", "testuser", "testpass")
        connector.connect() # Sets up connector.client
        connector.disconnect()

        mock_ssh_instance.close.assert_called_once()

    def test_execute_command_not_connected(self):
        connector = DeviceConnector("testhost", "testuser", "testpass")
        output = connector.execute_command("ls")
        self.assertIsNone(output) # Or check for specific error message if behavior changes

    @patch('paramiko.SSHClient')
    def test_execute_command_success(self, mock_ssh_client_constructor):
        mock_ssh_instance = MagicMock()
        mock_stdin, mock_stdout, mock_stderr = MagicMock(), MagicMock(), MagicMock()
        mock_stdout.read.return_value = b"some output"
        mock_stderr.read.return_value = b""
        mock_ssh_instance.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        mock_ssh_client_constructor.return_value = mock_ssh_instance

        connector = DeviceConnector("testhost", "testuser", "testpass")
        connector.connect() # Sets connector.client

        command = "ls -l"
        output = connector.execute_command(command)

        mock_ssh_instance.exec_command.assert_called_once_with(command)
        self.assertEqual(output, "some output")

    @patch('paramiko.SSHClient')
    def test_execute_command_with_error_output(self, mock_ssh_client_constructor):
        mock_ssh_instance = MagicMock()
        mock_stdin, mock_stdout, mock_stderr = MagicMock(), MagicMock(), MagicMock()
        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = b"some error"
        mock_ssh_instance.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        mock_ssh_client_constructor.return_value = mock_ssh_instance

        connector = DeviceConnector("testhost", "testuser", "testpass")
        connector.connect()

        command = "badcommand"
        output = connector.execute_command(command)

        self.assertEqual(output, "some error") # Current behavior returns stderr if present

    @patch('paramiko.SSHClient')
    def test_execute_command_exception(self, mock_ssh_client_constructor):
        mock_ssh_instance = MagicMock()
        mock_ssh_instance.exec_command.side_effect = Exception("Execution exception")
        mock_ssh_client_constructor.return_value = mock_ssh_instance

        connector = DeviceConnector("testhost", "testuser", "testpass")
        connector.connect()

        command = "anothercommand"
        output = connector.execute_command(command)

        self.assertEqual(output, "Execution exception")

if __name__ == '__main__':
    unittest.main()
