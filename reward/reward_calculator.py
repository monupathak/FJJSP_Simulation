"""Simple reward scaler for workcenter decisions."""

from typing import Dict, Union


class RewardCalculator:
    def __init__(self, queue_weight: float = 1.0, tardiness_weight: float = 0.05):
        self.queue_weight = queue_weight
        self.tardiness_weight = tardiness_weight

    def calculate(self, workcenter_state: Dict[str, Union[int, float]], metrics: Dict[str, float]) -> float:
        queue_length = workcenter_state.get('num_jobs', 0)
        tardiness = metrics.get('recent_mean_tardiness', 0)
        reward = - (self.queue_weight * queue_length + self.tardiness_weight * tardiness)
        return max(-100.0, min(100.0, reward))
