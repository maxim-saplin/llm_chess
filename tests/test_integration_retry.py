#!/usr/bin/env python3
"""
Integration test for retry logic in the actual game context.
"""

import unittest
import time
from unittest.mock import patch
from custom_agents import GameAgent, is_retryable_error
import llm_chess


class TestRetryIntegration(unittest.TestCase):
    """Integration test for retry logic in the chess game context."""
    
    def test_retry_logic_in_game_agent_creation(self):
        """Test that GameAgent instances are created with correct retry parameters."""
        # Test with default values from llm_chess configuration
        agent = GameAgent(
            name="TestPlayer",
            max_retries=llm_chess.max_api_retries,
            retry_delay=llm_chess.api_retry_delay
        )
        
        self.assertEqual(agent.max_retries, 3)  # Default value
        self.assertEqual(agent.retry_delay, 2.0)  # Default value
    
    def test_is_retryable_error_with_real_exception_structure(self):
        """Test the is_retryable_error function with error messages only."""
        
        # Test retryable error messages
        class GenericError(Exception):
            pass
        
        # Test retryable messages
        retryable_error1 = GenericError("Service is not available")
        self.assertTrue(is_retryable_error(retryable_error1))
        
        retryable_error2 = GenericError("The service is not available at this time")
        self.assertTrue(is_retryable_error(retryable_error2))
        
        retryable_error3 = GenericError("Rate limit exceeded")
        self.assertTrue(is_retryable_error(retryable_error3))
        
        retryable_error4 = GenericError("Connection error occurred")
        self.assertTrue(is_retryable_error(retryable_error4))
        
        retryable_error5 = GenericError("Service is currently over capacity")
        self.assertTrue(is_retryable_error(retryable_error5))
        
        # Test that "internal server error" is NOT retryable (commented out)
        non_retryable_error1 = GenericError("Internal server error occurred")
        self.assertFalse(is_retryable_error(non_retryable_error1))
        
        # Test other non-retryable errors
        non_retryable_error2 = GenericError("Invalid API key provided")
        self.assertFalse(is_retryable_error(non_retryable_error2))
        
        # Test invalid tool call error (should not be retryable)
        invalid_tool_call = GenericError("Unexpected tool call: Model tried to call an undeclared function: get_current_board")
        self.assertFalse(is_retryable_error(invalid_tool_call))
    
    def test_game_agent_retry_configuration_from_globals(self):
        """Test that GameAgent uses the global retry configuration correctly."""
        
        # Temporarily modify global config
        original_max_retries = llm_chess.max_api_retries
        original_retry_delay = llm_chess.api_retry_delay
        
        try:
            # Set custom values
            llm_chess.max_api_retries = 5
            llm_chess.api_retry_delay = 1.5
            
            # Create agent using the global configuration
            agent = GameAgent(
                name="TestPlayer",
                max_retries=llm_chess.max_api_retries,
                retry_delay=llm_chess.api_retry_delay
            )
            
            self.assertEqual(agent.max_retries, 5)
            self.assertEqual(agent.retry_delay, 1.5)
            
        finally:
            # Restore original values
            llm_chess.max_api_retries = original_max_retries
            llm_chess.api_retry_delay = original_retry_delay
    
    def test_retry_logic_preserves_game_state(self):
        """Test that retry logic doesn't interfere with game state tracking."""
        agent = GameAgent(
            name="TestPlayer",
            max_retries=2,
            retry_delay=0.01  # Very short for testing
        )
        
        # Initialize game state tracking attributes
        agent.prep_to_move()
        
        # Verify initial state
        self.assertFalse(agent.has_requested_board)
        self.assertEqual(agent.failed_action_attempts, 0)
        self.assertEqual(agent.accumulated_reply_time_seconds, 0.0)
        
        # Mock an API error followed by success (message-based retry check)
        class MockAPIError(Exception):
            def __init__(self, message="Service is not available"):
                super().__init__(message)
        
        call_count = 0
        def mock_generate_reply(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            time.sleep(0.001)  # Minimal processing time
            if call_count == 1:
                raise MockAPIError("Service is not available")
            return "Test response"
        
        with patch.object(agent.__class__.__bases__[0], 'generate_reply', side_effect=mock_generate_reply):
            with patch('builtins.print'):  # Suppress output
                result = agent.generate_reply(messages=[{"content": "test"}])
                
                # Verify the retry worked
                self.assertEqual(result, "Test response")
                self.assertEqual(call_count, 2)
                
                # Verify game state is preserved
                self.assertFalse(agent.has_requested_board)  # Should remain unchanged
                self.assertEqual(agent.failed_action_attempts, 0)  # Should remain unchanged
                self.assertGreater(agent.accumulated_reply_time_seconds, 0)  # Should have accumulated time


if __name__ == '__main__':
    unittest.main() 