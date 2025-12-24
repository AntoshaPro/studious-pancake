"""
Game State Tracker for the 2248 bot project
Tracks game state and statistics across multiple games
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from collections import defaultdict, deque
import numpy as np


@dataclass
class GameState:
    """Represents the current state of the game"""
    board: List[List[int]]
    score: int
    moves_count: int
    max_tile: int
    empty_cells: int
    timestamp: float
    profile_used: int
    chain_length_stats: Dict[int, int]  # Count of chains by length


@dataclass
class GameSession:
    """Represents a complete game session"""
    start_time: float
    end_time: float
    initial_state: GameState
    final_state: GameState
    moves_sequence: List[Tuple[int, int]]  # Sequence of moves made
    score_progression: List[int]  # Score after each move
    max_tile_progression: List[int]  # Max tile after each move
    profile_used: int
    success: bool  # Whether the game was successful
    reason: str  # Reason for game end (win, lose, stop, etc)


class GameStateTracker:
    """Tracks game state and statistics across multiple games"""
    
    def __init__(self, stats_file: str = "game_stats.json"):
        self.stats_file = Path(stats_file)
        
        # Current game state
        self.current_state: Optional[GameState] = None
        self.current_session: Optional[GameSession] = None
        
        # Historical data
        self.game_sessions: List[GameSession] = []
        self.session_history = deque(maxlen=50)  # Keep last 50 sessions
        
        # Statistics
        self.total_games: int = 0
        self.total_wins: int = 0
        self.total_score: int = 0
        self.total_moves: int = 0
        self.max_score_ever: int = 0
        self.max_tile_ever: int = 0
        
        # Profile statistics
        self.profile_stats: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
            'games': 0,
            'wins': 0,
            'total_score': 0,
            'avg_score': 0,
            'avg_duration': 0,
            'avg_moves': 0
        })
        
        # Chain statistics
        self.chain_stats: Dict[int, Dict[str, int]] = defaultdict(lambda: {
            'attempts': 0,
            'successes': 0,
            'total_score': 0
        })
        
        # Performance metrics
        self.performance_history: List[Dict[str, float]] = []
        
        # Load existing data if available
        self.load_stats()
    
    def start_new_game(self, board: List[List[int]], profile_idx: int = 0) -> GameState:
        """Start tracking a new game"""
        # End previous session if exists
        if self.current_session is not None:
            self.end_current_session("interrupted")
        
        # Calculate initial stats
        score = self._calculate_score_from_board(board)
        max_tile = self._get_max_tile(board)
        empty_cells = self._count_empty_cells(board)
        
        # Create initial game state
        initial_state = GameState(
            board=[row[:] for row in board],  # Deep copy
            score=score,
            moves_count=0,
            max_tile=max_tile,
            empty_cells=empty_cells,
            timestamp=time.time(),
            profile_used=profile_idx,
            chain_length_stats=self._analyze_chain_lengths(board)
        )
        
        # Create session
        self.current_session = GameSession(
            start_time=time.time(),
            end_time=0,  # Will be set when game ends
            initial_state=initial_state,
            final_state=None,  # Will be set when game ends
            moves_sequence=[],
            score_progression=[score],
            max_tile_progression=[max_tile],
            profile_used=profile_idx,
            success=False,
            reason=""
        )
        
        self.current_state = initial_state
        return initial_state
    
    def update_game_state(self, board: List[List[int]], move: Tuple[int, int] = None) -> GameState:
        """Update the current game state"""
        if self.current_state is None:
            raise ValueError("No active game session. Call start_new_game() first.")
        
        # Calculate new stats
        score = self._calculate_score_from_board(board)
        max_tile = self._get_max_tile(board)
        empty_cells = self._count_empty_cells(board)
        
        # Update moves count
        moves_count = self.current_state.moves_count
        if move is not None:
            moves_count += 1
        
        # Create new game state
        new_state = GameState(
            board=[row[:] for row in board],  # Deep copy
            score=score,
            moves_count=moves_count,
            max_tile=max_tile,
            empty_cells=empty_cells,
            timestamp=time.time(),
            profile_used=self.current_state.profile_used,
            chain_length_stats=self._analyze_chain_lengths(board)
        )
        
        # Update session data
        if move is not None and self.current_session is not None:
            self.current_session.moves_sequence.append(move)
            self.current_session.score_progression.append(score)
            self.current_session.max_tile_progression.append(max_tile)
        
        self.current_state = new_state
        return new_state
    
    def end_current_session(self, reason: str, success: bool = False) -> GameSession:
        """End the current game session and return the session data"""
        if self.current_session is None:
            raise ValueError("No active game session to end.")
        
        # Set final state
        self.current_session.final_state = self.current_state
        self.current_session.end_time = time.time()
        self.current_session.success = success
        self.current_session.reason = reason
        
        # Update statistics
        self._update_statistics(self.current_session)
        
        # Add to history
        self.game_sessions.append(self.current_session)
        self.session_history.append(self.current_session)
        
        # Save stats
        self.save_stats()
        
        session = self.current_session
        self.current_session = None
        self.current_state = None
        
        return session
    
    def _update_statistics(self, session: GameSession):
        """Update overall statistics based on completed session"""
        self.total_games += 1
        if session.success:
            self.total_wins += 1
        self.total_score += session.final_state.score
        self.total_moves += session.final_state.moves_count
        
        if session.final_state.score > self.max_score_ever:
            self.max_score_ever = session.final_state.score
        if session.final_state.max_tile > self.max_tile_ever:
            self.max_tile_ever = session.final_state.max_tile
        
        # Update profile statistics
        profile_idx = session.profile_used
        profile_stats = self.profile_stats[profile_idx]
        profile_stats['games'] += 1
        if session.success:
            profile_stats['wins'] += 1
        profile_stats['total_score'] += session.final_state.score
        profile_stats['avg_score'] = profile_stats['total_score'] / profile_stats['games']
        profile_stats['avg_duration'] = (
            profile_stats['avg_duration'] * (profile_stats['games'] - 1) + 
            (session.end_time - session.start_time)
        ) / profile_stats['games']
        profile_stats['avg_moves'] = (
            profile_stats['avg_moves'] * (profile_stats['games'] - 1) + 
            session.final_state.moves_count
        ) / profile_stats['games']
        
        # Calculate performance metrics
        duration = session.end_time - session.start_time
        performance = {
            'score': session.final_state.score,
            'duration': duration,
            'moves': session.final_state.moves_count,
            'score_per_second': session.final_state.score / max(duration, 1),
            'score_per_move': session.final_state.score / max(session.final_state.moves_count, 1),
            'max_tile': session.final_state.max_tile,
            'timestamp': session.end_time
        }
        self.performance_history.append(performance)
        if len(self.performance_history) > 100:  # Keep last 100 performances
            self.performance_history.pop(0)
    
    def _calculate_score_from_board(self, board: List[List[int]]) -> int:
        """Calculate approximate score from board state (simplified)"""
        score = 0
        for row in board:
            for cell in row:
                if cell > 2:
                    # Simplified scoring based on tile values
                    score += cell * (cell // 2)  # This is an approximation
        return score
    
    def _get_max_tile(self, board: List[List[int]]) -> int:
        """Get the maximum tile value on the board"""
        return max(max(row) for row in board)
    
    def _count_empty_cells(self, board: List[List[int]]) -> int:
        """Count empty cells on the board"""
        return sum(1 for row in board for cell in row if cell == 0)
    
    def _analyze_chain_lengths(self, board: List[List[int]]) -> Dict[int, int]:
        """Analyze potential chain lengths on the board"""
        # This is a simplified analysis - in a real implementation,
        # this would look for potential merge chains
        chain_counts = defaultdict(int)
        
        # Count adjacent equal tiles as potential length-2 chains
        for r in range(len(board)):
            for c in range(len(board[0])):
                if board[r][c] > 0:
                    # Check right neighbor
                    if c + 1 < len(board[0]) and board[r][c] == board[r][c + 1]:
                        chain_counts[2] += 1
                    # Check bottom neighbor
                    if r + 1 < len(board) and board[r][c] == board[r + 1][c]:
                        chain_counts[2] += 1
        
        return dict(chain_counts)
    
    def get_current_game_stats(self) -> Dict[str, Any]:
        """Get statistics for the current game"""
        if self.current_state is None:
            return {}
        
        return {
            'current_score': self.current_state.score,
            'current_max_tile': self.current_state.max_tile,
            'current_empty_cells': self.current_state.empty_cells,
            'moves_count': self.current_state.moves_count,
            'profile_used': self.current_state.profile_used,
            'chain_stats': self.current_state.chain_length_stats,
            'game_duration': time.time() - self.current_state.timestamp if self.current_session else 0
        }
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall game statistics"""
        avg_score = self.total_score / max(self.total_games, 1)
        win_rate = self.total_wins / max(self.total_games, 1)
        
        return {
            'total_games': self.total_games,
            'total_wins': self.total_wins,
            'win_rate': win_rate,
            'total_score': self.total_score,
            'avg_score': avg_score,
            'max_score_ever': self.max_score_ever,
            'max_tile_ever': self.max_tile_ever,
            'total_moves': self.total_moves,
            'avg_moves_per_game': self.total_moves / max(self.total_games, 1),
            'profile_stats': dict(self.profile_stats),
            'recent_performance': self.performance_history[-10:] if self.performance_history else []
        }
    
    def get_profile_recommendation(self) -> int:
        """Get the recommended profile based on statistics"""
        if not self.profile_stats:
            return 0  # Default to first profile
        
        best_profile = 0
        best_score = -float('inf')
        
        for profile_idx, stats in self.profile_stats.items():
            if stats['games'] == 0:
                continue
            
            # Calculate a composite score considering win rate and average score
            win_rate = stats['wins'] / stats['games']
            avg_score_norm = stats['avg_score'] / 10000  # Normalize
            avg_duration_norm = 1 / max(stats['avg_duration'], 1)  # Inverse for faster games
            
            # Weighted score: 40% win rate, 40% avg score, 20% speed
            profile_score = 0.4 * win_rate + 0.4 * avg_score_norm + 0.2 * avg_duration_norm
            
            if profile_score > best_score:
                best_score = profile_score
                best_profile = profile_idx
        
        return best_profile
    
    def save_stats(self):
        """Save statistics to file"""
        stats_data = {
            'total_games': self.total_games,
            'total_wins': self.total_wins,
            'total_score': self.total_score,
            'max_score_ever': self.max_score_ever,
            'max_tile_ever': self.max_tile_ever,
            'total_moves': self.total_moves,
            'profile_stats': dict(self.profile_stats),
            'chain_stats': dict(self.chain_stats),
            'performance_history': self.performance_history,
            'recent_sessions': [
                {
                    'start_time': s.start_time,
                    'end_time': s.end_time,
                    'initial_score': s.initial_state.score,
                    'final_score': s.final_state.score if s.final_state else 0,
                    'final_max_tile': s.final_state.max_tile if s.final_state else 0,
                    'moves_count': s.final_state.moves_count if s.final_state else 0,
                    'profile_used': s.profile_used,
                    'success': s.success,
                    'reason': s.reason
                }
                for s in list(self.session_history)[-20:]  # Save last 20 sessions
            ]
        }
        
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving game stats: {e}")
    
    def load_stats(self):
        """Load statistics from file"""
        if not self.stats_file.exists():
            return
        
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                stats_data = json.load(f)
            
            self.total_games = stats_data.get('total_games', 0)
            self.total_wins = stats_data.get('total_wins', 0)
            self.total_score = stats_data.get('total_score', 0)
            self.max_score_ever = stats_data.get('max_score_ever', 0)
            self.max_tile_ever = stats_data.get('max_tile_ever', 0)
            self.total_moves = stats_data.get('total_moves', 0)
            self.profile_stats = defaultdict(lambda: {
                'games': 0, 'wins': 0, 'total_score': 0, 
                'avg_score': 0, 'avg_duration': 0, 'avg_moves': 0
            }, stats_data.get('profile_stats', {}))
            self.chain_stats = defaultdict(lambda: {'attempts': 0, 'successes': 0, 'total_score': 0},
                                         stats_data.get('chain_stats', {}))
            self.performance_history = stats_data.get('performance_history', [])
            
            # Load recent sessions (but don't recreate full GameSession objects)
            # since we don't have the full board states saved
            recent_sessions_data = stats_data.get('recent_sessions', [])
            
        except Exception as e:
            print(f"Error loading game stats: {e}")
    
    def reset_stats(self):
        """Reset all statistics"""
        self.total_games = 0
        self.total_wins = 0
        self.total_score = 0
        self.max_score_ever = 0
        self.max_tile_ever = 0
        self.total_moves = 0
        self.profile_stats.clear()
        self.chain_stats.clear()
        self.performance_history.clear()
        self.game_sessions.clear()
        self.session_history.clear()
        self.current_state = None
        self.current_session = None