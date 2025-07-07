import unittest
import logging
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.ai_agent.utils.logger import get_logger, log_interaction, LOG_DIR

class TestLogger(unittest.TestCase):

    def setUp(self):
        self.test_log_files = []
        # Ensure LOG_DIR exists for tests that might create files
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)

    def tearDown(self):
        # Clean up any log files created during tests
        # Ensure handlers are closed before attempting to remove files
        # Get all loggers that might have file handlers
        loggers_to_check = [logging.getLogger(name) for name in list(logging.Logger.manager.loggerDict.keys())]
        loggers_to_check.append(logging.getLogger()) # include root logger

        for logger_instance in loggers_to_check:
            for handler in list(logger_instance.handlers): # Iterate over a copy
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    logger_instance.removeHandler(handler) # Remove handler to release file
                    # Add to cleanup list if not already explicitly added by test
                    if handler.baseFilename not in self.test_log_files:
                         # Check if it's in LOG_DIR to avoid deleting unrelated files
                        if os.path.dirname(handler.baseFilename) == os.path.abspath(LOG_DIR):
                            self.test_log_files.append(handler.baseFilename)

        for log_file_path in self.test_log_files:
            if os.path.exists(log_file_path):
                try:
                    os.remove(log_file_path)
                except Exception as e:
                    print(f"Warning: Could not remove test log file {log_file_path}: {e}")

        # Reset logging states by removing handlers from known test loggers
        # This is crucial because get_logger has `if not logger.handlers:`
        # This should now be handled by removing handlers above.
        # Forcing re-creation of loggers might be more robust if issues persist.
        # logging.shutdown() # This closes handlers but doesn't clear logger.handlers list for existing loggers


    @patch('src.ai_agent.utils.logger.datetime') # Patch datetime class in logger's namespace
    def test_get_logger_creates_file_handler_with_timestamp(self, mock_datetime_class):
        fixed_timestamp = "20230101_120000"
        # mock_datetime_class is now the mocked datetime type in logger.py
        # We configure its 'now' method, which returns a datetime-like object,
        # and that object's 'strftime' method.
        mock_datetime_class.now.return_value.strftime.return_value = fixed_timestamp

        logger_name = "TestLoggerFileCreation_UniqueForTimestampTest" # Unique name
        # Ensure this logger is fresh for the test of handler creation logic
        if logger_name in logging.Logger.manager.loggerDict:
            # If this unique logger somehow exists, clear its handlers to ensure full setup
            existing_logger = logging.getLogger(logger_name)
            for h in list(existing_logger.handlers): # Iterate over a copy
                h.close()
                existing_logger.removeHandler(h)
            # Optionally, del logging.Logger.manager.loggerDict[logger_name] if still problematic

        logger = get_logger(logger_name) # This will now create a new logger instance

        # FileHandler creates absolute path, so make expected path absolute too
        expected_log_file = os.path.abspath(os.path.join(LOG_DIR, f"ai_agent_{fixed_timestamp}.log"))
        # self.test_log_files.append(expected_log_file) # Will be added by teardown's handler scan

        file_handler_exists = False
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                self.assertEqual(handler.baseFilename, expected_log_file)
                file_handler_exists = True
                # Ensure formatter has the expected fields
                self.assertIn("device_id", handler.formatter._fmt)
                self.assertIn("prompt", handler.formatter._fmt)
                self.assertIn("command", handler.formatter._fmt)
                self.assertIn("response", handler.formatter._fmt)
                break
        self.assertTrue(file_handler_exists, "FileHandler not found or not configured correctly.")

    def test_get_logger_properties(self):
        logger = get_logger("TestLoggerProps")
        self.assertEqual(logger.name, "TestLoggerProps")
        self.assertEqual(logger.level, logging.INFO) # Default level set in get_logger
        self.assertTrue(any(isinstance(h, logging.StreamHandler) for h in logger.handlers))
        self.assertTrue(any(isinstance(h, logging.FileHandler) for h in logger.handlers))

        # Store the actual log file created by this test for cleanup
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                self.test_log_files.append(handler.baseFilename)
                break


    def test_get_logger_singleton_behavior(self):
        logger1 = get_logger("SingletonTest")
        logger2 = get_logger("SingletonTest")
        self.assertIs(logger1, logger2)
        self.assertEqual(len(logger1.handlers), 2) # Should not add handlers again

        for handler in logger1.handlers:
            if isinstance(handler, logging.FileHandler):
                self.test_log_files.append(handler.baseFilename)
                break # Only need one file path for cleanup


    @patch('src.ai_agent.utils.logger.datetime')
    def test_log_interaction(self, mock_datetime):
        fixed_timestamp = "20230101_120001" # Use a different timestamp
        mock_now = MagicMock()
        mock_now.strftime.return_value = fixed_timestamp
        mock_datetime.now.return_value = mock_now

        logger = get_logger("InteractionLogger")

        # Find the file handler to read its output
        file_handler = None
        for h in logger.handlers:
            if isinstance(h, logging.FileHandler):
                file_handler = h
                break
        self.assertIsNotNone(file_handler, "File handler not found for InteractionLogger")

        log_file_path = file_handler.baseFilename
        self.test_log_files.append(log_file_path)


        # Capture log output to the file handler stream (requires a bit of setup)
        # For simplicity, we'll close the default one and add a new one to a known temp file
        # Or, we can check if the file was written to after the call.

        # Test data
        device_id = "dev-001"
        user_prompt = "show version"
        llm_cmds = "show version"
        exec_cmds = "show version"
        dev_output = "Cisco IOS Software..."
        status = True

        log_interaction(logger, device_id, user_prompt, llm_cmds, exec_cmds, dev_output, status)

        # Close handler to flush
        file_handler.close()

        # Verify log file content
        self.assertTrue(os.path.exists(log_file_path))
        with open(log_file_path, 'r') as f:
            log_content = f.read()

        self.assertIn(f"DeviceID: {device_id}", log_content)
        self.assertIn(f"Prompt: {user_prompt}", log_content)
        self.assertIn(f"Command: {exec_cmds}", log_content) # 'command' in formatter
        self.assertIn(f"Response: {dev_output}", log_content) # 'response' in formatter
        self.assertIn("Status: SUCCESS", log_content) # Derived from msg_for_log
        self.assertIn(f"Interaction Summary - Device: {device_id}", log_content) # The 'message' part


    @patch('src.ai_agent.utils.logger.datetime')
    def test_log_interaction_failure(self, mock_datetime):
        fixed_timestamp = "20230101_120002"
        mock_now = MagicMock()
        mock_now.strftime.return_value = fixed_timestamp
        mock_datetime.now.return_value = mock_now

        logger = get_logger("InteractionFailureLogger")
        file_handler = next((h for h in logger.handlers if isinstance(h, logging.FileHandler)), None)
        self.assertIsNotNone(file_handler)
        log_file_path = file_handler.baseFilename
        self.test_log_files.append(log_file_path)

        log_interaction(logger, "dev-002", "bad prompt", "bad cmd", "bad cmd", "Error output", False)
        file_handler.close()

        with open(log_file_path, 'r') as f:
            log_content = f.read()
        self.assertIn("Status: FAILURE", log_content)

    def test_logger_level_filtering(self):
        # This test is more about standard logging behavior but good to confirm
        # For this, we need to capture stream output

        # Ensure this logger is fresh and set its level to DEBUG for this test
        logger_name = "LevelFilterLogger"
        if logger_name in logging.Logger.manager.loggerDict:
            # Clean up existing handlers if any, to ensure fresh setup by get_logger
            existing_logger = logging.getLogger(logger_name)
            for h in list(existing_logger.handlers):
                h.close()
                existing_logger.removeHandler(h)
            # It might be necessary to delete the logger instance itself from manager
            # if get_logger's `if not logger.handlers` is too simplistic for re-configuration
            # For now, just ensuring it's clean for the next get_logger call.
            # A better get_logger might accept a `force_reconfigure=True` or similar.

        logger = get_logger(logger_name, level=logging.DEBUG) # Explicitly set logger level to DEBUG

        # Find the file handler and its path for cleanup
        file_handler = next((h for h in logger.handlers if isinstance(h, logging.FileHandler)), None)
        if file_handler:
            self.test_log_files.append(file_handler.baseFilename)

        # Use a mock stream for the console handler to check what gets printed
        mock_stream = MagicMock()
        mock_stream.write = MagicMock()

        # Replace console handler's stream
        console_handler = next((h for h in logger.handlers if isinstance(h, logging.StreamHandler)), None)
        self.assertIsNotNone(console_handler)
        original_stream = console_handler.stream
        console_handler.stream = mock_stream

        # Log messages
        logger.debug("This is a debug message.") # Should not appear in INFO level file, but on DEBUG console
        logger.info("This is an info message.")   # Should appear in both
        logger.warning("This is a warning message.") # Should appear in both

        # Check console output (StreamHandler is DEBUG level)
        console_output = "".join(call_args[0][0] for call_args in mock_stream.write.call_args_list)
        self.assertIn("This is a debug message.", console_output)
        self.assertIn("This is an info message.", console_output)
        self.assertIn("This is a warning message.", console_output)

        # Check file output (FileHandler is INFO level)
        if file_handler:
            file_handler.close() # Flush
            with open(file_handler.baseFilename, 'r') as f:
                file_content = f.read()
            self.assertNotIn("This is a debug message.", file_content)
            self.assertIn("This is an info message.", file_content)
            self.assertIn("This is a warning message.", file_content)

        # Restore original stream
        console_handler.stream = original_stream


if __name__ == '__main__':
    unittest.main()
