
import simpy
from typing import List, Dict, Optional, Callable, Tuple


class Job:

    def __init__(self, job_id: int, typ: int, routing: List[int],
                 processing_time: List[Dict[int, int]], due_date: Optional[int] = None,
                 # Remove this parameter: all_work_centers: Optional[Dict[int, 'WorkCenter']] = None,
                 ):

        self.job_id = job_id
        self.routing = routing
        self.processing_time = processing_time
        self.current_op_idx = 0
        self.start_time = None
        self.end_time = None
        self.due_date = due_date
        self.completion_status = False
        self.operation_times = []
        # Remove this line: self.all_work_centers = all_work_centers
        # self.routing_agent = routing_agent
        self.completion_callbacks = []
        self.expected_slack = []
        self.actual_slack = []
        self.typ = typ
        self.rework = False



    def add_completion_callback(self, callback: Callable):
        self.completion_callbacks.append(callback)

    def notify_completion(self):
        return self.current_op_idx >= len(self.routing)

    def get_current_operation_options(self) -> Tuple[List[int], Dict[int, int]]:
        if self.current_op_idx < len(self.routing):
            return [self.routing[self.current_op_idx]], self.processing_time[self.current_op_idx]
        return [], {}

    def get_next_op(self):
        if self.current_op_idx < len(self.routing):
            return self.current_op_idx + 1
        else:
            return -1

    def is_completed(self) -> bool:
        return self.current_op_idx >= len(self.routing)

    def record_operation_start(self, time: float, wc_id: int, machine_id: int):

        if len(self.operation_times) <= self.current_op_idx:
            self.operation_times.append({
                'start': time,
                'wc_id': wc_id,
                'machine_id': machine_id,
                'end': None
            })
        else:
            self.operation_times[self.current_op_idx]['start'] = time
            self.operation_times[self.current_op_idx]['wc_id'] = wc_id
            self.operation_times[self.current_op_idx]['machine_id'] = machine_id

    def record_operation_end(self, time: float):
        if self.current_op_idx < len(self.operation_times):
            self.operation_times[self.current_op_idx]['end'] = time
        self.current_op_idx += 1
        if self.current_op_idx >= len(self.routing):
            self.end_time = time
            self.completion_status = True
            # print(f"-------------------Job {self.job_id} Has completed all of its Operation ")
            self.notify_completion()

    def calculate_flow_time(self) -> float:
        if self.start_time is not None and self.end_time is not None:
            return self.end_time - self.start_time
        return 0

    def calculate_tardiness(self) -> float:
        if self.due_date is not None and self.end_time is not None:
            return max(0, self.end_time - self.due_date)
        return 0

    def calculate_slack_time(self, current_time: float) -> float:
        remaining_ops = len(self.processing_time) - self.current_op_idx - 1
        remaining_pt = sum(
            min(ops.values())
            for ops in self.processing_time[self.current_op_idx+1:]
        )
        return self.due_date - (current_time + remaining_pt)

