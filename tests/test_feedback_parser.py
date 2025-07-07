import unittest
from src.ai_agent.feedback.feedback_parser import FeedbackParser

class TestFeedbackParser(unittest.TestCase):

    def setUp(self):
        self.parser = FeedbackParser(device_context=None) # Context not heavily used by basic parser

    def test_parse_output_no_output_received(self):
        result = self.parser.parse_output("any_command", None, "linux")
        self.assertFalse(result["success"])
        self.assertIn("No output received", result["message"])

    # Generic Error Keywords
    def test_parse_output_generic_error_keywords(self):
        errors = [
            ("some command", "Error: something went wrong", "linux", "error:"),
            ("another command", "system % invalid input detected here", "cisco_ios", "% invalid input"),
            ("do stuff", "Command execution failed.", "linux", "failed"),
            ("panos cmd", "this is a failure", "paloalto_panos", "failure"),
            ("cisco stuff", "Incomplete command.", "cisco_ios", "incomplete command"),
            ("cisco next", "Ambiguous command found", "cisco_ios", "ambiguous command"),
        ]
        for command, output, os_type, keyword in errors:
            result = self.parser.parse_output(command, output, os_type)
            self.assertFalse(result["success"], f"Output: '{output}' should indicate failure.")
            self.assertIn(f"Potential error detected: '{keyword}' found in output", result["message"])
            self.assertIn(keyword, result["error_line"].lower(), "Error line should contain the keyword")


    # Linux Specific
    def test_parse_output_linux_success(self):
        output = "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        20G  5.0G   15G  25% /"
        result = self.parser.parse_output("df -h", output, "linux")
        self.assertTrue(result["success"])
        self.assertIn("Command appears to have executed successfully", result["message"])

    def test_parse_output_linux_apt_install_unable_to_locate(self):
        output = "Reading package lists...\nBuilding dependency tree...\nE: Unable to locate package nonexistpkg"
        result = self.parser.parse_output("sudo apt install nonexistpkg", output, "linux")
        self.assertFalse(result["success"])
        self.assertIn("Apt install command failed", result["message"])

    def test_parse_output_linux_useradd_already_exists(self):
        output = "useradd: user 'testuser' already exists"
        result = self.parser.parse_output("useradd testuser", output, "linux")
        # Current logic treats "already exists" as an error for useradd. This might be debatable.
        self.assertFalse(result["success"])
        self.assertIn("User likely already exists", result["message"])

    # Cisco IOS Specific
    def test_parse_output_cisco_ios_success(self):
        output = "Router#show version\nCisco IOS Software, Version 15.1(4)M7, RELEASE SOFTWARE (fc1)"
        result = self.parser.parse_output("show version", output, "cisco_ios")
        self.assertTrue(result["success"])
        self.assertIn("Command appears to have executed successfully", result["message"])

    def test_parse_output_cisco_ios_incomplete_command(self):
        output = "Router(config)#interface GigabitEthernet0\n% Incomplete command."
        result = self.parser.parse_output("interface GigabitEthernet0", output, "cisco_ios")
        self.assertFalse(result["success"])
        self.assertIn("Incomplete command.", result["message"]) # Specific message
        self.assertIn("incomplete command", result["error_line"].lower())


    def test_parse_output_cisco_ios_ambiguous_command(self):
        output = "Router#sh\n% Ambiguous command: \"sh\""
        result = self.parser.parse_output("sh", output, "cisco_ios")
        self.assertFalse(result["success"])
        self.assertIn("Ambiguous command.", result["message"]) # Specific message
        self.assertIn("ambiguous command", result["error_line"].lower())

    def test_parse_output_cisco_ios_config_confirmation(self):
        # This is not an error, parser should ideally ignore it or mark success
        output = "Router(config)#hostname NewRouter\nNewRouter(config)#exit\n%SYS-5-CONFIG_I: Configured from console by console"
        result = self.parser.parse_output("hostname NewRouter", output, "cisco_ios")
        # Current basic parser might flag '%' if not for the specific exclusion.
        # Let's assume for now it's handled correctly or not seen as a generic error.
        # The current logic for cisco '%' is passive unless it matches other specific errors.
        self.assertTrue(result["success"])
        self.assertIn("Command appears to have executed successfully", result["message"])


    # Palo Alto PAN-OS Specific
    def test_parse_output_panos_success_cli(self):
        output = "admin@PA-VM> show system info\nhostname: PA-VM\n..."
        result = self.parser.parse_output("show system info", output, "paloalto_panos")
        self.assertTrue(result["success"])

    def test_parse_output_panos_success_api_xml(self):
        output = "<response status=\"success\"><result><system><hostname>PA-VM</hostname></system></result></response>"
        result = self.parser.parse_output("api_call_show_system_info", output, "paloalto_panos")
        self.assertTrue(result["success"])

    def test_parse_output_panos_cli_invalid_syntax(self):
        output = "admin@PA-VM# set interface ethernet1/1 ip 1.1.1.1\n  invalid syntax"
        result = self.parser.parse_output("set interface ethernet1/1 ip 1.1.1.1", output, "paloalto_panos")
        self.assertFalse(result["success"])
        self.assertIn("PAN-OS command syntax error", result["message"])
        self.assertIn("invalid syntax", result["error_line"].lower())


    def test_parse_output_panos_api_error_xml(self):
        output = "<response status=\"error\" code=\"19\"><msg>Invalid  command</msg></response>"
        result = self.parser.parse_output("api_call_bad_command", output, "paloalto_panos")
        self.assertFalse(result["success"])
        self.assertIn("PAN-OS API returned an error", result["message"])
        self.assertIn('<response status="error"', result["error_line"].lower())


    # Data Extraction Placeholder
    def test_extract_data_from_output_placeholder(self):
        # This method is just a placeholder in the actual code
        data = self.parser._extract_data_from_output("any_command", "any_output", "any_os")
        self.assertIsNone(data)

if __name__ == '__main__':
    unittest.main()
