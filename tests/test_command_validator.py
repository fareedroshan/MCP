import unittest
from src.ai_agent.validation.command_validator import CommandValidator

class TestCommandValidator(unittest.TestCase):

    def setUp(self):
        self.mock_linux_context = {"os_type": "linux", "hostname": "test-server"}
        self.mock_cisco_context = {"os_type": "cisco_ios", "hostname": "test-router"}
        self.mock_panos_context = {"os_type": "paloalto_panos", "hostname": "test-fw"}

        self.linux_validator = CommandValidator(self.mock_linux_context)
        self.cisco_validator = CommandValidator(self.mock_cisco_context)
        self.panos_validator = CommandValidator(self.mock_panos_context)

    # Test is_safe method
    def test_is_safe_linux_safe_commands(self):
        safe_commands = ["ls -l", "echo 'hello'", "cat /tmp/file", "sudo apt update"]
        for cmd in safe_commands:
            self.assertTrue(self.linux_validator.is_safe(cmd, "linux"), f"Command '{cmd}' should be safe for Linux")

    def test_is_safe_linux_destructive_commands(self):
        destructive_commands = ["rm -rf /", "sudo mkfs.ext4 /dev/sda1", "dd if=/dev/zero of=/dev/sdb", "reboot", "shutdown -h now"]
        for cmd in destructive_commands:
            self.assertFalse(self.linux_validator.is_safe(cmd, "linux"), f"Command '{cmd}' should be destructive for Linux")

    def test_is_safe_cisco_safe_commands(self):
        safe_commands = ["show ip interface brief", "show version", "show running-config"]
        for cmd in safe_commands:
            self.assertTrue(self.cisco_validator.is_safe(cmd, "cisco_ios"), f"Command '{cmd}' should be safe for Cisco IOS")

    def test_is_safe_cisco_destructive_commands(self):
        destructive_commands = ["erase startup-config", "delete flash:vlan.dat", "reload", "write erase"]
        for cmd in destructive_commands:
            self.assertFalse(self.cisco_validator.is_safe(cmd, "cisco_ios"), f"Command '{cmd}' should be destructive for Cisco IOS")

    def test_is_safe_panos_safe_commands(self):
        # Assuming these are safe based on current placeholder patterns
        safe_commands = ["show system info", "show interface ethernet1/1"]
        for cmd in safe_commands:
            self.assertTrue(self.panos_validator.is_safe(cmd, "paloalto_panos"), f"Command '{cmd}' should be safe for PAN-OS")

    def test_is_safe_panos_destructive_commands(self):
        # Based on example destructive patterns
        destructive_commands = ["delete rulebase security rules all", "request system private-data-reset"]
        for cmd in destructive_commands:
            self.assertFalse(self.panos_validator.is_safe(cmd, "paloalto_panos"), f"Command '{cmd}' should be destructive for PAN-OS")

    def test_is_safe_empty_or_invalid_command(self):
        invalid_commands = ["", "   ", None] # None won't pass type hint but good to test if it reaches
        for cmd in invalid_commands:
            if cmd is None: # Skip None as it would fail earlier, or handle if validator is made to accept it
                 with self.assertRaises(TypeError): # or some other error depending on how it's handled
                     self.linux_validator.is_safe(cmd, "linux")
            else:
                self.assertFalse(self.linux_validator.is_safe(cmd, "linux"), f"Command '{cmd}' should be unsafe/invalid")


    # Test needs_config_mode method
    def test_needs_config_mode_cisco_config_commands(self):
        config_commands = [
            "interface GigabitEthernet0/0",
            "router ospf 1",
            "ip route 0.0.0.0 0.0.0.0 192.168.1.254",
            "access-list 101 permit ip any any",
            "hostname NewRouterName",
            "banner motd #Restricted Access#",
            "enable secret mypassword",
            "line vty 0 4",
            "ip address 10.1.1.1 255.255.255.0"
        ]
        for cmd in config_commands:
            self.assertTrue(self.cisco_validator.needs_config_mode(cmd, "cisco_ios"), f"Command '{cmd}' should require config mode")

    def test_needs_config_mode_cisco_set_commands(self):
        # Example for 'set' style commands if added to validator logic
        # self.assertTrue(self.cisco_validator.needs_config_mode("set system clock ...", "cisco_ios"))
        pass # Current validator doesn't explicitly have generic "set", but some specific "set" might be part of other keywords

    def test_needs_config_mode_cisco_non_config_commands(self):
        non_config_commands = [
            "show ip interface brief",
            "show version",
            "copy running-config startup-config", # This is exec mode
            "ping 8.8.8.8"
        ]
        for cmd in non_config_commands:
            self.assertFalse(self.cisco_validator.needs_config_mode(cmd, "cisco_ios"), f"Command '{cmd}' should not require config mode")

    def test_needs_config_mode_non_cisco_os(self):
        self.assertFalse(self.linux_validator.needs_config_mode("some command", "linux"), "needs_config_mode should be False for non-Cisco OS")
        self.assertFalse(self.panos_validator.needs_config_mode("some command", "paloalto_panos"), "needs_config_mode should be False for non-Cisco OS")

    def test_is_safe_command_with_varied_casing(self):
        self.assertFalse(self.linux_validator.is_safe("RM -rf /tmp/test", "linux"), "Case-insensitivity check for rm -rf")
        self.assertFalse(self.cisco_validator.is_safe("Reload", "cisco_ios"), "Case-insensitivity check for reload")


if __name__ == '__main__':
    unittest.main()
