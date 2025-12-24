"""
Learning Engine for the 2248 bot project
Provides self-learning and strategy adaptation capabilities
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import numpy as np
from scipy import stats
from collections import defaultdict, deque
import pickle


@dataclass
class GameEpisode:
    """Represents a complete game episode for learning purposes"""
    board_states: List[List[List[int]]]  # List of board states during the game
    moves: List[Tuple[int, int]]  # List of moves made (from_pos, to_pos)
    scores: List[int]  # Scores after each move
    final_score: int
    max_tile: int
    duration: float
    timestamp: float
    success: bool  # Whether the game was successful (win or reached high score)


@dataclass
class MoveEvaluation:
    """Represents the evaluation of a specific move"""
    board_hash: int
    move: Tuple[int, int]  # (from_pos, to_pos) or chain representation
    score: float  # Evaluation score
    features: Dict[str, float]  # Features used for evaluation
    timestamp: float
    success: bool  # Whether this move led to a good outcome


class LearningEngine:
    """Learning engine for the 2248 bot that adapts strategy based on game outcomes"""
    
    def __init__(self, model_file: str = "learning_model.pkl", 
                 episodes_file: str = "learning_episodes.json"):
        self.model_file = Path(model_file)
        self.episodes_file = Path(episodes_file)
        
        # Episode history for learning
        self.episodes: List[GameEpisode] = []
        self.episode_buffer = deque(maxlen=100)  # Keep last 100 episodes
        
        # Move evaluations and statistics
        self.move_evaluations: Dict[str, List[MoveEvaluation]] = defaultdict(list)
        self.board_evaluations: Dict[int, Dict[str, Any]] = {}
        
        # Profile selection statistics
        self.profile_stats: Dict[int, Dict[str, float]] = defaultdict(lambda: {
            'games': 0,
            'total_score': 0,
            'wins': 0,
            'avg_duration': 0
        })
        
        # Feature weights for adaptive evaluation
        self.feature_weights: Dict[str, float] = {
            'chain_length': 0.3,
            'potential_merges': 0.25,
            'board_entropy': 0.2,
            'max_tile_position': 0.15,
            'empty_cells': 0.1
        }
        
        # Learning parameters
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.exploration_rate = 0.1
        
        # Load existing data if available
        self.load_model()
        self.load_episodes()
    
    def record_episode(self, episode: GameEpisode):
        """Record a completed game episode for learning"""
        self.episodes.append(episode)
        self.episode_buffer.append(episode)
        
        # Update profile statistics if available
        profile_idx = getattr(episode, 'profile_used', 0)
        self.profile_stats[profile_idx]['games'] += 1
        self.profile_stats[profile_idx]['total_score'] += episode.final_score
        if episode.success:
            self.profile_stats[profile_idx]['wins'] += 1
        self.profile_stats[profile_idx]['avg_duration'] = (
            self.profile_stats[profile_idx]['avg_duration'] * (self.profile_stats[profile_idx]['games'] - 1) + 
            episode.duration
        ) / self.profile_stats[profile_idx]['games']
    
    def evaluate_move(self, board_hash: int, move: Tuple[int, int], 
                     features: Dict[str, float], score: float = 0.0) -> float:
        """Evaluate a move based on current learned weights"""
        # Calculate weighted score based on features
        weighted_score = 0.0
        for feature_name, feature_value in features.items():
            weight = self.feature_weights.get(feature_name, 0.1)
            weighted_score += weight * feature_value
        
        # Store the evaluation for learning
        evaluation = MoveEvaluation(
            board_hash=board_hash,
            move=move,
            score=score,
            features=features,
            timestamp=time.time(),
            success=False  # Will be updated later based on outcome
        )
        
        move_key = f"{board_hash}_{move}"
        self.move_evaluations[move_key].append(evaluation)
        
        return weighted_score
    
    def update_move_success(self, board_hash: int, move: Tuple[int, int], success: bool):
        """Update the success status of a previously recorded move"""
        move_key = f"{board_hash}_{move}"
        if move_key in self.move_evaluations:
            # Update the most recent evaluation
            if self.move_evaluations[move_key]:
                self.move_evaluations[move_key][-1].success = success
    
    def update_feature_weights(self, episode: GameEpisode):
        """Update feature weights based on successful episodes"""
        if not episode.success:
            # If the episode was not successful, slightly reduce weights of moves made
            for i, (board_state, move) in enumerate(zip(episode.board_states, episode.moves)):
                board_hash = self._hash_board(board_state)
                move_key = f"{board_hash}_{move}"
                
                if move_key in self.move_evaluations:
                    # Get the evaluation that corresponds to this move
                    evaluations = self.move_evaluations[move_key]
                    if evaluations:
                        eval_idx = min(i, len(evaluations) - 1)
                        if not evaluations[eval_idx].success:
                            # Reduce weights for features that led to unsuccessful moves
                            for feature_name in evaluations[eval_idx].features:
                                if feature_name in self.feature_weights:
                                    self.feature_weights[feature_name] *= (1 - self.learning_rate * 0.5)
        else:
            # If the episode was successful, increase weights of moves that contributed
            for board_state, move in zip(episode.board_states, episode.moves):
                board_hash = self._hash_board(board_state)
                move_key = f"{board_hash}_{move}"
                
                if move_key in self.move_evaluations:
                    evaluations = self.move_evaluations[move_key]
                    if evaluations and evaluations[-1].success:
                        # Increase weights for features that led to successful moves
                        for feature_name in evaluations[-1].features:
                            if feature_name in self.feature_weights:
                                self.feature_weights[feature_name] *= (1 + self.learning_rate)
        
        # Normalize weights to sum to 1
        total_weight = sum(self.feature_weights.values())
        if total_weight > 0:
            for key in self.feature_weights:
                self.feature_weights[key] /= total_weight
    
    def get_best_profile(self) -> int:
        """Select the best profile based on historical performance"""
        if not self.profile_stats:
            return 0  # Default to first profile
        
        best_profile = 0
        best_score = -float('inf')
        
        for profile_idx, stats in self.profile_stats.items():
            if stats['games'] == 0:
                continue
                
            # Calculate a composite score considering wins, average score, and consistency
            win_rate = stats['wins'] / stats['games']
            avg_score = stats['total_score'] / stats['games']
            
            # Weighted score: 50% win rate, 30% avg score, 20% for stability (inverse of duration)
            profile_score = (0.5 * win_rate + 
                           0.3 * (avg_score / 10000) +  # Normalize score
                           0.2 * (1 / max(stats['avg_duration'], 1)))
            
            if profile_score > best_score:
                best_score = profile_score
                best_profile = profile_idx
        
        return best_profile
    
    def adapt_strategy(self, current_board: List[List[int]], 
                      available_profiles: List[List[int]]) -> List[int]:
        """Adapt the current strategy based on board state and historical performance"""
        # Analyze current board state
        board_features = self._analyze_board_features(current_board)
        
        # Select profile based on current board characteristics and historical performance
        best_profile_idx = self.get_best_profile()
        
        if best_profile_idx < len(available_profiles):
            return available_profiles[best_profile_idx]
        else:
            # Fallback to first profile if index is out of range
            return available_profiles[0]
    
    def _analyze_board_features(self, board: List[List[int]]) -> Dict[str, float]:
        """Analyze features of the current board state"""
        features = {}
        
        # Count empty cells
        empty_cells = sum(1 for row in board for cell in row if cell == 0)
        features['empty_cells'] = empty_cells / (len(board) * len(board[0]))
        
        # Calculate board entropy (measure of randomness)
        values = [cell for row in board for cell in row if cell > 0]
        if values:
            unique_values = set(values)
            entropy = -sum((values.count(v) / len(values)) * 
                          np.log2(values.count(v) / len(values)) 
                          for v in unique_values)
            features['board_entropy'] = entropy / 10  # Normalize
        else:
            features['board_entropy'] = 0
        
        # Position of max tile (prefer corner positions)
        max_val = max(max(row) for row in board)
        max_positions = [(r, c) for r, row in enumerate(board) 
                        for c, val in enumerate(row) if val == max_val]
        
        if max_positions:
            # Check if max tile is in a corner (good for monotonic strategy)
            corner_positions = [(0, 0), (0, 3), (3, 0), (3, 3)]
            is_corner = any(pos in corner_positions for pos in max_positions)
            features['max_tile_position'] = 1.0 if is_corner else 0.3
        
        # Potential merges
        potential_merges = 0
        for r in range(len(board)):
            for c in range(len(board[0])):
                if board[r][c] > 0:
                    # Check right neighbor
                    if c + 1 < len(board[0]) and board[r][c] == board[r][c + 1]:
                        potential_merges += 1
                    # Check bottom neighbor
                    if r + 1 < len(board) and board[r][c] == board[r + 1][c]:
                        potential_merges += 1
        features['potential_merges'] = potential_merges / 20  # Normalize
        
        return features
    
    def _hash_board(self, board: List[List[int]]) -> int:
        """Create a hash for the board state"""
        return hash(tuple(tuple(row) for row in board))
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about the learning process"""
        total_games = sum(stats['games'] for stats in self.profile_stats.values())
        total_wins = sum(stats['wins'] for stats in self.profile_stats.values())
        
        return {
            'total_episodes': len(self.episodes),
            'total_games': total_games,
            'total_wins': total_wins,
            'win_rate': total_wins / total_games if total_games > 0 else 0,
            'profile_stats': dict(self.profile_stats),
            'feature_weights': dict(self.feature_weights),
            'recent_performance': [ep.final_score for ep in list(self.episode_buffer)[-10:]]
        }
    
    def save_model(self):
        """Save the learning model to file"""
        model_data = {
            'feature_weights': self.feature_weights,
            'profile_stats': self.profile_stats,
            'move_evaluations': dict(self.move_evaluations),
            'board_evaluations': self.board_evaluations,
            'learning_rate': self.learning_rate,
            'discount_factor': self.discount_factor,
            'exploration_rate': self.exploration_rate
        }
        
        try:
            with open(self.model_file, 'wb') as f:
                pickle.dump(model_data, f)
        except Exception as e:
            print(f"Error saving learning model: {e}")
    
    def load_model(self):
        """Load the learning model from file"""
        if not self.model_file.exists():
            return
        
        try:
            with open(self.model_file, 'rb') as f:
                model_data = pickle.load(f)
            
            self.feature_weights = model_data.get('feature_weights', self.feature_weights)
            self.profile_stats = defaultdict(lambda: {'games': 0, 'total_score': 0, 'wins': 0, 'avg_duration': 0},
                                           model_data.get('profile_stats', {}))
            self.move_evaluations = defaultdict(list, model_data.get('move_evaluations', {}))
            self.board_evaluations = model_data.get('board_evaluations', {})
            self.learning_rate = model_data.get('learning_rate', self.learning_rate)
            self.discount_factor = model_data.get('discount_factor', self.discount_factor)
            self.exploration_rate = model_data.get('exploration_rate', self.exploration_rate)
            
        except Exception as e:
            print(f"Error loading learning model: {e}")
    
    def save_episodes(self):
        """Save learning episodes to file"""
        episodes_data = []
        for episode in self.episodes:
            episodes_data.append({
                'board_states': episode.board_states,
                'moves': episode.moves,
                'scores': episode.scores,
                'final_score': episode.final_score,
                'max_tile': episode.max_tile,
                'duration': episode.duration,
                'timestamp': episode.timestamp,
                'success': episode.success
            })
        
        try:
            with open(self.episodes_file, 'w', encoding='utf-8') as f:
                json.dump(episodes_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving learning episodes: {e}")
    
    def load_episodes(self):
        """Load learning episodes from file"""
        if not self.episodes_file.exists():
            return
        
        try:
            with open(self.episodes_file, 'r', encoding='utf-8') as f:
                episodes_data = json.load(f)
            
            self.episodes = []
            for ep_data in episodes_data:
                episode = GameEpisode(
                    board_states=ep_data['board_states'],
                    moves=ep_data['moves'],
                    scores=ep_data['scores'],
                    final_score=ep_data['final_score'],
                    max_tile=ep_data['max_tile'],
                    duration=ep_data['duration'],
                    timestamp=ep_data['timestamp'],
                    success=ep_data['success']
                )
                self.episodes.append(episode)
                self.episode_buffer.append(episode)
                
        except Exception as e:
            print(f"Error loading learning episodes: {e}")
    
    def reset_learning(self):
        """Reset all learning data"""
        self.episodes = []
        self.episode_buffer.clear()
        self.move_evaluations.clear()
        self.board_evaluations.clear()
        self.profile_stats.clear()
        # Keep default feature weights but reset stats
        self.feature_weights = {
            'chain_length': 0.3,
            'potential_merges': 0.25,
            'board_entropy': 0.2,
            'max_tile_position': 0.15,
            'empty_cells': 0.1
        }