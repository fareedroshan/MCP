# Command Validator Module

class CommandValidator:
    def __init__(self, device_context):
        self.device_context = device_context
        # Define potentially destructive commands patterns for different OS types
        # This is a very basic example and needs significant expansion
        self.destructive_patterns = {
            "linux": [
                r"\brm\s+-rf",
                r"\bmkfs",
                r"\bfdisk",
                r"\bdd\b",
                r"reboot", # Could be disruptive
                r"shutdown", # Could be disruptive
                r"poweroff"
            ],
            "cisco_ios": [
                r"erase\s+startup-config",
                r"delete\s+flash:",
                r"reload", # Could be disruptive
                r"write\s+erase"
            ],
            "paloalto_panos": [
                # PAN-OS CLI/API commands that are destructive
                # e.g., related to deleting policies, interfaces, or system reset
                r"delete\s+rulebase", # Example, needs verification
                r"request\s+system\s+private-data-reset" # Highly destructive
            ]
        }
        # Define commands that require 'configure terminal' or equivalent for Cisco
        self.cisco_config_mode_commands = [
            "interface", "router ospf", "ip route", "access-list",
            "crypto map", "snmp-server", "logging host", "ntp server",
            # Keywords that usually imply configuration
            "hostname", "banner motd", "enable secret", "line vty", "ip address"
        ]


    def is_safe(self, command, os_type):
        """
        Checks if a command is safe to execute based on a predefined list of
        destructive commands and basic syntax checks.
        This is a simplified validator. A real-world validator would be more complex,
        potentially involving a sandbox or more sophisticated pattern matching.
        """
        print(f"Validating command for {os_type}: '{command}'")

        # 1. Check for known destructive commands
        if os_type in self.destructive_patterns:
            for pattern in self.destructive_patterns[os_type]:
                import re # Import re here as it's used within the loop
                if re.search(pattern, command, re.IGNORECASE):
                    print(f"Command '{command}' matched destructive pattern '{pattern}'. Unsafe.")
                    return False

        # 2. Basic syntax checks (very rudimentary)
        if not command or not isinstance(command, str) or len(command.strip()) == 0:
            print("Command is empty or invalid. Unsafe.")
            return False

        # 3. Placeholder for more sophisticated checks (e.g., command structure per OS)
        if os_type == "cisco_ios":
            # Example: Check if a command looks like it needs config mode but isn't wrapped
            # This is a very naive check. A proper solution would understand command context.
            pass


        print(f"Command '{command}' deemed safe by basic validator.")
        return True

    def needs_config_mode(self, command, os_type):
        """
        Checks if a Cisco IOS command likely requires 'configure terminal' mode.
        """
        if os_type != "cisco_ios":
            return False

        command_lower = command.strip().lower()
        for config_cmd_pattern in self.cisco_config_mode_commands:
            if command_lower.startswith(config_cmd_pattern.lower()):
                return True
        # Check for set commands which are usually config commands
        if command_lower.startswith("set "): # Common in some Cisco-like OS or specific modes
             return True
        return False

if __name__ == '__main__':
    print("CommandValidator module placeholder execution.")
    # Example (context here is not deeply used by this basic validator yet)
    mock_context = {"os_type": "linux", "hostname": "test-server"}
    validator = CommandValidator(mock_context)

    # Test Linux commands
    print(f"\nTesting Linux commands:")
    safe_linux_cmd = "ls -l /tmp"
    unsafe_linux_cmd = "sudo rm -rf /"
    print(f"'{safe_linux_cmd}' is safe: {validator.is_safe(safe_linux_cmd, 'linux')}")
    print(f"'{unsafe_linux_cmd}' is safe: {validator.is_safe(unsafe_linux_cmd, 'linux')}")

    # Test Cisco commands
    mock_context_cisco = {"os_type": "cisco_ios", "hostname": "test-router"}
    validator_cisco = CommandValidator(mock_context_cisco)
    print(f"\nTesting Cisco IOS commands:")
    safe_cisco_cmd = "show ip interface brief"
    unsafe_cisco_cmd = "erase startup-config"
    config_cisco_cmd = "interface GigabitEthernet0/0"
    print(f"'{safe_cisco_cmd}' is safe: {validator_cisco.is_safe(safe_cisco_cmd, 'cisco_ios')}")
    print(f"'{unsafe_cisco_cmd}' is safe: {validator_cisco.is_safe(unsafe_cisco_cmd, 'cisco_ios')}")
    print(f"'{config_cisco_cmd}' needs config mode: {validator_cisco.needs_config_mode(config_cisco_cmd, 'cisco_ios')}")
    print(f"'{safe_cisco_cmd}' needs config mode: {validator_cisco.needs_config_mode(safe_cisco_cmd, 'cisco_ios')}")

    # Test Palo Alto commands (destructive patterns are examples)
    mock_context_pa = {"os_type": "paloalto_panos", "hostname": "fw-1"}
    validator_pa = CommandValidator(mock_context_pa)
    print(f"\nTesting Palo Alto PAN-OS commands:")
    safe_pa_cmd = "show system info"
    unsafe_pa_cmd = "request system private-data-reset" # This is a very destructive command
    print(f"'{safe_pa_cmd}' is safe: {validator_pa.is_safe(safe_pa_cmd, 'paloalto_panos')}")
    print(f"'{unsafe_pa_cmd}' is safe: {validator_pa.is_safe(unsafe_pa_cmd, 'paloalto_panos')}")
