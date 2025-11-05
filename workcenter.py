import simpy
import statistics
from typing import List
from job import Job
from machine import Machine
# from routing_agent import DRLAwareRoutingAgent
BREAKDOWN_MEAN = 500  # Mean time between breakdowns
REPAIR_TIME = 50      # Mean repair time    

class WorkCenter:
    def __init__(self, env: simpy.Environment, wc_id: int, num_machines: int,
                 strategy:  str = "FIS"):
        self.env = env
        self.wc_id = wc_id
        self.num_machines = num_machines
        self.machines = []
        self.queue = []
        self.completed_jobs = []

        # self.routing_agent = routing_agent
        self.mac_ind = {}

        self.workcenter_strategy = strategy  # This line was missing!
        self.current_shift = 1
        self.workcenter_state = {}
        # Experience tracking for WorkCenter (if needed)
        self.workcenter_experiences = []
        self.state_history = []
        self.last_workcenter_state = None
        self.state = {}
        self.processed_count = []

        # Create machines and assign WorkCenter strategy to all machines
        for i in range(num_machines):
            machine_id = (wc_id - 1) * num_machines + i + 1
            resource = simpy.PriorityResource(self.env, capacity=1)
            self.mac_ind[machine_id] = i

            # Now self.workcenter_strategy exists and can be used
            machine = Machine(
                self.env, resource, BREAKDOWN_MEAN, REPAIR_TIME,
                machine_id, wc_id, self.workcenter_strategy
            )
            self.machines.append(machine)

        # self.env.process(self._periodic_state_collection())

    def update_workcenter_strategy(self, new_strategy: str):
            """Update strategy for entire WorkCenter and propagate to all machines"""
            self.workcenter_strategy = new_strategy
            for machine in self.machines:
                machine.strategy = new_strategy
            print(f"WorkCenter {self.wc_id} strategy updated to: {new_strategy}")



    def _periodic_state_collection(self):
        """Collect machine states every 120 minutes"""
        while True:
            yield self.env.timeout(60*12)  # Wait 120 minutes
            current_time = self.env.now
            print(f"\n=== WorkCenter {self.wc_id} State Report @ {current_time} min ===")
            self.current_shift += 1

            # Initialize state dictionaries
            state1 = {}
            state2 = {}

            for machine in self.machines:
                queue = machine.get_sorted_queue()
                state = self.get_machine_state(machine, queue, self.env.now)

                # Assign states based on machine ID (odd/even)
                if machine.machine_id % 2 == 1:  # Odd machine IDs go to state1
                    state1 = state
                else:  # Even machine IDs go to state2
                    state2 = state

                # Print individual machine information
                print("from Workcenter:")
                for key, value in state.items():
                    print(f"{key}: {value}")
                print(f"Machine {machine.machine_id}:")
                print(f"  Jobs in queue: {state['num_jobs']}")
                print(f"  Avg processing time: {state['processing_time']['avg']:.2f}")
                print(f"Machine Strategy {machine.strategy}")

                # Reset per-shift counters for THIS machine (not self)
                print(f"Jobs >5 mins: {machine.temp_upper}")
                print(f"Jobs <=5 mins: {machine.temp_lower}")
                self.processed_count.append((machine.temp_upper, machine.temp_lower ))
                machine.temp_lower = 0  # Fixed: use machine.temp_lower
                machine.temp_upper = 0  # Fixed: use machine.temp_upper

            # Get combined WorkCenter state and store it
            # self.workcenter_state = self.get_workcenter_states(state1, state2)

            # Store the WorkCenter state for later use
            if not hasattr(self, 'workcenter_state_history'):
                self.workcenter_state_history = []

            self.workcenter_state_history.append({
                'timestamp': current_time,
                'shift': self.current_shift,
                'state': self.workcenter_state
            })

      

    def get_queue_length(self) -> int:
        return sum(len(m.queue) for m in self.machines)

    #Returns the machine with the shortest queue in this work center.
    def shortest_queue_length(self):

        if not self.machines:
            return None

        min_q_len = float('inf')  # Initialize to infinity for proper comparison
        min_q_mac = 0

        for i in range(self.num_machines):
            machine = self.machines[i]
            queue_len = len(machine.queue)
            if machine.processing_job != None :
               queue_len += 1
            if queue_len < min_q_len:
                min_q_len = queue_len
                min_q_mac = i

        # Calculate the machine ID based on work center ID and machine index
        machine_id = (self.wc_id - 1) * self.num_machines + min_q_mac + 1

        # Get the corresponding machine object
        machine = self.machines[min_q_mac] # i am selceting the machine with its list that's why here index can be zero


        # print(f"Machine {machine_id}, machine index {min_q_mac} is having the smallest queue with {min_q_len} jobs")

        return machine


    def shortest_queue_pt(self):
        """Returns the machine with the shortest queue processing time in this work center."""
        if not self.machines:
            return None

        min_total_time = float('inf')  # Initialize to infinity for proper comparison
        min_q_mac = -1
        machine_idx = -1

        for i in range(self.num_machines):
            machine = self.machines[i]
            # Calculate the machine ID based on work center ID and machine index
            machine_id = (self.wc_id - 1) * self.num_machines + i + 1

            total_time = 0
            for job in machine.queue:
                if machine_id in job.processing_time[job.current_op_idx]:
                    total_time += job.processing_time[job.current_op_idx][machine_id]

            if total_time < min_total_time:
                min_total_time = total_time
                min_q_mac = i
                machine_idx = machine_id

        # Handle case where all queues might be empty
        if min_q_mac == -1:
            return None

        # Get the corresponding machine object
        machine = self.machines[min_q_mac]

        # print(f"Machine {machine_idx}, machine index {min_q_mac} is having the smallest queue processing time i.e {min_total_time} time units")

        return machine


    def queue_status(self):

        for i in range(self.num_machines):

            machine = self.machines[i]
            # Calculate the machine ID based on work center ID and machine index
            machine_id = (self.wc_id - 1) * self.num_machines + i + 1
            print(f"Machine and Queue Status of Machine {machine_id} Current_time {self.env.now} ")
            if machine.processing_job != None :
              print("status of current job" )
              print(" Job Id---",machine.processing_job.job_id, " PT---",machine.processing_job.processing_time[machine.processing_job.current_op_idx],"DD---", machine.processing_job.due_date, "Start_time---", machine.start_time )

            for job in machine.queue:
                if machine_id in job.processing_time[job.current_op_idx]:
                    print(" Job Id---", job.job_id," PT---", job.processing_time[job.current_op_idx][machine_id],"DD---", job.due_date, "Ends Here" )



    def earliest_available(self):
        """Returns the machine with the shortest queue processing time in this work center."""
        if not self.machines:
            return None
        min_total_time = float('inf')  # Initialize to infinity for proper comparison
        min_q_mac = -1
        machine_idx = -1
        # total_time = 0
        for i in range(self.num_machines):
            machine = self.machines[i]
            # Calculate the machine ID based on work center ID and machine index
            machine_id = (self.wc_id - 1) * self.num_machines + i + 1
            mc_av_t = machine.get_available_time()
            if mc_av_t < min_total_time:
                min_total_time = mc_av_t
                min_q_mac = i
                machine_idx = machine_id

        # Get the corresponding machine object
        machine = self.machines[min_q_mac]

        # print(f"Machine {machine_idx}, machine index {min_q_mac} is earliest availble i.e {min_total_time} time units")

        return machine



    def get_machine_state(self, machine, queue_sorted: List[Job], current_time):
        """Calculate machine state metrics for jobs in sorted queue"""
        state = {
            'num_jobs': len(queue_sorted),
            'processing_time': {'min': 0, 'max': 0, 'avg': 0, 'sum': 0},
            'slack_time': {'min': 0, 'max': 0, 'avg': 0},
            'due_date_tightness': {'min': 0, 'max': 0, 'sum': 0},
            'processing_time_distribution': {'<=5': 0, '>5': 0},
            'remaining_time': {'min': 0, 'max': 0, 'avg': 0, 'sum': 0},
            'coeff_variation_pt': 0,
            'coeff_variation_rt': 0
        }

        if not queue_sorted:
            return state

        # Initialize collections
        processing_times = []
        slack_times = []
        ttd_values = []
        remaining_times = []
        pt_buckets = [0]*2  # For <5, 6

        # Calculate machine available time
        exp_mc_av = 0
        if machine.processing_job and machine.machine_id in machine.processing_job.processing_time[machine.processing_job.current_op_idx]:
            exp_mc_av += (machine.processing_job.processing_time[machine.processing_job.current_op_idx][machine.machine_id] -
                        (machine.env.now - machine.start_time))

        # Process each job in queue
        for idx, job in enumerate(queue_sorted):
            # Get processing time
            pt = job.processing_time[job.current_op_idx][machine.machine_id]
            processing_times.append(pt)

            # Calculate slack
            total_remaining = machine.total_process_time_remain(machine, job)
            slack = job.due_date - current_time - exp_mc_av - total_remaining
            slack_times.append(slack)

            # Calculate tightness of due date
            ttd = job.due_date - current_time
            ttd_values.append(ttd)

            # Calculate remaining time
            remaining_times.append(total_remaining)

            # Update processing time buckets
            if pt <= 5:
                pt_buckets[0] += 1
            else:
                pt_buckets[1] += 1

            # Update machine available time for next job
            exp_mc_av += pt

        # Calculate statistics
        state['processing_time'] = {
            'min': min(processing_times),
            'max': max(processing_times),
            'avg': statistics.mean(processing_times),
            'sum': sum(processing_times)  }

        state['slack_time'] = {
            'min': min(slack_times),
            'max': max(slack_times),
            'avg': statistics.mean(slack_times)
        }

        state['due_date_tightness'] = {
            'min': min(ttd_values),
            'max': max(ttd_values),
            'sum': sum(ttd_values)
        }

        state['remaining_time'] = {
            'min': min(remaining_times),
            'max': max(remaining_times),
            'avg': statistics.mean(remaining_times),
            'sum': sum(remaining_times)
        }

        # Calculate coefficients of variation
        state['coeff_variation_pt'] = self._calculate_coeff_variation(processing_times)
        state['coeff_variation_rt'] = self._calculate_coeff_variation(remaining_times)

        # Calculate percentage distributions
        total_jobs = len(queue_sorted)
        state['processing_time_distribution'] = {
            '<=5': (pt_buckets[0]/total_jobs)*100,
            '>5': (pt_buckets[1]/total_jobs)*100
        }



        return state

    def _calculate_coeff_variation(self, data):
        """Helper function to calculate coefficient of variation"""
        if len(data) < 2:
            return 0
        try:
            return statistics.stdev(data)/statistics.mean(data)
        except statistics.StatisticsError:
            return 0


    def get_workcenter_states(self, machine_states: List[dict], max_machines: int) -> dict:
        """Combine a list of machine state dicts into a single workcenter state.

        Rules:
        - If more machine states are provided than max_machines: warn and truncate to max_machines.
        - If fewer machine states are provided than max_machines: include given states and append
          empty placeholder states for remaining machines.
        - If equal: combine and return.
        """
        combined_state = {}

        # Normalize input
        if machine_states is None:
            machine_states = []

        actual_count = len(machine_states)

        if actual_count > max_machines:
            print(f"Warning: {actual_count} machine states provided, which exceeds max_machines={max_machines}. Truncating.")
            machine_states = machine_states[:max_machines]
            actual_count = max_machines
        elif actual_count < max_machines:
            print(f"Info: {actual_count} machine states provided, less than max_machines={max_machines}. Filling remaining with empty states.")

        # Template for an empty machine state (keeps keys consistent with get_machine_state)
        empty_state = {
            'num_jobs': 0,
            'processing_time': {'min': 0, 'max': 0, 'avg': 0, 'sum': 0},
            'slack_time': {'min': 0, 'max': 0, 'avg': 0},
            'due_date_tightness': {'min': 0, 'max': 0, 'sum': 0},
            'processing_time_distribution': {'<=5': 0, '>5': 0},
            'remaining_time': {'min': 0, 'max': 0, 'avg': 0, 'sum': 0},
            'coeff_variation_pt': 0,
            'coeff_variation_rt': 0
        }

        # Ensure list length equals max_machines by appending empty states if needed
        for _ in range(actual_count, max_machines):
            machine_states.append(empty_state.copy())

        # Combine states: for dict-valued keys keep a nested dict with per-machine suffixes,
        # for scalar keys create key_m{n}
        for idx, st in enumerate(machine_states[:max_machines]):
            m_suffix = f"_m{idx+1}"
            for key, val in (st or {}).items():
                if isinstance(val, dict):
                    # create or update nested dict for this key
                    if key not in combined_state or not isinstance(combined_state[key], dict):
                        combined_state[key] = {}
                    for subk, subv in val.items():
                        combined_state[key][f"{subk}{m_suffix}"] = subv
                else:
                    combined_state[f"{key}{m_suffix}"] = val
        
        return combined_state

