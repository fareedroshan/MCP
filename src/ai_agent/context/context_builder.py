# Context Builder Module
import json

class ContextBuilder:
    def __init__(self, device_connector):
        self.device_connector = device_connector
        self.context = {}

    def gather_context(self, os_type):
        """Gathers basic context from the device."""
        if not self.device_connector or not self.device_connector.client:
            print("Device not connected. Cannot gather context.")
            return None

        print(f"Gathering context for OS type: {os_type}...")
        try:
            if os_type.lower() == "linux":
                self._gather_linux_context()
            elif os_type.lower() == "cisco_ios":
                self._gather_cisco_ios_context()
            elif os_type.lower() == "paloalto_panos":
                self._gather_paloalto_panos_context()
            else:
                print(f"Unsupported OS type: {os_type}")
                return None

            print("Context gathering complete.")
            return self.context
        except Exception as e:
            print(f"Error gathering context: {e}")
            return None

    def _gather_linux_context(self):
        """Gathers context specific to Linux servers."""
        self.context['os_type'] = 'linux'
        self.context['hostname'] = self.device_connector.execute_command("hostname").strip()
        self.context['os_version'] = self.device_connector.execute_command("cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"'").strip()
        self.context['interfaces'] = self._parse_linux_interfaces()
        # Add more Linux-specific commands as needed (e.g., routing, services)

    def _parse_linux_interfaces(self):
        """Parses interface information from ip addr command."""
        output = self.device_connector.execute_command("ip addr")
        interfaces = {}
        current_interface_name = None
        if output:
            for line in output.splitlines():
                stripped_line = line.strip()
                # Check for a new interface line (e.g., "2: eth0: <...")
                # Example: "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000"
                if not line.startswith(" ") and ":" in line:
                    try:
                        # Split line like "2: eth0: <FLAGS> mtu ..."
                        parts = line.split(":", 2) # Expect 3 parts: num, name_flags, details_line
                        iface_name_from_line = parts[1].strip()

                        if iface_name_from_line == "lo":
                            current_interface_name = None
                            continue
                        current_interface_name = iface_name_from_line
                        interfaces[current_interface_name] = {}

                        details_part = parts[2] # This is the part with "<...>" and "state UP"

                        # Prefer "state UP/DOWN" from the latter part of the line
                        if 'state ' in details_part:
                            status_part = details_part.split('state ')[1].split(' ')[0]
                            interfaces[current_interface_name]['status'] = status_part.upper()
                        # Fallback to flags if state not found
                        elif '<' in details_part and '>' in details_part:
                            flags_str = details_part.split('<')[1].split('>')[0]
                            if 'UP' in flags_str.upper().split(','):
                                interfaces[current_interface_name]['status'] = "UP"
                            else:
                                interfaces[current_interface_name]['status'] = "UNKNOWN"
                        else:
                            interfaces[current_interface_name]['status'] = "UNKNOWN"
                    except (IndexError, ValueError):
                        current_interface_name = None
                        continue

                elif current_interface_name and stripped_line.startswith("inet "):
                    ip_parts = stripped_line.split()
                    if len(ip_parts) >= 2:
                        if 'ip_address' not in interfaces[current_interface_name]:
                            interfaces[current_interface_name]['ip_address'] = ip_parts[1]

        interfaces_cleaned = {k: v for k, v in interfaces.items() if v and v.get('status')}
        return interfaces_cleaned

    def _gather_cisco_ios_context(self):
        """Gathers context specific to Cisco IOS devices."""
        self.context['os_type'] = 'cisco_ios'
        # Note: Cisco commands might need "terminal length 0" before running to avoid pagination
        self.device_connector.execute_command("terminal length 0") # Ensure full output
        self.context['hostname'] = self.device_connector.execute_command("show running-config | include hostname").split()[-1]
        version_output = self.device_connector.execute_command("show version | include Cisco IOS Software")
        if version_output:
             # Example: "Cisco IOS Software, C2960S Software (C2960S-UNIVERSALK9-M), Version 15.0(2)SE4, RELEASE SOFTWARE (fc1)"
             # This parsing is basic and might need refinement for different IOS versions
            parts = version_output.split(',')
            if len(parts) > 2:
                self.context['os_version'] = parts[2].replace(" Version ", "").strip()
        # Add more Cisco-specific commands (e.g., show ip interface brief, show ip route)
        self.context['interfaces'] = self._parse_cisco_interfaces()
        self.device_connector.execute_command("terminal no length") # Reset terminal length

    def _parse_cisco_interfaces(self):
        """Parses 'show ip interface brief' output."""
        output = self.device_connector.execute_command("show ip interface brief")
        interfaces = {}
        if output:
            lines = output.splitlines()
            for line in lines:
                # Example line: "GigabitEthernet0/0    192.168.1.1     YES manual up                    up      "
                parts = line.split()
                if len(parts) >= 6 and ("Interface" not in parts[0]): # Basic check for valid interface line
                    iface_name = parts[0]
                    ip_address = parts[1]
                    status = parts[-2] # Second to last element for line status
                    protocol_status = parts[-1] # Last element for protocol status
                    interfaces[iface_name] = {
                        'ip_address': ip_address if ip_address != "unassigned" else None,
                        'status': status, # This will be "down" for "administratively down"
                        'protocol': protocol_status
                    }
        return interfaces

    def _gather_paloalto_panos_context(self):
        """Gathers context specific to Palo Alto PAN-OS devices (CLI via SSH)."""
        self.context['os_type'] = 'paloalto_panos'
        self.context['hostname'] = self.device_connector.execute_command("show system info | match hostname").split(":")[-1].strip()
        self.context['os_version'] = self.device_connector.execute_command("show system info | match sw-version").split(":")[-1].strip()
        print("Palo Alto context gathering is a placeholder. Requires specific PAN-OS commands or API integration.")

    def get_context_json(self):
        """Returns the gathered context as a JSON string."""
        return json.dumps(self.context, indent=4)

if __name__ == '__main__':
    print("ContextBuilder module placeholder execution.")
