"""Utility to convert workcenter dictionaries into fixed-size vectors."""

from typing import Dict, Iterable, Tuple, Union


class StateVectorizer:
    def vectorize(self, workcenter_state: Dict[str, Union[int, float]]) -> Tuple[float, ...]:
        num_jobs = float(workcenter_state.get('num_jobs', 0))
        avg_processing = float(workcenter_state.get('processing_time', {}).get('avg', 0))
        utilization = float(workcenter_state.get('utilization', 0))
        return (num_jobs, avg_processing, utilization)

    def vectorize_all(self, workcenter_states: Dict[int, Dict[str, Union[int, float]]]) -> Dict[int, Tuple[float, ...]]:
        return {wc_id: self.vectorize(state) for wc_id, state in workcenter_states.items()}
