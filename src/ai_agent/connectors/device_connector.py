# Device Connector Module
import paramiko

class DeviceConnector:
    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.client = None

    def connect(self):
        """Establishes an SSH connection to the device."""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(self.hostname, username=self.username, password=self.password)
            print(f"Successfully connected to {self.hostname}")
            return True
        except Exception as e:
            print(f"Failed to connect to {self.hostname}: {e}")
            return False

    def disconnect(self):
        """Closes the SSH connection."""
        if self.client:
            self.client.close()
            print(f"Disconnected from {self.hostname}")

    def execute_command(self, command):
        """Executes a command on the connected device."""
        if not self.client:
            print("Not connected to any device.")
            return None

        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            if error:
                print(f"Error executing command '{command}': {error}")
                return error
            return output
        except Exception as e:
            print(f"Exception while executing command '{command}': {e}")
            return str(e)

if __name__ == '__main__':
    # This is a placeholder for actual device credentials and testing
    # In a real scenario, use a secure way to handle credentials
    print("DeviceConnector module placeholder execution.")
    # Example (requires a running SSH server to test against, replace with your details)
    # connector = DeviceConnector("your_device_ip", "your_username", "your_password")
    # if connector.connect():
    #     output = connector.execute_command("ls -l")
    #     if output:
    #         print("Command output:\n", output)
    #     connector.disconnect()
