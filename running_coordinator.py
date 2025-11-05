import simpy
from typing import Dict
from workcenter import WorkCenter
from jobcreator import JobCreator
from enhance_simulation import EnhancedSubSimulation
from workcenter_experience import WorkCenterExperience
from workcenter_experience import WorkCenterExperienceReplayMemory
from workcenter_experience import OptimalWorkCenterMemory
from recent_metrics_collector import RecentMetricsCollector
from typing import Tuple, List



class PauseResumeTrainingCoordinator:
    def __init__(self, num_work_centers=3, num_machines:List[int]=[2,2,2], strategies : List[str]=["SPT", "EDD", "FIFO", "LPT", "FIS"]):
        """
        Initialize training coordinator with WorkCenter-level strategy management

        Args:
            num_work_centers: Number of WorkCenters in the system
            num_machines: Number of machines per WorkCenter
        """
        self.num_episodes = 2
        self.interval_duration = 60  # 4 hours in seconds
        self.evaluation_duration = 60  # 4 hours for sub-simulation

        # Strategy options for WorkCenters[6]
        self.strategies = strategies

        # WorkCenter-level strategies (one strategy per WorkCenter)
        self.workcenter_strategies = {
            wc_id: "FIS" for wc_id in range(1, num_work_centers + 1)
        }

        # Experience storage for WorkCenter-level learning
        self.wc_experience_memory = WorkCenterExperienceReplayMemory(capacity=256)
        self.wc_optimal_memory = OptimalWorkCenterMemory()

        # Training parameters
        self.num_work_centers = num_work_centers
        self.num_machines = num_machines
        self.current_episode = 0

        # no of jobs processed by workcenter
        self.wc1_count_lower = 0
        self.wc2_count_upper =  0
        self.wc3_count_lower = 0
        self.wc1_count_upper = 0
        self.wc2_count_lower =  0
        self.wc3_count_upper = 0
        self.recent_metric = {}
        # Initialize environment
        self.initialize_environment()

    def initialize_environment(self):
        """Initialize the simulation environment with WorkCenter-level strategies"""
        self.env = simpy.Environment()
        print("""Initialize the simulation environment with WorkCenter-level strategies""")
        self.work_centers = {}
        for wc_id in range(1, self.num_work_centers + 1):
            # Each WorkCenter gets its assigned strategy
            wc_strategy = self.workcenter_strategies.get(wc_id, "FIS")
            #need to add code for custom strategies for each workcenter

            self.work_centers[wc_id] = WorkCenter(
                self.env,
                wc_id,
                self.num_machines[wc_id-1],
                strategy=wc_strategy
            )

        # Initialize job creator and link to machines
        self.job_creator = JobCreator(
            self.env,
            self.work_centers,
            num_work_centers=len(self.work_centers)
        )

        for wc in self.work_centers.values():
            for machine in wc.machines:
                machine.job_creator = self.job_creator


    def pause_and_collect_workcenter_states(self) -> Dict[int, Dict]:
        """Pause simulation and collect WorkCenter states"""
        # print(f"Pausing simulation at time: {self.env.now}")

        recent_collector  = RecentMetricsCollector(self.env, self.job_creator, time_window=240)
        recent_metrics = recent_collector.calculate()
        # recent_collector.print_metrics()
        self.recent_metric = recent_metrics

        workcenter_states = {}

        for wc_id, wc in self.work_centers.items():
            machine_states = []
            tempupper = 0
            templower = 0
            for machine in wc.machines:
                queue_sorted = machine.get_sorted_queue()
                if wc_id == 1:
                  self.wc1_count_lower +=machine.temp_lower
                  self.wc1_count_upper +=machine.temp_upper
                elif wc_id == 2:
                  self.wc1_count_lower +=machine.temp_lower
                  self.wc1_count_upper +=machine.temp_upper
                else:
                  self.wc3_count_lower += machine.temp_lower
                  self.wc3_count_upper += machine.temp_upper

                machine_state = wc.get_machine_state(machine, queue_sorted, self.env.now)
                machine_states.append(machine_state)

            # Combine first two machines' states (adjust as needed)
            wc_state = wc.get_workcenter_states(machine_states, max(self.num_machines))
            workcenter_states[wc_id] = wc_state
            # print(f"Workcenter {wc_state}")
            # self.print_state(wc_state)

        return workcenter_states

    def evaluate_workcenter_strategy_combinations(self, current_time: float):
        """Evaluate different strategy combinations across WorkCenters"""
        strategy_results = {}

        # Test each strategy on each WorkCenter individually
        for strategy in self.strategies:
            for test_wc_id in self.work_centers.keys():
                # Create strategy configuration: one WorkCenter gets test strategy,
                # others keep their current strategy
                wc_strategies = {}
                for wc_id in self.work_centers.keys():
                    if wc_id == test_wc_id:
                        wc_strategies[wc_id] = strategy
                    else:
                        wc_strategies[wc_id] = self.work_centers[wc_id].workcenter_strategy

                strategy_name = f"WC{test_wc_id}_{strategy}"
                print(f"  Evaluating strategy combination: {strategy_name}")

                # Run sub-simulation with this strategy combination
                sub_sim = EnhancedSubSimulation(
                    main_coordinator=self,
                    workcenter_strategies=wc_strategies,
                    duration=self.evaluation_duration,
                    current_time=current_time
                )

                metrics = sub_sim.run()

                strategy_results[strategy_name] = {
                    'sub_simulation': sub_sim,
                    'metrics': metrics,
                    'wc_strategies': wc_strategies,
                    'test_wc_id': test_wc_id,
                    'test_strategy': strategy,
                    'final_states': sub_sim._capture_final_states(),
                }

        return strategy_results

    def store_workcenter_experiences_and_find_optimal(self, initial_wc_states: Dict[int, Dict],
                                                     strategy_results: Dict[str, Dict]) -> Dict[int, str]:
        """Store WorkCenter experiences and identify optimal strategies"""

        optimal_strategies = {}

        for wc_id in self.work_centers.keys():
            wc_experiences = []

            # Find results where this WorkCenter was tested
            for result_name, result_data in strategy_results.items():
                if result_data['test_wc_id'] == wc_id:
                    # Calculate WorkCenter-specific reward
                    sub_sim = result_data['sub_simulation']
                    wc_reward = sub_sim.calculate_workcenter_reward(wc_id)

                    experience = WorkCenterExperience(
                        workcenter_id=wc_id,
                        state=initial_wc_states[wc_id].copy(),
                        action=result_data['test_strategy'],
                        reward=wc_reward,
                        next_state=sub_sim.final_workcenter_states[wc_id].copy(),
                        timestamp=self.env.now,
                        episode=self.current_episode
                    )

                    wc_experiences.append(experience)
                    self.wc_experience_memory.push(experience)

            # Find optimal strategy for this WorkCenter (minimum reward)
            if wc_experiences:
                optimal_exp = min(wc_experiences, key=lambda x: x.reward)
                self.wc_optimal_memory.add_optimal_experience(optimal_exp)
                optimal_strategies[wc_id] = optimal_exp.action

                print(f"WorkCenter {wc_id}: Optimal Strategy = {optimal_exp.action}, "
                      f"Reward = {optimal_exp.reward:.2f}")

        return optimal_strategies

    def update_workcenter_strategies(self, optimal_strategies: Dict[int, str]):
        """Update WorkCenter strategies based on optimal results"""
        for wc_id, optimal_strategy in optimal_strategies.items():
            self.work_centers[wc_id].update_workcenter_strategy(optimal_strategy)
            self.workcenter_strategies[wc_id] = optimal_strategy

    def run_main_simulation_interval(self):
        """Run main simulation for one interval (4 hours)"""
        start_time = self.env.now
        target_time = start_time + self.interval_duration

        print(f"Running main simulation from {start_time} to {target_time}")

        # Ensure all machines are processing
        for wc in self.work_centers.values():
            for machine in wc.machines:
                # print(f"inside machine case  just cheking {self.env.now} and {machine.is_idle} ")
                if machine.queue and machine.is_idle:
                    # print(f"Queue Size of machine {machine.machine_id}: {len(machine.queue)}at  time {self.env.now}")
                    machine.env.process(machine.process_jobs())

                # else : print("not ran from th pause this")

        # Run until target time
        self.env.run(until=target_time)




    def train(self):
        """Main training loop with pause-resume approach"""
        print("Starting Simulation with WorkCenter Strategy Management...")
        print(f"Input Parameters:")
        print(f"  Intervals : {self.num_episodes}")
        print(f"  Interval Duration: {self.interval_duration/3600} hours")
        print(f"  Future Duration: {self.evaluation_duration/3600} hours")
        print(f"  Strategies: {self.strategies}")

        for episode in range(self.num_episodes):
            self.current_episode = episode
            print(f"\n{'='*60}")
            print(f"Episode {episode + 1}/{self.num_episodes}")
            print(f"{'='*60}")

            # Reset environment for new episode if needed
            if episode == 0:
                self.initialize_environment()

            interval_count = 0
            max_intervals = 6  # Run for 24 hours total (6 * 4 hours)

            while interval_count < max_intervals:
                interval_count += 1
                print(f"\n--- Interval {interval_count}/{max_intervals} ---")

                # Step 1: Run main simulation for 4 hours
                self.run_main_simulation_interval()

                # Step 2: Pause and collect WorkCenter states

                initial_wc_states = self.pause_and_collect_workcenter_states()

                # Step 3: Run strategy evaluations with sub-simulations
                strategy_results = self.evaluate_workcenter_strategy_combinations(self.env.now)

                # Step 4: Store experiences and find optimal strategies
                optimal_strategies = self.store_workcenter_experiences_and_find_optimal(
                    initial_wc_states, strategy_results)

                # # Step 5: Update WorkCenter strategies for next interval
                self.update_workcenter_strategies(optimal_strategies)

                # Print interval summary
                self._print_interval_summary(interval_count, optimal_strategies)

            # Print episode summary
            self._print_episode_summary(episode)

        print("\nTraining Complete!")
        # self.save_results()




    def _print_interval_summary(self, interval: int, optimal_strategies: Dict[int, str]):
        """Print interval summary"""
        print(f"\nInterval {interval} Complete:")
        print(f"  Current Time: {self.env.now}")
        print(f"  Optimal Strategies: {optimal_strategies}")
        print(f"  Total WC Experiences: {len(self.wc_experience_memory)}")
        print(f"  Optimal WC Experiences: {len(self.wc_optimal_memory.optimal_experiences)}")

    def _print_episode_summary(self, episode: int):
        """Print episode summary"""
        completed_jobs = len([j for j in self.job_creator.created_jobs if j.completion_status])
        total_jobs = len(self.job_creator.created_jobs)

        print(f"\nEpisode {episode + 1} Complete:")
        print(f"  Simulation Time: {self.env.now}")
        print(f"  Jobs Completed: {completed_jobs}/{total_jobs}")
        print(f"  Total WC Experiences: {len(self.wc_experience_memory)}")
        print(f"  Optimal WC Experiences: {len(self.wc_optimal_memory.optimal_experiences)}")


    def print_state(self, state: Dict):
      print(f"\n=== WorkCenter State Report ===")
      print(f"=== Machine 1 Metrics ===")
      print(f"**Queue Status**")
      print(f"- Jobs in queue: {state['num_jobs_m1']}")
      print(f"- Total processing time: {state['processing_time']['sum_m1']:.2f} min")

      print(f"\n**Processing Time Analysis**")
      print(f"- Range: {state['processing_time']['min_m1']:.2f} to {state['processing_time']['max_m1']:.2f} min")
      print(f"- Average: {state['processing_time']['avg_m1']:.2f} min")
      print(f"- Distribution:")
      # print(f"  Short (<1.5min): {state['processing_time_distribution']['<1.5_m1']:.2f}%")
      # print(f"  Medium (1.5-3min): {state['processing_time_distribution']['1.5-3_m1']:.2f}%")
      # print(f"  Long (3-4.5min): {state['processing_time_distribution']['3-4.5_m1']:.2f}%")
      # print(f"  Extra Long (>4.5min): {state['processing_time_distribution']['>4.5_m1']:.2f}%")

      print(f"\n**Time Analysis**")
      print(f"- Slack time: {state['slack_time']['avg_m1']:.2f} min (avg)")
      print(f"- Due date tightness: {state['due_date_tightness']['sum_m1']:.2f} min")
      print(f"- Remaining time: {state['remaining_time']['avg_m1']:.2f} min (avg)")

      print(f"\n=== Machine 2 Metrics ===")
      print(f"**Queue Status**")
      print(f"- Jobs in queue: {state['num_jobs_m2']}")
      print(f"- Total processing time: {state['processing_time']['sum_m2']:.2f} min")

      print(f"\n**Processing Time Analysis**")
      print(f"- Range: {state['processing_time']['min_m2']:.2f} to {state['processing_time']['max_m2']:.2f} min")
      print(f"- Average: {state['processing_time']['avg_m2']:.2f} min")
      print(f"- Distribution:")
      # print(f"  Short (<1.5min): {state['processing_time_distribution']['<1.5_m2']:.2f}%")
      # print(f"  Medium (1.5-3min): {state['processing_time_distribution']['1.5-3_m2']:.2f}%")
      # print(f"  Long (3-4.5min): {state['processing_time_distribution']['3-4.5_m2']:.2f}%")
      # print(f"  Extra Long (>4.5min): {state['processing_time_distribution']['>4.5_m2']:.2f}%")

      print(f"\n**Time Analysis**")
      print(f"- Slack time: {state['slack_time']['avg_m2']:.2f} min (avg)")
      print(f"- Due date tightness: {state['due_date_tightness']['sum_m2']:.2f} min")
      print(f"- Remaining time: {state['remaining_time']['avg_m2']:.2f} min (avg)")

      print(f"\n=== System Variability ===")
      print(f"**Processing Time Variation**")
      print(f"- Machine 1: {state['coeff_variation_pt_m1']:.4f}")
      print(f"- Machine 2: {state['coeff_variation_pt_m2']:.4f}")

      print(f"\n**Remaining Time Variation**")
      print(f"- Machine 1: {state['coeff_variation_rt_m1']:.4f}")
      print(f"- Machine 2: {state['coeff_variation_rt_m2']:.4f}")


