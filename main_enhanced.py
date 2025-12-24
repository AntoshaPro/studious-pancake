"""
Enhanced Main Module for the 2248 bot project
Integrates all improved components while preserving the original API
"""
import sys
import time
from pathlib import Path

# Import original components (to preserve API)
from config_manager import ConfigManager
from screen_processor import ScreenProcessor
from game_logic import GameLogic
from input_controller import InputController
from end_game_handler import EndGameHandler
from ad_detector_2248 import EndGameAdDetector2248

# Import enhanced components
from event_system import EventSystem, EventType
from learning_engine import LearningEngine
from game_state_tracker import GameStateTracker
from game_runner_enhanced import EnhancedGameRunner
from game_logic_enhanced import EnhancedGameLogic
from ad_detector_enhanced import EnhancedEndGameAdDetector2248
from screen_processor_enhanced import EnhancedScreenProcessor


class EnhancedMain:
    """Main class that integrates all enhanced components while preserving original API"""
    
    def __init__(self, use_enhanced=True):
        self.use_enhanced = use_enhanced
        
        # Initialize config manager (original)
        self.config_manager = ConfigManager()
        
        # Initialize components based on mode
        if use_enhanced:
            # Use enhanced components
            self.screen_processor = EnhancedScreenProcessor(self.config_manager)
            self.game_logic = EnhancedGameLogic(self.config_manager, self.screen_processor, None)
            self.ad_detector = EnhancedEndGameAdDetector2248()
            self.end_handler = EndGameHandler(self.config_manager, self.screen_processor)
        else:
            # Use original components
            self.screen_processor = ScreenProcessor(self.config_manager)
            self.game_logic = GameLogic(self.config_manager, self.screen_processor, None)
            self.ad_detector = EndGameAdDetector2248()
            self.end_handler = EndGameHandler(self.config_manager, self.screen_processor)
        
        # Common components
        self.input_controller = InputController()
        self.event_system = EventSystem()
        self.learning_engine = LearningEngine()
        self.game_state_tracker = GameStateTracker()
        
        # Set up game logic with required components
        self.game_logic.set_ad_detector(self.ad_detector)
        self.game_logic.end_handler = self.end_handler
        
        # Initialize runner
        if use_enhanced:
            self.runner = EnhancedGameRunner(
                self.config_manager,
                self.screen_processor,
                self.game_logic,
                self.end_handler,
                self.input_controller,
                self.ad_detector
            )
        else:
            from game_runner import GameRunner
            self.runner = GameRunner(
                self.config_manager,
                self.screen_processor,
                self.game_logic,
                self.end_handler,
                self.input_controller,
                self.ad_detector
            )
        
        # Subscribe to events for logging
        self.event_system.subscribe(EventType.GAME_START, self._on_game_start)
        self.event_system.subscribe(EventType.GAME_END, self._on_game_end)
        self.event_system.subscribe(EventType.AD_DETECTED, self._on_ad_detected)
        self.event_system.subscribe(EventType.ERROR_OCCURRED, self._on_error)
    
    def _on_game_start(self, event):
        """Handle game start event"""
        print(f"[EVENT] Game started at {time.ctime(event.timestamp)}")
    
    def _on_game_end(self, event):
        """Handle game end event"""
        print(f"[EVENT] Game ended with state: {event.data.get('state', 'unknown')}")
        print(f"[EVENT] Final score: {event.data.get('score', 0)}")
    
    def _on_ad_detected(self, event):
        """Handle ad detection event"""
        print(f"[EVENT] Advertisement detected at {time.ctime(event.timestamp)}")
    
    def _on_error(self, event):
        """Handle error event"""
        print(f"[EVENT] Error occurred: {event.data.get('message', 'Unknown error')}")
    
    def run_auto_game(self, max_moves=100):
        """Run auto game with enhanced features"""
        print("🤖 Запуск улучшенной версии 2248 бота")
        print(f"Использую {'enhanced' if self.use_enhanced else 'original'} components")
        
        # Emit start event
        self.event_system.emit_simple(EventType.GAME_START, 
                                   {'use_enhanced': self.use_enhanced, 'timestamp': time.time()})
        
        try:
            # Run the game
            self.runner.run_auto_game(max_moves)
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Остановлено пользователем.")
            self.event_system.emit_simple(EventType.STOP_REQUESTED, 
                                       {'timestamp': time.time()})
        except Exception as e:
            print(f"❌ Ошибка во время игры: {e}")
            self.event_system.emit_simple(EventType.ERROR_OCCURRED, 
                                       {'message': str(e), 'timestamp': time.time()})
        finally:
            # Save all statistics
            self.learning_engine.save_model()
            self.learning_engine.save_episodes()
            self.game_state_tracker.save_stats()
            self.event_system.save_history()
            print("📊 Статистика сохранена.")
    
    def get_learning_stats(self):
        """Get learning statistics"""
        return self.learning_engine.get_learning_stats()
    
    def get_game_stats(self):
        """Get game statistics"""
        return self.game_state_tracker.get_overall_stats()
    
    def get_event_stats(self):
        """Get event system statistics"""
        return self.event_system.get_statistics()
    
    def reset_learning(self):
        """Reset all learning data"""
        self.learning_engine.reset_learning()
        self.game_state_tracker.reset_stats()
        print("🔄 Learning data reset.")


def main():
    """Main function to run the enhanced bot"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced 2248 Bot')
    parser.add_argument('--original', action='store_true', 
                       help='Use original components instead of enhanced ones')
    parser.add_argument('--max-moves', type=int, default=100,
                       help='Maximum number of moves per game')
    parser.add_argument('--stats', action='store_true',
                       help='Show statistics after run')
    
    args = parser.parse_args()
    
    # Create enhanced main instance
    main_bot = EnhancedMain(use_enhanced=not args.original)
    
    # Run the game
    main_bot.run_auto_game(max_moves=args.max_moves)
    
    # Show statistics if requested
    if args.stats:
        print("\n📈 Статистика обучения:")
        learning_stats = main_bot.get_learning_stats()
        for key, value in learning_stats.items():
            print(f"  {key}: {value}")
        
        print("\n📊 Статистика игр:")
        game_stats = main_bot.get_game_stats()
        for key, value in game_stats.items():
            print(f"  {key}: {value}")
        
        print("\n🔔 Статистика событий:")
        event_stats = main_bot.get_event_stats()
        for key, value in event_stats.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()