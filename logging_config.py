"""
Enhanced logging configuration for Pokemon battle bots.
Reduces verbosity and provides structured logging for battle analysis.
"""

import logging
import sys
import re

class WebsocketLogFilter(logging.Filter):
    """Enhanced filter to reduce websocket verbosity and format logs better."""
    
    def __init__(self):
        super().__init__()
        # Patterns to filter out
        self.noise_patterns = [
            r'\[92m.*<<<.*\[0m',  # Incoming websocket messages with color codes
            r'\[93m.*>>>.*\[0m',  # Outgoing websocket messages with color codes
            r'\|updateuser\|',     # User update messages
            r'\|challstr\|',       # Challenge string messages
            r'\|formats\|',        # Format list messages
            r'\|customgroups\|',   # Custom groups messages
            r'\|updatesearch\|',   # Search update messages
            r'Starting listening to showdown websocket',  # Connection messages
            r'Bypassing authentication request',  # Auth bypass messages
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern) for pattern in self.noise_patterns]
    
    def filter(self, record):
        """Filter out noisy websocket traffic."""
        message = record.getMessage()
        
        # Check if message matches any noise pattern
        for pattern in self.compiled_patterns:
            if pattern.search(message):
                return False
        
        return True

class BattleLogFormatter(logging.Formatter):
    """Custom formatter for structured battle logging."""
    
    def format(self, record):
        # Add structured prefixes for battle-related logs
        if hasattr(record, 'battle_id') and hasattr(record, 'bot_name'):
            # Battle-specific logs
            record.msg = f"[{record.bot_name}@{record.battle_id}] {record.msg}"
        elif hasattr(record, 'bot_name'):
            # Bot-specific logs
            record.msg = f"[{record.bot_name}] {record.msg}"
        elif hasattr(record, 'battle_id'):
            # Battle-specific logs without bot name
            record.msg = f"[Battle:{record.battle_id}] {record.msg}"
        
        return super().format(record)

def setup_enhanced_logging():
    """Setup enhanced logging configuration."""
    
    # Create custom formatter
    formatter = BattleLogFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create websocket filter
    websocket_filter = WebsocketLogFilter()
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with filtering
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(websocket_filter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    
    # Reduce poke_env verbosity significantly
    poke_env_logger = logging.getLogger('poke_env')
    poke_env_logger.setLevel(logging.ERROR)  # Only show errors
    
    # Reduce websocket client verbosity
    websocket_logger = logging.getLogger('websockets')
    websocket_logger.setLevel(logging.WARNING)
    
    # Battle tracker logger
    battle_tracker_logger = logging.getLogger('battle_tracker')
    battle_tracker_logger.setLevel(logging.INFO)
    
    # Bot manager logger
    bot_manager_logger = logging.getLogger('bot_manager')
    bot_manager_logger.setLevel(logging.INFO)
    
    # LLM client logger
    llm_logger = logging.getLogger('llm_client')
    llm_logger.setLevel(logging.INFO)
    
    print("Enhanced logging configuration applied - reduced websocket verbosity")

if __name__ == "__main__":
    setup_enhanced_logging()
    
    # Test the logging
    logger = logging.getLogger(__name__)
    logger.info("Test message - this should appear")
    
    # Test battle-specific logging
    logger.info("Battle decision made", extra={'battle_id': 'test123', 'bot_name': 'TestBot'})