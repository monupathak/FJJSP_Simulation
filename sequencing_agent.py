# from machine import Machine
from typing import List, Optional, Dict, Tuple, Callable
from job import Job


class SequencingAgent:
    def __init__(self, strategy: str = 'SPT'):
        self.strategy = strategy

    def select(self, machine: 'Machine', strategy_override: str = None) -> Optional[Job]:
        if not machine.queue:
            return None

        # Use override if provided, otherwise use instance strategy
        strategy_to_use = strategy_override if strategy_override is not None else self.strategy

        if strategy_to_use == 'SPT':  # Shortest Processing Time
            selected_job = min(machine.queue,
                             key=lambda job: job.processing_time[job.current_op_idx][machine.machine_id])
            machine.queue.remove(selected_job)
            return selected_job

        elif strategy_to_use == 'FIFO':  # First In First Out
            return machine.queue.pop(0)

        elif strategy_to_use == 'EDD':  # Earliest Due Date
            selected_job = min(machine.queue, key=lambda job: job.due_date)
            machine.queue.remove(selected_job)
            return selected_job

        elif strategy_to_use == "FIS":  # First In System
            selected_job = min(machine.queue, key=lambda job: job.job_id)
            machine.queue.remove(selected_job)
            return selected_job

        elif strategy_to_use == "LPT":  # Longest Processing Time
            selected_job = max(machine.queue,
                             key=lambda job: job.processing_time[job.current_op_idx][machine.machine_id])
            machine.queue.remove(selected_job)
            return selected_job

        else:  # Default to FIFO
            return machine.queue.pop(0)

