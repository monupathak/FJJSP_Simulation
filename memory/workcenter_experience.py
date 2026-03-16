import random
from dataclasses import dataclass
from collections import deque
from typing import Dict, List, Optional

@dataclass
class WorkCenterExperience:
    """Experience tuple for WorkCenter-level reinforcement learning"""
    workcenter_id: int
    state: Dict
    action: str  # Strategy applied to WorkCenter
    reward: float
    next_state: Dict
    timestamp: float
    episode: int

class WorkCenterExperienceReplayMemory:
    """Experience replay buffer for storing WorkCenter experiences"""
    def __init__(self, capacity: int = 256):
        self.capacity = capacity
        self.memory = deque(maxlen=capacity)

    def push(self, experience: WorkCenterExperience):
        """Store a WorkCenter experience"""
        self.memory.append(experience)

    def sample(self, batch_size: int) -> List[WorkCenterExperience]:
        """Sample random batch of WorkCenter experiences"""
        if len(self.memory) < batch_size:
            return list(self.memory)
        return random.sample(list(self.memory), batch_size)

    def get_experiences_by_workcenter(self, wc_id: int) -> List[WorkCenterExperience]:
        """Get all experiences for a specific WorkCenter"""
        return [exp for exp in self.memory if exp.workcenter_id == wc_id]

    def __len__(self):
        return len(self.memory)

class OptimalWorkCenterMemory:
    """Storage for optimal WorkCenter experiences"""
    def __init__(self):
        self.optimal_experiences = []

    def add_optimal_experience(self, experience: WorkCenterExperience):
        """Add an optimal WorkCenter experience"""
        self.optimal_experiences.append(experience)

    def get_best_strategy_for_workcenter(self, wc_id: int, current_episode: int) -> str:
        """Get the most recent best strategy for a WorkCenter"""
        wc_experiences = [exp for exp in self.optimal_experiences
                         if exp.workcenter_id == wc_id and exp.episode <= current_episode]
        if wc_experiences:
            return sorted(wc_experiences, key=lambda x: x.episode)[-1].action
        return "FIS"  # Default strategy
