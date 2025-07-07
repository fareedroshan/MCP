# Executor Module

class Executor:
    def __init__(self, device_connector, command_validator):
        self.device_connector = device_connector
        self.command_validator = command_validator

    def execute_commands_on_device(self, commands_str, os_type, ask_confirmation=True):
        """
        Executes a list of commands (as a string, one command per line) on the device
        after validation and optional confirmation.
        Handles Cisco 'configure terminal' mode if needed.
        """
        if not self.device_connector or not self.device_connector.client:
            print("Executor: Device not connected.")
            return None, "Device not connected."

        commands_to_execute = [cmd.strip() for cmd in commands_str.splitlines() if cmd.strip()]
        if not commands_to_execute:
            print("Executor: No commands to execute.")
            return "", "No commands provided."

        print(f"\nExecutor: Preparing to execute on {os_type} device '{self.device_connector.hostname}':")
        for cmd in commands_to_execute:
            print(f"  - {cmd}")

        # Validate all commands first
        all_safe = True
        for cmd in commands_to_execute:
            if not self.command_validator.is_safe(cmd, os_type):
                print(f"Executor: Command '{cmd}' failed safety validation. Aborting.")
                return None, f"Command '{cmd}' is unsafe."

        if ask_confirmation:
            # In a real CLI/UI, this would be an actual prompt to the user
            # For now, we simulate it or assume 'yes' for automated testing
            # confirmation = input("Proceed with execution? (yes/no): ").lower()
            # For non-interactive, default to yes or make it a parameter
            confirmation = "yes"
            if confirmation != "yes":
                print("Executor: Execution cancelled by user.")
                return None, "Execution cancelled by user."

        full_output = ""
        error_occurred = False

        # Handle Cisco 'configure terminal'
        is_cisco_config_session = False
        if os_type == "cisco_ios":
            # Check if any command needs config mode
            if any(self.command_validator.needs_config_mode(cmd, os_type) for cmd in commands_to_execute):
                print("Executor: Entering Cisco config mode.")
                conf_t_output = self.device_connector.execute_command("configure terminal")
                full_output += f"configure terminal\n{conf_t_output}\n"
                if "Enter configuration commands" not in conf_t_output and "% Invalid input" in conf_t_output : # Basic check
                    print("Executor: Failed to enter config mode.")
                    return full_output, "Failed to enter Cisco config mode."
                is_cisco_config_session = True

        for cmd in commands_to_execute:
            print(f"Executor: Executing '{cmd}'...")
            output = self.device_connector.execute_command(cmd)
            full_output += f"$ {cmd}\n{output}\n"
            print(f"Output for '{cmd}':\n{output}")
            # Basic error check (can be improved by FeedbackParser)
            if output and ("% Invalid input" in output or "Error:" in output or "fail" in output.lower()):
                print(f"Executor: Potential error detected in output for '{cmd}'.")
                # error_occurred = True # Decide if script should stop or continue
                # For now, we continue but log it.

        if is_cisco_config_session:
            print("Executor: Exiting Cisco config mode.")
            end_output = self.device_connector.execute_command("end")
            full_output += f"end\n{end_output}\n"

        if error_occurred:
            return full_output, "One or more commands may have failed."
        else:
            return full_output, "Commands executed successfully."


if __name__ == '__main__':
    print("Executor module placeholder execution.")
    # This requires a live SSH connection and other modules.
    # from ai_agent.connectors.device_connector import DeviceConnector
    # from ai_agent.validation.command_validator import CommandValidator
    # from ai_agent.context.context_builder import ContextBuilder # For context

    # # Example for Linux (replace with your details)
    # # Ensure you have a test Linux VM/server with SSH enabled
    # try:
    #     print("\n--- Testing Linux Execution ---")
    #     linux_host = "YOUR_LINUX_IP"
    #     linux_user = "YOUR_LINUX_USER"
    #     linux_pass = "YOUR_LINUX_PASSWORD"

    #     connector_linux = DeviceConnector(linux_host, linux_user, linux_pass)
    #     if connector_linux.connect():
    #         # Gather context (optional for executor, but good for validator)
    #         # builder_linux = ContextBuilder(connector_linux)
    #         # context_linux = builder_linux.gather_context("linux")
    #         context_linux = {"os_type": "linux"} # Simplified for this test

    #         validator_linux = CommandValidator(context_linux)
    #         executor_linux = Executor(connector_linux, validator_linux)

    #         # Safe commands
    #         cmds_linux_safe = "echo 'Hello from AI Agent'\ndate\nls -la /tmp | grep test_file || touch /tmp/test_file_ai_agent"
    #         output, status = executor_linux.execute_commands_on_device(cmds_linux_safe, "linux", ask_confirmation=False)
    #         print(f"Status: {status}")
    #         # print(f"Full Output:\n{output}")

    #         # Potentially unsafe command (should be caught by validator if patterns are good)
    #         # cmds_linux_unsafe = "rm -rf /some_non_existent_test_dir_for_safety"
    #         # output_unsafe, status_unsafe = executor_linux.execute_commands_on_device(cmds_linux_unsafe, "linux", ask_confirmation=False)
    #         # print(f"Status (unsafe): {status_unsafe}")

    #         connector_linux.disconnect()
    # except Exception as e:
    #     print(f"Error during Linux test: {e}")

    # # Example for Cisco (replace with your details if you have a Cisco lab)
    # # Ensure 'configure terminal' and 'end' commands work as expected via your DeviceConnector
    # try:
    #     print("\n--- Testing Cisco IOS Execution ---")
    #     cisco_host = "YOUR_CISCO_IP"
    #     cisco_user = "YOUR_CISCO_USER"
    #     cisco_pass = "YOUR_CISCO_PASSWORD"

    #     # connector_cisco = DeviceConnector(cisco_host, cisco_user, cisco_pass)
    #     # if connector_cisco.connect():
    #     #     context_cisco = {"os_type": "cisco_ios"} # Simplified
    #     #     validator_cisco = CommandValidator(context_cisco)
    #     #     executor_cisco = Executor(connector_cisco, validator_cisco)

    #     #     # Non-config commands
    #     #     cmds_cisco_show = "show version | inc IOS\nshow ip interface brief"
    #     #     output_show, status_show = executor_cisco.execute_commands_on_device(cmds_cisco_show, "cisco_ios", ask_confirmation=False)
    #     #     print(f"Status (show): {status_show}")
    #     #     # print(f"Full Output (show):\n{output_show}")

    #     #     # Config commands
    #     #     # Ensure these are safe for your lab environment!
    #     #     cmds_cisco_config = "interface Loopback99\ndescription AI_AGENT_TEST_LOOPBACK\nip address 99.99.99.99 255.255.255.255"
    #     #     output_config, status_config = executor_cisco.execute_commands_on_device(cmds_cisco_config, "cisco_ios", ask_confirmation=False)
    #     #     print(f"Status (config): {status_config}")
    #     #     # print(f"Full Output (config):\n{output_config}")

    #     #     # Clean up (optional, be careful)
    #     #     # cleanup_cmds = "no interface Loopback99"
    #     #     # output_cleanup, status_cleanup = executor_cisco.execute_commands_on_device(cleanup_cmds, "cisco_ios", ask_confirmation=False)
    #     #     # print(f"Status (cleanup): {status_cleanup}")

    #     #     connector_cisco.disconnect()
    #     print("Cisco test skipped or requires manual setup.")
    # except Exception as e:
    #     print(f"Error during Cisco test: {e}")
