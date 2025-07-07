# Logger Utility
import logging
import os
from datetime import datetime

# Basic logger setup
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# LOG_FILE definition moved into get_logger to use mocked datetime during tests.

def get_logger(name="AI_Agent", level=logging.INFO):
    """
    Configures and returns a logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers: # Avoid adding multiple handlers if logger already exists
        logger.setLevel(level)

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG) # Show debug and above on console
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File Handler - Filename is now dynamic
        # This ensures that datetime.now() is called when get_logger is executed,
        # allowing mocks to take effect during testing.
        # Added logger name to filename for better test isolation if timestamps collide.
        log_file_path = os.path.join(LOG_DIR, f"ai_agent_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.INFO) # Log info and above to file
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - DeviceID: %(device_id)s - Prompt: %(prompt)s - Command: %(command)s - Response: %(response)s - Message: %(message)s',
                                           defaults={"device_id": "N/A", "prompt": "N/A", "command": "N/A", "response": "N/A"})
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger

# Global logger instance for easy import
# agent_logger = get_logger()

def log_interaction(logger_instance, device_id, user_prompt, llm_response_commands, executed_commands, device_output, success_status):
    """
    Custom log function to record a full interaction.
    Uses extra fields in the logger.
    """
    log_entry = {
        "device_id": device_id,
        "prompt": user_prompt,
        "llm_commands": llm_response_commands, # Commands suggested by LLM
        "executed_commands": executed_commands, # Commands actually sent to device
        "device_response": device_output, # Output from device
        "status": "SUCCESS" if success_status else "FAILURE"
    }

    # Construct a readable message for the general log
    # File logger will use the structured format from Formatter
    # Console logger will use its simpler format
    # The 'message' part of the file formatter will get this:
    msg_for_log = (
        f"Interaction Summary - Device: {device_id}, Status: {log_entry['status']}. "
        f"User Prompt: '{user_prompt}'. LLM Commands: '{llm_response_commands}'. Executed: '{executed_commands}'."
    )

    # Log with extra context that the FileHandler's Formatter can use
    # The 'message' field in the Formatter will be replaced by msg_for_log.
    # The other fields like 'device_id', 'prompt' etc. will be picked up from 'extra'.
    logger_instance.info(
        msg_for_log,
        extra={
            "device_id": device_id,
            "prompt": user_prompt,
            "command": executed_commands, # 'command' in formatter
            "response": device_output,    # 'response' in formatter
            # 'message' in formatter is the first arg to logger_instance.info()
        }
    )
    # print(f"Audit Log: {log_entry}") # Also print to console for now or send to audit system


if __name__ == '__main__':
    print("Logger utility placeholder execution.")

    # Example Usage
    main_logger = get_logger("MainAppLogger")
    main_logger.info("This is an info message from MainAppLogger.")
    main_logger.debug("This is a debug message (will appear on console, not by default in file).")
    main_logger.warning("This is a warning message.")

    # Example of logging an interaction
    # This would typically be called from your main orchestrator logic
    test_device_id = "router-01"
    test_user_prompt = "Configure OSPF on interface Gig0/0"
    test_llm_cmds = "router ospf 1\nnetwork 10.0.0.0 0.0.0.255 area 0"
    test_executed_cmds = "configure terminal\nrouter ospf 1\nnetwork 10.0.0.0 0.0.0.255 area 0\nend"
    test_device_output = "Router(config)#router ospf 1\nRouter(config-router)#network 10.0.0.0 0.0.0.255 area 0\nRouter(config-router)#end\nRouter#"
    test_status = True

    print(f"\nLogging a sample interaction to {LOG_FILE} (and console via root logger)...")
    # Use the logger instance obtained by get_logger()
    # The custom log_interaction function is one way to structure it.
    # Alternatively, you can call logger.info with 'extra' kwarg directly.

    # Using the custom log_interaction function:
    log_interaction(
        logger_instance=main_logger,
        device_id=test_device_id,
        user_prompt=test_user_prompt,
        llm_response_commands=test_llm_cmds,
        executed_commands=test_executed_cmds,
        device_output=test_device_output,
        success_status=test_status
    )

    # Direct logging with 'extra' for specific fields in formatter
    main_logger.error(
        "A specific error occurred during device config.",
        extra={
            "device_id": "firewall-02",
            "command": "set rulebase security rules malicious-ips source any destination any action deny",
            "prompt": "Block malicious IPs",
            "response": "Error: rulebase commit failed."
        }
    )
    print(f"\nLog file created at: {LOG_FILE}")
    print("Check the log file and console output for messages.")
