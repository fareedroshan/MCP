import unittest
from unittest.mock import MagicMock, patch
import json

from src.ai_agent.context.context_builder import ContextBuilder
# Assuming DeviceConnector is in src.ai_agent.connectors.device_connector
from src.ai_agent.connectors.device_connector import DeviceConnector


class TestContextBuilder(unittest.TestCase):

    def setUp(self):
        # Mock DeviceConnector
        self.mock_connector = MagicMock(spec=DeviceConnector)
        self.mock_connector.client = MagicMock() # Simulate a connected client
        self.builder = ContextBuilder(self.mock_connector)

    def test_gather_context_not_connected(self):
        self.mock_connector.client = None # Simulate not connected
        context = self.builder.gather_context("linux")
        self.assertIsNone(context)

    def test_gather_context_unsupported_os(self):
        context = self.builder.gather_context("windows")
        self.assertIsNone(context)
        self.assertEqual(self.builder.context, {}) # Context should remain empty

    @patch.object(ContextBuilder, '_gather_linux_context')
    def test_gather_context_linux_delegation(self, mock_gather_linux):
        self.builder.gather_context("linux")
        mock_gather_linux.assert_called_once()

    @patch.object(ContextBuilder, '_gather_cisco_ios_context')
    def test_gather_context_cisco_ios_delegation(self, mock_gather_cisco):
        self.builder.gather_context("cisco_ios")
        mock_gather_cisco.assert_called_once()

    @patch.object(ContextBuilder, '_gather_paloalto_panos_context')
    def test_gather_context_paloalto_delegation(self, mock_gather_palo):
        self.builder.gather_context("paloalto_panos")
        mock_gather_palo.assert_called_once()

    def test_gather_linux_context_commands(self):
        # Define return values for commands executed by DeviceConnector
        command_map = {
            "hostname": "test-linux-host\n",
            "cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"'": "Ubuntu 22.04 LTS\n",
            "ip addr": (
                "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000\n"
                "    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00\n"
                "    inet 127.0.0.1/8 scope host lo\n"
                "       valid_lft forever preferred_lft forever\n"
                "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000\n"
                "    link/ether 00:11:22:33:44:55 brd ff:ff:ff:ff:ff:ff\n"
                "    inet 192.168.1.100/24 brd 192.168.1.255 scope global dynamic eth0\n"
                "       valid_lft 86352sec preferred_lft 86352sec\n"
                "    inet6 fe80::211:22ff:fe33:4455/64 scope link \n"
                "       valid_lft forever preferred_lft forever\n"
                "3: docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default \n"
                "    link/ether 02:42:ac:11:00:02 brd ff:ff:ff:ff:ff:ff\n"
                "    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0\n"
                "       valid_lft forever preferred_lft forever"
            )
        }
        self.mock_connector.execute_command.side_effect = lambda cmd: command_map.get(cmd, "")

        self.builder._gather_linux_context()

        self.assertEqual(self.builder.context['os_type'], 'linux')
        self.assertEqual(self.builder.context['hostname'], 'test-linux-host')
        self.assertEqual(self.builder.context['os_version'], 'Ubuntu 22.04 LTS')
        self.assertIn('eth0', self.builder.context['interfaces'])
        self.assertEqual(self.builder.context['interfaces']['eth0']['ip_address'], '192.168.1.100/24')
        self.assertEqual(self.builder.context['interfaces']['eth0']['status'], 'UP')
        self.assertIn('docker0', self.builder.context['interfaces']) # Check another interface
        self.assertEqual(self.builder.context['interfaces']['docker0']['status'], 'DOWN')
        self.assertNotIn('lo', self.builder.context['interfaces']) # Loopback should be excluded by current logic

    def test_gather_cisco_ios_context_commands(self):
        command_map = {
            "terminal length 0": "", # No output expected to be parsed
            "show running-config | include hostname": "hostname Router1\n",
            "show version | include Cisco IOS Software": "Cisco IOS Software, C2960S Software (C2960S-UNIVERSALK9-M), Version 15.0(2)SE4, RELEASE SOFTWARE (fc1)\n",
            "show ip interface brief": (
                "Interface              IP-Address      OK? Method Status                Protocol\n"
                "GigabitEthernet0/0     192.168.1.1     YES manual up                    up      \n"
                "GigabitEthernet0/1     unassigned      YES unset  administratively down down    \n"
                "Vlan1                  10.0.0.1        YES manual up                    up      \n"
            ),
            "terminal no length": "" # No output expected
        }
        self.mock_connector.execute_command.side_effect = lambda cmd: command_map.get(cmd, "")

        self.builder._gather_cisco_ios_context()

        self.assertEqual(self.builder.context['os_type'], 'cisco_ios')
        self.assertEqual(self.builder.context['hostname'], 'Router1')
        self.assertEqual(self.builder.context['os_version'], '15.0(2)SE4') # Based on current parsing
        self.assertIn('GigabitEthernet0/0', self.builder.context['interfaces'])
        self.assertEqual(self.builder.context['interfaces']['GigabitEthernet0/0']['ip_address'], '192.168.1.1')
        self.assertEqual(self.builder.context['interfaces']['GigabitEthernet0/0']['status'], 'up')
        self.assertEqual(self.builder.context['interfaces']['GigabitEthernet0/0']['protocol'], 'up')
        self.assertIn('GigabitEthernet0/1', self.builder.context['interfaces'])
        self.assertIsNone(self.builder.context['interfaces']['GigabitEthernet0/1']['ip_address'])
        self.assertEqual(self.builder.context['interfaces']['GigabitEthernet0/1']['status'], 'down') # Current parser gets 'down'
        self.assertEqual(self.builder.context['interfaces']['GigabitEthernet0/1']['protocol'], 'down')

    def test_gather_paloalto_panos_context_placeholder(self):
        # This tests the placeholder nature
        command_map = {
            "show system info | match hostname": "hostname: PA-VM-1\n",
            "show system info | match sw-version": "sw-version: 10.1.0\n"
        }
        self.mock_connector.execute_command.side_effect = lambda cmd: command_map.get(cmd, "")

        self.builder._gather_paloalto_panos_context()
        self.assertEqual(self.builder.context['os_type'], 'paloalto_panos')
        self.assertEqual(self.builder.context['hostname'], 'PA-VM-1')
        self.assertEqual(self.builder.context['os_version'], '10.1.0')
        # Add more assertions if the placeholder gets more features

    def test_get_context_json(self):
        self.builder.context = {"test_key": "test_value", "number": 123}
        json_output = self.builder.get_context_json()
        expected_json = json.dumps({"test_key": "test_value", "number": 123}, indent=4)
        self.assertEqual(json_output, expected_json)

    def test_parse_cisco_interfaces_empty_output(self):
        self.mock_connector.execute_command.return_value = "" # Empty output for "show ip interface brief"
        interfaces = self.builder._parse_cisco_interfaces()
        self.assertEqual(interfaces, {})

    def test_parse_cisco_interfaces_header_only(self):
        self.mock_connector.execute_command.return_value = "Interface              IP-Address      OK? Method Status                Protocol\n"
        interfaces = self.builder._parse_cisco_interfaces()
        self.assertEqual(interfaces, {})

    def test_parse_linux_interfaces_empty_output(self):
        self.mock_connector.execute_command.return_value = "" # Empty output for "ip addr"
        interfaces = self.builder._parse_linux_interfaces()
        self.assertEqual(interfaces, {})

if __name__ == '__main__':
    unittest.main()
