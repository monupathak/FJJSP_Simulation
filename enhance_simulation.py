import copy
import simpy
import random
from jobcreator import JobCreator      
from workcenter import WorkCenter

from typing import Dict, List, Optional

class EnhancedSubSimulation:
    def __init__(self, main_coordinator, workcenter_strategies: Dict[int, str],
                 duration=14400, current_time: int = 0):
        """
        Initialize enhanced sub-simulation with WorkCenter-level strategies

        Args:
            main_coordinator: Reference to main training coordinator
            workcenter_strategies: Dict mapping WorkCenter ID to strategy name
            duration: Simulation duration in seconds (default 4 hours)
            current_time: Current simulation time
        """
        self.main = main_coordinator
        self.workcenter_strategies = workcenter_strategies
        self.duration = duration
        self.env = simpy.Environment()
        self.env.timeout(current_time)
        self.current_time = current_time
        self.machine_config = []

        # Initialize metrics tracking[6]
        self.metrics = {
            'total_tardiness': 0,
            'mean_tardiness': 0,
            'throughput': 0,
            'utilization': 0.0,
            'jobs_completed': 0,
            'new_jobs_created': 0
        }

        # State tracking dictionaries
        self.initial_machine_states = {}
        self.final_machine_states = {}
        self.initial_workcenter_states = {}
        self.final_workcenter_states = {}
        self.machine_processing_counts = {}
        self.workcenter_processing_counts = {}

        # Clone WorkCenters with new strategies
        self.work_centers = self._clone_workcenters_with_strategies()

        # Create isolated job creator
        self.job_creator = JobCreator(
            self.env,
            self.work_centers,
            num_work_centers=len(self.main.work_centers),
            current_time=0
        )

        self._link_machines_to_jobcreator()

        # Deep copy incomplete jobs from main simulation
        self.job_creator.created_jobs = [
            copy.deepcopy(job)
            for job in self.main.job_creator.created_jobs
            if not job.completion_status
        ]

        # Capture initial states
        self._capture_initial_states()

    def _clone_workcenters_with_strategies(self):
        """Clone WorkCenters and apply WorkCenter-level strategies"""
        cloned_wcs = {}
        
        
        for wc_id, original_wc in self.main.work_centers.items():
            # Get strategy for this WorkCenter
            wc_strategy = self.workcenter_strategies.get(wc_id, "FIS")

            self.machine_config.append(len(original_wc.machines))

            # Create new WorkCenter with the assigned strategy
            new_wc = WorkCenter(
                self.env,
                wc_id=wc_id,
                num_machines=len(original_wc.machines),
                strategy=wc_strategy  # WorkCenter-level strategy
            )
            
            # Clone machine queues from original WorkCenter
            for idx, original_machine in enumerate(original_wc.machines):
                cloned_machine = new_wc.machines[idx]
                cloned_machine.queue = [
                    copy.deepcopy(job) for job in original_machine.queue
                ]
                # Ensure the cloned machine has the WorkCenter strategy[7]
                cloned_machine.strategy = wc_strategy

                # Reset processing time counters for sub-simulation
                cloned_machine.temp_upper = 0
                cloned_machine.temp_lower = 0

            cloned_wcs[wc_id] = new_wc

        return cloned_wcs

    def _capture_initial_states(self):
        """Capture initial machine and WorkCenter states"""

        for wc_id, wc in self.work_centers.items():
            # Collect machine states for this WorkCenter
            machine_states = []
            for machine in wc.machines:
                queue_sorted = machine.get_sorted_queue()
                machine_state = wc.get_machine_state(machine, queue_sorted, self.env.now)
                machine_states.append(machine_state)
                self.initial_machine_states[machine.machine_id] = machine_state

            # Combine first two machines' states (adjust as needed)
            wc_state = wc.get_workcenter_states(machine_states,max(self.machine_config))

            self.initial_workcenter_states[wc_id] = wc_state




    def _link_machines_to_jobcreator(self):
        """Connect all machines to the sub-simulation's job creator"""
        for wc in self.work_centers.values():
            for machine in wc.machines:
                machine.job_creator = self.job_creator

    def run(self):
        """Run the sub-simulation and capture final states"""
        print(f"Running future-simulation to evaluate it over {self.workcenter_strategies} strategies")

        # Start processing on all machines
        for wc in self.work_centers.values():
            for machine in wc.machines:
                if machine.queue:
                   
                    self.env.process(machine.process_jobs())

        # Run simulation for specified duration
        self.env.run(until=self.duration)

        # Capture final states
        self._capture_final_states()

        # Calculate metrics
        self._calculate_metrics()

        print(f"Sub-simulation complete. Metrics: {self.metrics}")
        return self.metrics

    def _capture_final_states(self):
        """Capture final machine and WorkCenter states after simulation"""
        for wc_id, wc in self.work_centers.items():
            # Capture final WorkCenter state

            machine_states = []
            # Capture final machine states and processing counts
            for machine in wc.machines:
                queue_sorted = machine.get_sorted_queue()

                machine_state = wc.get_machine_state(machine, queue_sorted, self.env.now)

                self.final_machine_states[machine.machine_id] = machine_state
                machine_states.append(machine_state)
                # Store processing time counts for reward calculation

                self.machine_processing_counts[machine.machine_id] = {
                    'over_5min': machine.temp_upper,
                    'under_5min': machine.temp_lower
                }
           
            self.final_workcenter_states[wc_id] = wc.get_workcenter_states(machine_states, max(self.machine_config))





    def calculate_machine_reward(self, machine_id: int) -> float:
        """Calculate reward using the new proportional cost function"""
        mean_tardiness = self.metrics.get('mean_tardiness', 0)
        counts = self.machine_processing_counts.get(machine_id, {'over_5min': 0, 'under_5min': 0})

        nlong = counts['over_5min']
        nshort = counts['under_5min']
        ntotal = nlong + nshort

        if ntotal == 0:
            # Only tardiness component when no jobs processed
            cost = mean_tardiness
        else:
            # New cost function: mean_tardiness + 0.25 * nlong/ntotal + 0.75 * nshort/ntotal
            cost = mean_tardiness + 0.25 * (nlong / ntotal) + 0.75 * (nshort / ntotal)

        return cost

    def calculate_workcenter_reward(self, wc_id: int) -> float:
        """Calculate WorkCenter-level reward"""
        mean_tardiness = self.metrics.get('mean_tardiness', 0)
        wc_state = self.final_workcenter_states.get(wc_id, {})
        print(f"workcenter ID: {wc_id}" )
        if wc_id == 1:
          count1 = self.machine_processing_counts.get(1, {'over_5min': 0, 'under_5min': 0})
          count2 = self.machine_processing_counts.get(2, {'over_5min': 0, 'under_5min': 0})
        elif wc_id == 2:
          count1 = self.machine_processing_counts.get(3, {'over_5min': 0, 'under_5min': 0})
          count2 = self.machine_processing_counts.get(4, {'over_5min': 0, 'under_5min': 0})
        else :
          count1 = self.machine_processing_counts.get(5, {'over_5min': 0, 'under_5min': 0})
          count2 = self.machine_processing_counts.get(6, {'over_5min': 0, 'under_5min': 0})




        nlong = count1['over_5min'] +count2['over_5min']
        nshort = count1['under_5min'] + count1['under_5min']
        ntotal = nlong + nshort

        if ntotal == 0:
            cost = mean_tardiness
        else:
            cost = mean_tardiness + 0.25 * (nlong / ntotal) + 0.75 * (nshort / ntotal)

        print(f"reward Calulation for workcenter {wc_id}")
        print("processed jobs count: ",self.machine_processing_counts)
        print("cost :-",cost)


        return cost

    def _calculate_metrics(self):
        """Calculate simulation metrics"""

        if self.env.now < 240:
            print("using privious jobs ")
            # During early simulation, use only completed jobs
            completed_jobs = [
                job for job in self.job_creator.created_jobs
                if job.completion_status
            ]
        else:
            print("Using recent jobs ")
            # Use jobs completed in the last 240 minutes
            completed_jobs = [
                job for job in self.job_creator.created_jobs
                if job.completion_status and job.end_time >= self.env.now - 240
            ]
        total_working = sum(
            m.total_working_time
            for wc in self.work_centers.values()
            for m in wc.machines
        )

        total_machines = sum(len(wc.machines) for wc in self.work_centers.values())

        # Calculate tardiness metrics
        if completed_jobs:
            tardiness_values = [j.calculate_tardiness() for j in completed_jobs]
            self.metrics.update({
                'total_tardiness': sum(tardiness_values),
                'mean_tardiness': sum(tardiness_values) / len(tardiness_values),
                'jobs_completed': len(completed_jobs),
                'throughput': len(completed_jobs) / (self.duration/3600),
                'utilization': total_working / (self.duration * total_machines) if total_machines > 0 else 0,
                'new_jobs_created': len([
                    j for j in self.job_creator.created_jobs
                    if j.start_time >= self.current_time
                ])
            })

