"""
Event System for the 2248 bot project
Provides centralized event coordination between modules
"""
import time
from typing import Any, Dict, List, Callable, Optional
from enum import Enum
from dataclasses import dataclass
from threading import Lock
import json
from pathlib import Path


class EventType(Enum):
    """Enumeration of event types for the 2248 bot"""
    GAME_START = "game_start"
    GAME_END = "game_end"
    BOARD_RECOGNIZED = "board_recognized"
    CHAIN_FOUND = "chain_found"
    MOVE_EXECUTED = "move_executed"
    AD_DETECTED = "ad_detected"
    AD_HANDLED = "ad_handled"
    ERROR_OCCURRED = "error_occurred"
    STRATEGY_CHANGED = "strategy_changed"
    PROFILE_SELECTED = "profile_selected"
    LEARNING_UPDATE = "learning_update"
    STOP_REQUESTED = "stop_requested"


@dataclass
class Event:
    """Event data structure"""
    type: EventType
    data: Dict[str, Any]
    timestamp: float = None
    source: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class EventSystem:
    """Centralized event system for coordinating between bot modules"""
    
    def __init__(self, history_file: str = "events_history.json"):
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._history: List[Event] = []
        self._lock = Lock()
        self.history_file = Path(history_file)
        self.max_history_size = 1000
        
    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe a handler to an event type"""
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe a handler from an event type"""
        with self._lock:
            if event_type in self._handlers and handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
    
    def emit(self, event: Event):
        """Emit an event and notify all subscribers"""
        with self._lock:
            # Add to history
            self._history.append(event)
            if len(self._history) > self.max_history_size:
                self._history.pop(0)
            
            # Notify handlers
            if event.type in self._handlers:
                for handler in self._handlers[event.type]:
                    try:
                        handler(event)
                    except Exception as e:
                        print(f"Error in event handler for {event.type}: {e}")
    
    def emit_simple(self, event_type: EventType, data: Dict[str, Any] = None, source: str = None):
        """Helper method to emit an event with minimal setup"""
        event_data = data if data is not None else {}
        event = Event(type=event_type, data=event_data, source=source)
        self.emit(event)
    
    def get_events_by_type(self, event_type: EventType) -> List[Event]:
        """Get all events of a specific type"""
        with self._lock:
            return [event for event in self._history if event.type == event_type]
    
    def get_events_by_source(self, source: str) -> List[Event]:
        """Get all events from a specific source"""
        with self._lock:
            return [event for event in self._history if event.source == source]
    
    def get_recent_events(self, seconds: int) -> List[Event]:
        """Get events from the last specified seconds"""
        current_time = time.time()
        with self._lock:
            return [event for event in self._history 
                   if current_time - event.timestamp <= seconds]
    
    def clear_history(self):
        """Clear the event history"""
        with self._lock:
            self._history.clear()
    
    def save_history(self):
        """Save event history to file"""
        events_data = []
        for event in self._history:
            events_data.append({
                'type': event.type.value,
                'data': event.data,
                'timestamp': event.timestamp,
                'source': event.source
            })
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(events_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving event history: {e}")
    
    def load_history(self):
        """Load event history from file"""
        if not self.history_file.exists():
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
            
            self._history.clear()
            for event_data in events_data:
                event_type = EventType(event_data['type'])
                event = Event(
                    type=event_type,
                    data=event_data['data'],
                    timestamp=event_data['timestamp'],
                    source=event_data.get('source')
                )
                self._history.append(event)
                
        except Exception as e:
            print(f"Error loading event history: {e}")
    
    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about event counts by type"""
        stats = {}
        for event in self._history:
            event_type = event.type.value
            stats[event_type] = stats.get(event_type, 0) + 1
        return stats