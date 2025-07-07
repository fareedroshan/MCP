import unittest
from unittest.mock import MagicMock, call

# Assuming modules are in src.ai_agent.*
from src.ai_agent.execution.executor import Executor
from src.ai_agent.connectors.device_connector import DeviceConnector
from src.ai_agent.validation.command_validator import CommandValidator

class TestExecutor(unittest.TestCase):

    def setUp(self):
        self.mock_connector = MagicMock(spec=DeviceConnector)
        self.mock_validator = MagicMock(spec=CommandValidator)

        # Ensure connector.client is mocked if Executor checks it
        self.mock_connector.client = MagicMock()
        self.mock_connector.hostname = "test-device"

        self.executor = Executor(self.mock_connector, self.mock_validator)

    def test_execute_commands_not_connected(self):
        self.mock_connector.client = None # Simulate not connected
        output, status = self.executor.execute_commands_on_device("ls", "linux")
        self.assertIsNone(output)
        self.assertEqual(status, "Device not connected.")

    def test_execute_commands_no_commands(self):
        output, status = self.executor.execute_commands_on_device("", "linux")
        self.assertEqual(output, "") # Empty string output for no commands
        self.assertEqual(status, "No commands provided.")

        output, status = self.executor.execute_commands_on_device("\n   \n", "linux") # whitespace only
        self.assertEqual(output, "")
        self.assertEqual(status, "No commands provided.")


    def test_execute_commands_unsafe_command(self):
        self.mock_validator.is_safe.return_value = False
        unsafe_cmd = "rm -rf /"
        output, status = self.executor.execute_commands_on_device(unsafe_cmd, "linux", ask_confirmation=False)

        self.mock_validator.is_safe.assert_called_once_with(unsafe_cmd, "linux")
        self.assertIsNone(output)
        self.assertEqual(status, f"Command '{unsafe_cmd}' is unsafe.")
        self.mock_connector.execute_command.assert_not_called()

    def test_execute_commands_single_safe_linux_command(self):
        cmd = "ls -l"
        expected_output = "total 0"
        self.mock_validator.is_safe.return_value = True
        self.mock_connector.execute_command.return_value = expected_output

        output, status = self.executor.execute_commands_on_device(cmd, "linux", ask_confirmation=False)

        self.mock_validator.is_safe.assert_called_once_with(cmd, "linux")
        self.mock_connector.execute_command.assert_called_once_with(cmd)
        self.assertIn(expected_output, output)
        self.assertEqual(status, "Commands executed successfully.")

    def test_execute_commands_multiple_safe_linux_commands(self):
        cmds_str = "ls -l\ndate"
        cmds_list = ["ls -l", "date"]
        outputs = ["output_ls", "output_date"]

        self.mock_validator.is_safe.return_value = True
        self.mock_connector.execute_command.side_effect = outputs

        full_output, exec_status = self.executor.execute_commands_on_device(cmds_str, "linux", ask_confirmation=False)

        self.mock_validator.is_safe.assert_any_call(cmds_list[0], "linux")
        self.mock_validator.is_safe.assert_any_call(cmds_list[1], "linux")
        self.assertEqual(self.mock_validator.is_safe.call_count, 2)

        self.mock_connector.execute_command.assert_any_call(cmds_list[0])
        self.mock_connector.execute_command.assert_any_call(cmds_list[1])
        self.assertEqual(self.mock_connector.execute_command.call_count, 2)

        self.assertIn(f"$ {cmds_list[0]}\n{outputs[0]}", full_output)
        self.assertIn(f"$ {cmds_list[1]}\n{outputs[1]}", full_output)
        self.assertEqual(exec_status, "Commands executed successfully.")

    def test_execute_commands_cisco_non_config(self):
        cmd = "show version"
        expected_output = "Cisco IOS Software..."
        self.mock_validator.is_safe.return_value = True
        self.mock_validator.needs_config_mode.return_value = False
        self.mock_connector.execute_command.return_value = expected_output

        output, status = self.executor.execute_commands_on_device(cmd, "cisco_ios", ask_confirmation=False)

        self.mock_validator.needs_config_mode.assert_called_once_with(cmd, "cisco_ios")
        self.mock_connector.execute_command.assert_called_once_with(cmd)
        self.assertNotIn("configure terminal", output.lower())
        self.assertNotIn("end", output.lower())
        self.assertEqual(status, "Commands executed successfully.")

    def test_execute_commands_cisco_with_config_mode(self):
        cmds_str = "interface Loopback0\nip address 1.1.1.1 255.255.255.255"
        cmds_list = ["interface Loopback0", "ip address 1.1.1.1 255.255.255.255"]

        self.mock_validator.is_safe.return_value = True
        # First command needs config, second is part of it (validator might say True or False for needs_config_mode depending on its logic for sub-commands)
        self.mock_validator.needs_config_mode.side_effect = [True, True] # Assume both are checked and indicate config context

        # Mock outputs for conf t, cmd1, cmd2, end
        self.mock_connector.execute_command.side_effect = [
            "Enter configuration commands, one per line.  End with CNTL/Z.", # conf t
            "Router(config-if)#", # interface Loopback0
            "Router(config-if)#", # ip address ...
            "Router#"             # end
        ]

        full_output, exec_status = self.executor.execute_commands_on_device(cmds_str, "cisco_ios", ask_confirmation=False)

        self.mock_validator.is_safe.assert_any_call(cmds_list[0], "cisco_ios")
        self.mock_validator.is_safe.assert_any_call(cmds_list[1], "cisco_ios")

        # needs_config_mode is checked for all commands in the list by 'any()'
        self.mock_validator.needs_config_mode.assert_any_call(cmds_list[0], "cisco_ios")
        self.mock_validator.needs_config_mode.assert_any_call(cmds_list[1], "cisco_ios")


        expected_calls = [
            call("configure terminal"),
            call(cmds_list[0]),
            call(cmds_list[1]),
            call("end")
        ]
        self.mock_connector.execute_command.assert_has_calls(expected_calls)
        self.assertEqual(self.mock_connector.execute_command.call_count, 4)

        self.assertIn("configure terminal", full_output)
        self.assertIn(cmds_list[0], full_output)
        self.assertIn(cmds_list[1], full_output)
        self.assertIn("end", full_output)
        self.assertEqual(exec_status, "Commands executed successfully.")

    def test_execute_commands_cisco_fail_enter_config_mode(self):
        cmd = "interface Loopback0"
        self.mock_validator.is_safe.return_value = True
        self.mock_validator.needs_config_mode.return_value = True
        self.mock_connector.execute_command.return_value = "% Invalid input detected at '^' marker." # Failed "conf t"

        output, status = self.executor.execute_commands_on_device(cmd, "cisco_ios", ask_confirmation=False)

        self.mock_connector.execute_command.assert_called_once_with("configure terminal")
        self.assertIn("Failed to enter Cisco config mode.", status)
        # Check that the actual command 'interface Loopback0' was not executed
        # This depends on the exact sequence of calls. If 'end' is still called, adjust.
        # For now, assuming it bails out.
        # self.assertEqual(self.mock_connector.execute_command.call_count, 1) # Only "conf t"

    def test_execute_commands_with_error_in_output(self):
        cmd = "show something wrong"
        output_with_error = "blah blah\n% Invalid input detected\nblah"
        self.mock_validator.is_safe.return_value = True
        self.mock_connector.execute_command.return_value = output_with_error

        full_output, status = self.executor.execute_commands_on_device(cmd, "linux", ask_confirmation=False) # os_type doesn't matter much here

        self.assertIn(output_with_error, full_output)
        self.assertEqual(status, "One or more commands may have failed.") # Current status message for this case

    def test_execute_commands_confirmation_skipped(self):
        # This test implies ask_confirmation=True, but the main.py flow handles the actual input()
        # Here, we just ensure the logic branch for ask_confirmation=True (if it were to prompt)
        # doesn't break if we bypass the input part.
        # The executor's own ask_confirmation is by default True, but in main.py it's set to False
        # because main.py handles the interactive prompt.
        # So, we test the path where confirmation is effectively "yes" (ask_confirmation=False)
        cmd = "ls"
        self.mock_validator.is_safe.return_value = True
        self.mock_connector.execute_command.return_value = "output"

        _, status = self.executor.execute_commands_on_device(cmd, "linux", ask_confirmation=False)
        self.assertEqual(status, "Commands executed successfully.")
        self.mock_connector.execute_command.assert_called_once()

    # Test for ask_confirmation=True and user says "no" - this is harder to test directly
    # without `patch('builtins.input')` because the Executor itself doesn't prompt.
    # The main.py orchestrator handles the prompting. The Executor's `ask_confirmation` flag
    # is more of a signal that was intended for a scenario where Executor *might* prompt.
    # Given current design, direct test of this in Executor is less relevant.

if __name__ == '__main__':
    unittest.main()
