#!/usr/bin/env python3
"""
Test script for win/loss detection functionality in the enhanced 2248 bot
"""
import numpy as np
from game_state_recognition import GameStateRecognizer
from game_logic_enhanced import EnhancedGameLogic
from config_manager import ConfigManager
from screen_processor_enhanced import EnhancedScreenProcessor
from input_controller import InputController


def test_game_state_recognition():
    """Test the game state recognition functionality"""
    print("🧪 Testing Game State Recognition...")
    
    # Initialize the recognizer
    recognizer = GameStateRecognizer()
    
    # Test win condition detection with a sample board
    # Create a test board with a winning tile (2248 or higher)
    test_board_win = [
        [2, 4, 8, 16],
        [32, 64, 128, 256],
        [512, 1024, 2048, 2], 
        [4, 8, 16, 2248]  # Contains the target tile
    ]
    
    # Test win detection
    is_win = recognizer.detect_win_condition(test_board_win, target_tile=2248)
    print(f"   Win detection test: {is_win} (expected: True)")
    
    # Test with a non-winning board
    test_board_no_win = [
        [2, 4, 8, 16],
        [32, 64, 128, 256], 
        [512, 1024, 2048, 2],
        [4, 8, 16, 32]  # No 2248 tile
    ]
    
    is_win2 = recognizer.detect_win_condition(test_board_no_win, target_tile=2248)
    print(f"   Non-win detection test: {is_win2} (expected: False)")
    
    print("✅ Game State Recognition tests completed")


def test_enhanced_game_logic_with_detection():
    """Test the enhanced game logic with win/loss detection"""
    print("\\n🧪 Testing Enhanced Game Logic with Win/Loss Detection...")
    
    # Initialize components (using minimal setup for testing)
    config_manager = ConfigManager()
    screen_processor = EnhancedScreenProcessor(config_manager)
    # Pass screen_processor to InputController as required
    input_controller = InputController(screen_processor)
    
    # Create enhanced game logic instance
    game_logic = EnhancedGameLogic(config_manager, screen_processor, input_controller)
    
    # Test win condition detection
    # Set up a board that should trigger a win (using 5x4 board as per constants)
    game_logic.board = [
        [2, 4, 8, 16],
        [32, 64, 128, 256],
        [512, 1024, 2048, 2],
        [4, 8, 16, 2248],  # Contains target tile
        [2, 4, 8, 16]
    ]
    
    is_won = game_logic.detect_win_condition(target_tile=2248)
    print(f"   Enhanced logic win detection: {is_won} (expected: True)")
    
    # Test loss condition detection
    # Set up a board that is full with no possible moves
    game_logic.board = [
        [2, 4, 8, 16],
        [64, 32, 128, 8],
        [256, 512, 64, 1024],
        [2048, 128, 4096, 32],
        [2, 4, 8, 16]
    ]
    
    # This should not be a loss yet (no adjacent equal tiles)
    is_lost = game_logic.is_game_lost()
    print(f"   Loss detection (no possible moves): {is_lost}")
    
    # Set up a board that is full with possible moves
    game_logic.board = [
        [2, 4, 2, 4],
        [4, 2, 4, 2], 
        [2, 4, 2, 4],
        [4, 2, 4, 2],
        [2, 4, 2, 4]
    ]
    
    is_lost2 = game_logic.is_game_lost()
    print(f"   Loss detection (possible moves exist): {is_lost2} (expected: False)")
    
    print("✅ Enhanced Game Logic tests completed")


def simulate_game_loop_detection():
    """Simulate how win/loss detection would work in the game loop"""
    print("\\n🎮 Simulating Game Loop with Win/Loss Detection...")
    
    # Initialize components
    config_manager = ConfigManager()
    screen_processor = EnhancedScreenProcessor(config_manager)
    # Pass screen_processor to InputController as required
    input_controller = InputController(screen_processor)
    
    game_logic = EnhancedGameLogic(config_manager, screen_processor, input_controller)
    
    # Simulate a game progression
    print("   Simulating game progression...")
    
    # Initial board state
    game_logic.board = [
        [2, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0], 
        [0, 0, 0, 2]
    ]
    
    print("   Initial board - checking win/loss conditions:")
    print(f"   - Is game won: {game_logic.detect_win_condition()}")
    print(f"   - Is game lost: {game_logic.is_game_lost()}")
    
    # Simulate a winning board
    game_logic.board = [
        [2, 4, 8, 16],
        [32, 64, 128, 256],
        [512, 1024, 2048, 2],
        [4, 8, 16, 2248]  # Win condition met
    ]
    
    print("\\n   Winning board - checking win/loss conditions:")
    is_won = game_logic.detect_win_condition()
    is_lost = game_logic.is_game_lost()
    print(f"   - Is game won: {is_won} (expected: True)")
    print(f"   - Is game lost: {is_lost}")
    
    print("✅ Game loop simulation completed")


def main():
    """Main test function"""
    print("🎯 Testing Win/Loss Detection in Enhanced 2248 Bot")
    print("=" * 50)
    
    test_game_state_recognition()
    test_enhanced_game_logic_with_detection()
    simulate_game_loop_detection()
    
    print("\\n" + "=" * 50)
    print("🎉 All win/loss detection tests completed!")


if __name__ == "__main__":
    main()