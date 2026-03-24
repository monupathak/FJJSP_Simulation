"""Simple epsilon scheduler for exploration decay."""

from dataclasses import dataclass


@dataclass
class EpsilonScheduler:
    start: float = 1.0
    end: float = 0.1
    decay: float = 0.97
    epsilon: float = 1.0

    def __post_init__(self):
        self.epsilon = self.start

    def step(self) -> float:
        self.epsilon = max(self.end, self.epsilon * self.decay)
        return self.epsilon

    def reset(self) -> None:
        self.epsilon = self.start
