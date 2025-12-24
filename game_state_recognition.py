"""
Module for recognizing game win/loss conditions in the 2248 bot
"""
import numpy as np
from typing import Tuple, Optional
import cv2
import logging

class GameStateRecognizer:
    """
    Recognizes win/loss conditions in the 2248 game
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Define colors for win/loss detection
        self.win_color_range = {
            'lower': np.array([0, 100, 0]),    # Dark green for win text
            'upper': np.array([50, 255, 50])   # Light green for win text
        }
        
        self.loss_color_range = {
            'lower': np.array([0, 0, 100]),    # Red for loss text
            'upper': np.array([50, 50, 255])   # Light red for loss text
        }
        
        # Predefined templates for win/loss detection
        # These would be loaded from image files in a real implementation
        self.win_templates = []
        self.loss_templates = []
        
    def detect_game_over(self, screen_image) -> Tuple[bool, Optional[str]]:
        """
        Detect if the game is over (win or loss)
        
        Args:
            screen_image: Current game screen image
            
        Returns:
            Tuple of (is_game_over, result_type) where result_type is 'win', 'loss', or None
        """
        try:
            # Method 1: Check for win/loss text using color detection
            win_detected = self._detect_win_by_color(screen_image)
            if win_detected:
                return True, 'win'
                
            loss_detected = self._detect_loss_by_color(screen_image)
            if loss_detected:
                return True, 'loss'
                
            # Method 2: Check for game over using board state analysis
            board_full_and_no_moves = self._check_board_full_no_moves(screen_image)
            if board_full_and_no_moves:
                return True, 'loss'
                
            # Method 3: Template matching for win/loss screens
            win_template_match = self._match_win_template(screen_image)
            if win_template_match:
                return True, 'win'
                
            loss_template_match = self._match_loss_template(screen_image)
            if loss_template_match:
                return True, 'loss'
                
            return False, None
            
        except Exception as e:
            self.logger.error(f"Error in game over detection: {e}")
            return False, None
    
    def _detect_win_by_color(self, image) -> bool:
        """
        Detect win condition by looking for win-specific colors/text
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        mask = cv2.inRange(hsv, 
                          self.win_color_range['lower'], 
                          self.win_color_range['upper'])
        
        # Count pixels that match win color
        win_pixels = cv2.countNonZero(mask)
        
        # If we have a significant number of win-colored pixels in expected areas
        height, width = image.shape[:2]
        total_pixels = height * width
        win_ratio = win_pixels / total_pixels if total_pixels > 0 else 0
        
        # Adjust threshold based on typical win screen characteristics
        return win_ratio > 0.01  # 1% of screen showing win color
    
    def _detect_loss_by_color(self, image) -> bool:
        """
        Detect loss condition by looking for loss-specific colors/text
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        mask = cv2.inRange(hsv, 
                          self.loss_color_range['lower'], 
                          self.loss_color_range['upper'])
        
        # Count pixels that match loss color
        loss_pixels = cv2.countNonZero(mask)
        
        height, width = image.shape[:2]
        total_pixels = height * width
        loss_ratio = loss_pixels / total_pixels if total_pixels > 0 else 0
        
        # Adjust threshold based on typical loss screen characteristics
        return loss_ratio > 0.01  # 1% of screen showing loss color
    
    def _check_board_full_no_moves(self, image) -> bool:
        """
        Check if board is full and no moves are possible
        This is a loss condition in 2248
        """
        # This would involve analyzing the game board to see if:
        # 1. All cells are filled
        # 2. No adjacent cells have the same value (no possible moves)
        
        # For a more accurate implementation, we'd need to connect with the board parsing logic
        # For now, we'll implement a basic version that looks for visual indicators
        # that the game board is full and no moves are available
        
        # Look for visual elements that indicate game over (like "Game Over" text)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Look for specific colors that might indicate game over text
        # Using a range that might capture game over text (red, white, etc.)
        game_over_masks = []
        
        # Red color mask (often used for "Game Over" text)
        red_lower1 = np.array([0, 50, 50])
        red_upper1 = np.array([10, 255, 255])
        red_lower2 = np.array([170, 50, 50])
        red_upper2 = np.array([180, 255, 255])
        
        mask_red1 = cv2.inRange(hsv, red_lower1, red_upper1)
        mask_red2 = cv2.inRange(hsv, red_lower2, red_upper2)
        red_mask = cv2.bitwise_or(mask_red1, mask_red2)
        
        # White color mask (often used for text)
        white_lower = np.array([0, 0, 200])
        white_upper = np.array([180, 30, 255])
        white_mask = cv2.inRange(hsv, white_lower, white_upper)
        
        # Combine masks
        combined_mask = cv2.bitwise_or(red_mask, white_mask)
        
        # Find contours that might represent text
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Look for text-like contours in the expected area of the screen
        height, width = image.shape[:2]
        text_area_threshold = height * width * 0.001  # 0.1% of screen area
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > text_area_threshold:  # Large enough to be text
                # Check if it's in the center area where game over text typically appears
                x, y, w, h = cv2.boundingRect(contour)
                center_x, center_y = x + w/2, y + h/2
                
                # If text is in the central upper area of the screen
                if (width * 0.25 < center_x < width * 0.75 and 
                    height * 0.2 < center_y < height * 0.6):
                    return True
        
        return False  # No clear indication of game over found
    
    def _match_win_template(self, image):
        """
        Match against win screen templates
        """
        # Template matching for win screen
        # Would match against known win screen images
        return False  # Placeholder
    
    def _match_loss_template(self, image):
        """
        Match against loss screen templates
        """
        # Template matching for loss screen
        # Would match against known loss screen images
        return False  # Placeholder
    
    def detect_win_condition(self, board_state, target_tile=2248) -> bool:
        """
        Detect win by checking if target tile exists on board
        
        Args:
            board_state: Current board state as 2D array
            target_tile: Target tile value to win (default 2248)
            
        Returns:
            True if win condition is met
        """
        try:
            board_array = np.array(board_state)
            return np.any(board_array >= target_tile)
        except:
            return False