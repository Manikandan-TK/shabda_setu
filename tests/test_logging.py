"""Unit tests for logging configuration."""

import unittest
import os
import logging
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from config.logging_config import setup_logging

class TestLoggingConfig(unittest.TestCase):
    """Test cases for logging configuration."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for test logs
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        
        # Store original logs directory
        self.original_logs_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data',
            'logs'
        )
    
    def test_setup_logging_creates_directory(self):
        """Test if setup_logging creates the logs directory if it doesn't exist."""
        with patch('config.logging_config.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = self.test_dir
            logger = setup_logging("test_logger")
            
            # Check if logs directory was created
            logs_dir = os.path.join(self.test_dir, 'data', 'logs')
            self.assertTrue(os.path.exists(logs_dir))
    
    def test_logger_name_assignment(self):
        """Test if logger is created with the correct name."""
        logger = setup_logging("test_logger")
        self.assertEqual(logger.name, "test_logger")
        
        # Test default name
        with patch('config.logging_config.__name__', 'default_module'):
            logger = setup_logging()
            self.assertEqual(logger.name, "default_module")
    
    def test_log_file_creation(self):
        """Test if log file is created with correct format."""
        with patch('config.logging_config.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = self.test_dir
            logger = setup_logging("test_logger")
            
            # Get the log file
            logs_dir = os.path.join(self.test_dir, 'data', 'logs')
            log_files = os.listdir(logs_dir)
            
            # Check if exactly one log file was created
            self.assertEqual(len(log_files), 1)
            
            # Check if log file name matches expected format
            log_file = log_files[0]
            self.assertTrue(log_file.startswith("test_logger_"))
            self.assertTrue(log_file.endswith(".log"))
    
    def test_log_handlers_setup(self):
        """Test if both file and console handlers are properly configured."""
        logger = setup_logging("test_logger")
        
        # Check number of handlers
        self.assertEqual(len(logger.handlers), 2)
        
        # Check handler types
        handlers = logger.handlers
        handler_types = [type(h) for h in handlers]
        self.assertIn(logging.handlers.RotatingFileHandler, handler_types)
        self.assertIn(logging.StreamHandler, handler_types)
    
    def test_log_levels(self):
        """Test if log levels are properly set."""
        logger = setup_logging("test_logger")
        
        # Check logger level
        self.assertEqual(logger.level, logging.DEBUG)
        
        # Check handler levels
        file_handler = next(h for h in logger.handlers 
                          if isinstance(h, logging.handlers.RotatingFileHandler))
        console_handler = next(h for h in logger.handlers 
                             if isinstance(h, logging.StreamHandler))
        
        self.assertEqual(file_handler.level, logging.DEBUG)
        self.assertEqual(console_handler.level, logging.INFO)
    
    def test_rotating_file_handler_config(self):
        """Test if RotatingFileHandler is configured with correct parameters."""
        logger = setup_logging("test_logger")
        
        # Get the RotatingFileHandler
        handler = next(h for h in logger.handlers 
                      if isinstance(h, logging.handlers.RotatingFileHandler))
        
        # Check maxBytes and backupCount
        self.assertEqual(handler.maxBytes, 10*1024*1024)  # 10MB
        self.assertEqual(handler.backupCount, 5)
    
    def test_logging_functionality(self):
        """Test if logging actually works at different levels."""
        with patch('config.logging_config.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = self.test_dir
            logger = setup_logging("test_logger")
            
            # Log messages at different levels
            test_message = "Test log message"
            logger.debug(test_message)
            logger.info(test_message)
            logger.warning(test_message)
            logger.error(test_message)
            
            # Check if messages were written to file
            logs_dir = os.path.join(self.test_dir, 'data', 'logs')
            log_file = os.listdir(logs_dir)[0]
            with open(os.path.join(logs_dir, log_file), 'r') as f:
                content = f.read()
                
                # Check if all messages are present
                self.assertIn("DEBUG", content)
                self.assertIn("INFO", content)
                self.assertIn("WARNING", content)
                self.assertIn("ERROR", content)
                self.assertEqual(content.count(test_message), 4)

if __name__ == '__main__':
    unittest.main()
