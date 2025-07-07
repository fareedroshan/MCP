# Feedback Parser Module

class FeedbackParser:
    def __init__(self, device_context):
        self.device_context = device_context # To tailor parsing if needed

    def parse_output(self, command, output, os_type):
        """
        Parses the output of a command to determine success, failure, or extract data.
        This is a basic parser and would need to be significantly more sophisticated
        for robust error detection and data extraction.
        """
        print(f"Parsing output for command '{command}' on {os_type}...")
        # print(f"Raw Output:\n{output}") # For debugging

        # Default status
        result = {
            "success": True, # Assume success unless an error is found
            "message": "Command output received.",
            "data": None # For extracted data, if any
        }

        if output is None:
            result["success"] = False
            result["message"] = "No output received from device (connection issue or command produced no STDOUT/STDERR)."
            return result

        output_lower = output.lower()

        # Generic error indicators (very basic)
        generic_error_keywords = [
            "error:", "% invalid input", "command rejected", "unknown command",
            "failure", "failed" # Removed "incomplete command" and "ambiguous command"
        ]
        for err_key in generic_error_keywords:
            if err_key in output_lower:
                result["success"] = False
                result["message"] = f"Potential error detected: '{err_key}' found in output."
                # Extract the line containing the error for more context
                for line in output.splitlines():
                    if err_key in line.lower():
                        result["error_line"] = line
                        break
                return result # Stop on first major error indicator

        # OS-specific parsing can be added here
        if os_type == "linux":
            # Example: if command was 'useradd' and output contains "already exists"
            if "useradd" in command and "already exists" in output_lower:
                result["success"] = False # Or True, depending on idempotency definition
                result["message"] = "User likely already exists."
            # Example: if command was 'apt install' and it failed
            if command.startswith("apt install") or command.startswith("apt-get install"):
                apt_error_keywords = ["unable to locate package", "e:"] # "E:" becomes "e:" in output_lower
                for keyword in apt_error_keywords:
                    if keyword in output_lower:
                        result["success"] = False
                        result["message"] = "Apt install command failed. Package not found or other apt error."
                        for line in output.splitlines(): # Try to get the error line
                            if keyword in line.lower(): # Check original case or common variations if needed
                                result["error_line"] = line
                                break
                        return result # Return immediately after finding apt error

        elif os_type == "cisco_ios":
            # Cisco errors often start with '%'
            if "% " in output: # A bit broad, but captures many Cisco info/error messages
                # Filter out common informational messages that aren't errors
                if not ("%SYS-" in output and "configured from console" in output_lower): # e.g. %SYS-5-CONFIG_I: Configured from console by console
                    # If it's not a known informational message, assume it might be an issue or needs review
                    # This logic needs to be much more refined.
                    pass # For now, don't mark all '%' as errors unless they match specific error patterns

            # More specific Cisco error checks
            cisco_error_patterns = {
                "incomplete command": "Incomplete command.",
                "ambiguous command": "Ambiguous command.",
                # Can add more known specific error strings and their user-friendly messages
            }
            for pattern, msg in cisco_error_patterns.items():
                if pattern in output_lower:
                    result["success"] = False
                    result["message"] = msg
                    for line in output.splitlines():
                        if pattern in line.lower():
                            result["error_line"] = line
                            break
                    return result # Stop on first specific Cisco error


        elif os_type == "paloalto_panos":
            # PAN-OS CLI errors or API error responses
            panos_cli_errors = ['invalid syntax', 'unknown command']
            panos_api_error_pattern = '<response status="error"'

            for err_pattern in panos_cli_errors:
                if err_pattern in output_lower:
                    result["success"] = False
                    result["message"] = f"PAN-OS command error: '{err_pattern}' found."
                    for line in output.splitlines():
                        if err_pattern in line.lower():
                            result["error_line"] = line
                            break
                    return result # Stop on first major error indicator

            if panos_api_error_pattern in output_lower: # For XML API
                result["success"] = False
                result["message"] = "PAN-OS API returned an error."
                for line in output.splitlines(): # Find the line with the API error status
                    if panos_api_error_pattern in line.lower():
                        result["error_line"] = line
                        break
                # Potentially parse XML error details here
                return result

        if result["success"]:
             result["message"] = "Command appears to have executed successfully (no obvious errors found)."

        # Placeholder for actual data extraction logic
        # e.g., if command was 'show ip interface brief', parse and structure the interface data
        # result["data"] = self._extract_data_from_output(command, output, os_type)

        return result

    def _extract_data_from_output(self, command, output, os_type):
        """
        Placeholder for data extraction logic.
        This would parse structured data from command output.
        """
        # if os_type == "cisco_ios" and "show ip interface brief" in command:
        #   return parse_show_ip_interface_brief(output) # A dedicated parsing function
        return None


if __name__ == '__main__':
    print("FeedbackParser module placeholder execution.")
    parser = FeedbackParser(device_context=None) # Context not used in this basic example

    # Test Linux output
    print("\n--- Testing Linux Feedback Parsing ---")
    linux_output_ok = "Last login: Mon Jul 22 10:00:00 2024 from 192.168.1.1\nuser@host:~$ date\nMon Jul 22 10:00:01 UTC 2024"
    res_linux_ok = parser.parse_output("date", linux_output_ok, "linux")
    print(f"Linux OK: {res_linux_ok}")

    linux_output_err = "user@host:~$ sudo apt install nonexistpkg\nReading package lists...\nE: Unable to locate package nonexistpkg"
    res_linux_err = parser.parse_output("sudo apt install nonexistpkg", linux_output_err, "linux")
    print(f"Linux Error: {res_linux_err}")

    # Test Cisco output
    print("\n--- Testing Cisco IOS Feedback Parsing ---")
    cisco_output_ok = "Router#show version\nCisco IOS Software, ... Version 15.7(3)M3, ..."
    res_cisco_ok = parser.parse_output("show version", cisco_output_ok, "cisco_ios")
    print(f"Cisco OK: {res_cisco_ok}")

    cisco_output_err_invalid = "Router(config)#int GigaEthernet0/0\n% Invalid input detected at '^' marker."
    res_cisco_err_inv = parser.parse_output("int GigaEthernet0/0", cisco_output_err_invalid, "cisco_ios")
    print(f"Cisco Error (Invalid): {res_cisco_err_inv}")

    cisco_output_err_ambiguous = "Router#sh\n% Ambiguous command: \"sh\""
    res_cisco_err_amb = parser.parse_output("sh", cisco_output_err_ambiguous, "cisco_ios")
    print(f"Cisco Error (Ambiguous): {res_cisco_err_amb}")

    # Test Palo Alto output (very basic)
    print("\n--- Testing Palo Alto PAN-OS Feedback Parsing ---")
    panos_output_ok = "<response status=\"success\"><result><system><hostname>PA-VM</hostname>...</system></result></response>" # XML API example
    res_panos_ok = parser.parse_output("show system info (via API)", panos_output_ok, "paloalto_panos")
    print(f"PAN-OS OK (API): {res_panos_ok}")

    panos_output_err_cli = "admin@PA-VM> configure\nEntering configuration mode\n[edit]\nadmin@PA-VM# set interface ethernet1/1 ip 1.1.1.1\n  invalid syntax"
    res_panos_err_cli = parser.parse_output("set interface ethernet1/1 ip 1.1.1.1", panos_output_err_cli, "paloalto_panos")
    print(f"PAN-OS Error (CLI): {res_panos_err_cli}")

    no_output_res = parser.parse_output("some command", None, "linux")
    print(f"No output: {no_output_res}")
