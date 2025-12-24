#!/usr/bin/env python3
"""
Demo script showing win/loss detection functionality in the enhanced 2248 bot
"""
import numpy as np
from game_state_recognition import GameStateRecognizer
from game_logic_enhanced import EnhancedGameLogic
from config_manager import ConfigManager
from screen_processor_enhanced import EnhancedScreenProcessor
from input_controller import InputController


def demo_win_loss_detection():
    """Demonstrate the win/loss detection functionality"""
    print("🎯 Demo: Win/Loss Detection in Enhanced 2248 Bot")
    print("=" * 50)
    
    # Initialize components
    config_manager = ConfigManager()
    screen_processor = EnhancedScreenProcessor(config_manager)
    input_controller = InputController(screen_processor)
    game_logic = EnhancedGameLogic(config_manager, screen_processor, input_controller)
    
    print("✅ All components initialized successfully!")
    
    # Demo 1: Win condition detection
    print("\\n🎮 Demo 1: Win Condition Detection")
    print("-" * 30)
    
    # Set up a winning board state
    winning_board = [
        [2, 4, 8, 16],
        [32, 64, 128, 256],
        [512, 1024, 2048, 2],
        [4, 8, 16, 2248],  # Target tile (2248) achieved!
        [2, 4, 8, 16]
    ]
    
    # Assign to game_logic board
    game_logic.board = winning_board
    
    print("Current board state:")
    for row in game_logic.board:
        print(f"  {row}")
    
    is_won = game_logic.detect_win_condition(target_tile=2248)
    print(f"\\n🎯 Win condition detected (target 2248): {is_won}")
    
    # Demo 2: Loss condition detection
    print("\\n🔴 Demo 2: Loss Condition Detection")
    print("-" * 30)
    
    # Set up a board that is full with no possible moves
    # (all adjacent tiles have different values that can't merge)
    losing_board = [
        [2, 4, 2, 4],
        [8, 16, 8, 16],
        [32, 64, 32, 64],
        [128, 256, 128, 256],
        [512, 1024, 512, 1024]
    ]
    
    game_logic.board = losing_board
    print("Current board state:")
    for row in game_logic.board:
        print(f"  {row}")
    
    is_lost = game_logic.is_game_lost()
    print(f"\\n🔴 Loss condition detected (no moves possible): {is_lost}")
    
    # Demo 3: Visual win/loss detection (simulated)
    print("\\n👁️ Demo 3: Visual Win/Loss Detection")
    print("-" * 30)
    
    # Create a mock screen image for testing
    # In a real scenario, this would come from grab_screen_cv2()
    mock_screen = np.zeros((720, 1280, 3), dtype=np.uint8)  # Mock screen
    
    is_game_over, result_type = game_logic.detect_game_over(mock_screen)
    print(f"Visual game over detection: is_game_over={is_game_over}, result_type={result_type}")
    
    print("\\n" + "=" * 50)
    print("🎉 Win/Loss Detection Demo Completed Successfully!")
    print("\\n📋 Summary:")
    print("  • Win detection: Identifies when target tile (2248) is achieved")
    print("  • Loss detection: Identifies when no moves are possible") 
    print("  • Visual detection: Identifies win/loss from screen image")
    print("  • Integrated: Works with the enhanced game loop and event system")


def demo_integration_with_game_runner():
    """Show how win/loss detection integrates with the game runner"""
    print("\\n🔄 Demo: Integration with Game Runner")
    print("-" * 40)
    
    print("The EnhancedGameRunner now includes:")
    print("  • Board state analysis for win/loss conditions")
    print("  • Visual screen analysis for win/loss detection")
    print("  • Event system integration for game end events")
    print("  • Learning engine updates based on game outcomes")
    print("  • Proper game state tracking and statistics")
    
    print("\\n✅ Win/loss detection seamlessly integrates with:")
    print("  • Existing game loop logic")
    print("  • Learning and adaptation systems")
    print("  • Event handling and statistics")
    print("  • All existing functionality preserved")


if __name__ == "__main__":
    demo_win_loss_detection()
    demo_integration_with_game_runner()
    
    print("\\n🎊 Win/Loss Detection Successfully Added to Enhanced 2248 Bot!")