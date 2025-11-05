import simpy 
import random
from typing import List, Optional, Dict, Tuple, Callable
from job import Job
from sequencing_agent import SequencingAgent


class Machine:
    def __init__(self, env, resource, breakdown_mean, repair_time, machine_id, wc_id,  strategy: str = None,  initial_queue: List = None, sequenceing_agent: SequencingAgent = SequencingAgent("FIS")):
        self.env = env
        self.resource = resource
        self.breakdown_mean = breakdown_mean
        self.repair_time = repair_time
        self.machine_id = machine_id
        self.wc_id = wc_id
        self.is_broken = False
        self.processing_job = None
        self.breakdown_count = 0
        self.total_working_time = 0.0
        self.total_idle_time = 0.0
        self.last_activity_time = 0.0
        self.queue = initial_queue if initial_queue is not None else []
        self.next_available_time = 0.0
        self.scheduled_jobs = []
        self.env.process(self.breakdown_process())
        # self.env.process(self.process_jobs())
        self.repair_dur = 0
        self.start_time = self.env.now
        self.cur_st = 1
        self.sequenceing_agent = SequencingAgent("FIS")

        self.is_idle = True
        self.job_creator = None
        # self.strategy = strategy if strategy is not None else []
        self.strategy = strategy if strategy else "SPT"
        print(self.strategy)
        self.count_lower = 0  # Jobs processed in <=5 mins
        self.count_upper = 0  # Jobs processed in >5 mins
        self.temp_lower = 0   # Per-shift counter for <=5 mins
        self.temp_upper = 0   # Per-shift counter for >5 mins
        self.shift_duration = 60*4  # 4-hour shifts

        self.state_history = []
        self.last_state = None
        self.queue_buildup_time = 0

    def breakdown_process(self):
        while True:
            yield self.env.timeout(random.expovariate(1.0 / self.breakdown_mean))
            if not self.is_broken and self.processing_job:
                print(f"Machine {self.machine_id} breakdown at {self.env.now}")
                self.is_broken = True
                self.breakdown_count += 1
                repair_duration = max(1, random.normalvariate(self.repair_time, self.repair_time/4))
                self.repair_dur = repair_duration
                yield self.env.timeout(repair_duration)
                self.next_available_time += repair_duration
                self.is_broken = False
                self.repair_dur = 0
                print(f"Machine {self.machine_id} repaired at {self.env.now}")

                #again run process

    def get_available_time(self):
      #Calculate the total available time for this machine from a given start time
      total_time = 0
      Q_t = 0
      M_R = 0
      # repair time if machine is broken
      if self.is_broken:
          total_time += self.repair_dur

      # processing time for all queued jobs
      for job in self.queue:
          if self.machine_id in job.processing_time[job.current_op_idx]:
              Q_t += job.processing_time[job.current_op_idx][self.machine_id]
      # remaining processing time of current job
      if self.processing_job and self.machine_id in self.processing_job.processing_time[self.processing_job.current_op_idx]:
          M_R += (self.processing_job.processing_time[self.processing_job.current_op_idx][self.machine_id] -
                        (self.env.now - self.start_time))
      total_time = Q_t + M_R
      # print(f"available time of machine{self.machine_id} is -->{total_time} Q_t = {Q_t} M_R = {M_R}")
      # print(f"processing { self.processing_job.processing_time[self.processing_job.current_op_idx][self.machine_id]}, env.now {self.env.now} self.start {self.start_time}")
      # print(f"processing { self.processing_job}, env.now {self.env.now} self.start {self.start_time}")

      return total_time



    def get_sorted_queue(self, queue: Optional[List[Job]] = None, strategy: Optional[str] = None, machine_id: Optional[int] = None) -> List[Job]:
        if queue is None:
            queue = self.queue
        if strategy is None:
            strategy = self.strategy[0]
        if machine_id is None:
            machine_id = self.machine_id
        # sorted_queue = copy.deepcopy(queue)  # make a copy to avoid modifying the original
        sorted_queue = list(queue)
        if strategy == 'SPT':  # Shortest Processing Time
            sorted_queue.sort(key=lambda job: job.processing_time[job.current_op_idx][machine_id])

        elif strategy == 'FIFO':  # First In First Out (keep original order)
            pass  # no sorting needed

        elif strategy == 'EDD':  # Earliest Due Date
            sorted_queue.sort(key=lambda job: job.due_date)

        elif strategy == 'FIS':  # First In System
            sorted_queue.sort(key=lambda job: job.job_id)

        elif strategy == 'LPT':  # Longest Processing Time
            sorted_queue.sort(key=lambda job: job.processing_time[job.current_op_idx][machine_id], reverse=True)

        return sorted_queue

    def total_process_time_remain(self, machine, job):
        """Calculate total remaining processing time for a job"""
        # Current operation processing time
        sigma_tji = job.processing_time[job.current_op_idx][machine.machine_id]

        # Remaining operations processing time
        r_tij = 0
        if job.current_op_idx < len(job.processing_time) - 1:
            # Sum expected processing times from next operation to end
            for op_index in range(job.current_op_idx + 1, len(job.processing_time)):
                op = job.processing_time[op_index]  # Fixed: was job.processing_time[op]
                for machine_id, time in op.items():
                    r_tij += time
            r_tij = r_tij / 2 # Average across machines

        return sigma_tji + r_tij

    def get_expected_slack_sequencing(self, machine, queue_sorted: List[Job], current_time):
        """
        Calculate expected slack times for jobs in sorted queue

        Parameters:
        - machine: Machine object
        - queue_sorted: List of jobs sorted by selected strategy
        - current_time: Current simulation time
        - env_now: Environment current time
        """

        slack_times = {}
        sl = []
        p_t = []

        # Calculate machine available time (when current job will finish)
        exp_mc_av = 0
        if self.processing_job and self.machine_id in self.processing_job.processing_time[self.processing_job.current_op_idx]:
          exp_mc_av += (self.processing_job.processing_time[self.processing_job.current_op_idx][self.machine_id] -
                        (self.env.now - self.start_time))
        # exp_mc_av = max(0, exp_mc_av)  # Ensure non-negative

        print(f"\n=== Expected Slack Times for Machine {machine.machine_id} ===")
        print(f"Given Sequence:f{self.strategy}")
        print(f"Queue sequence: {[job.job_id for job in queue_sorted]}")
        print(f"Current time: {current_time}")
        print(f"Machine Available time: {exp_mc_av}")
        print(f"Initial machine available time: {exp_mc_av:.2f}")

        # Calculate slack for each job in the sorted queue
        for idx, job in enumerate(queue_sorted):
            # Get total remaining processing time for this job
            total_remaining_time = self.total_process_time_remain(machine, job)

            # Calculate expected slack time
            # Slack = Due Date - Current Time - Machine Available Time - Total Remaining Processing Time
            slack = job.due_date - current_time - exp_mc_av - total_remaining_time

            #processing time of current job
            p = job.processing_time[job.current_op_idx][machine.machine_id]
            # Update machine available time for next job
            exp_mc_av += p
            sl.append(slack)
            # Store slack time
            slack_times[job.job_id] = slack

            print(f"Job ID: {job.job_id}, Position: {idx}, "
                  f"Due Date: {job.due_date}, "
                  f"Total Remaining Time: {total_remaining_time:.2f}, "
                  f" Current Job Processing time {job.processing_time[job.current_op_idx][machine.machine_id]}, "
                  f"Expected Slack Time: {slack:.2f}")

        return slack_times

    # i think there is some issue with the implemenation of the function below
    # to calculate the expected available time of machine for ith operation of a job
    def get_expected_available_time(self, job):

        if job.current_op_idx >= len(job.processing_time):
            return 0

        operation = job.processing_time[job.current_op_idx]
        count = 0
        total_time = 0

        for machine_id, processing_time in operation.items():
            count += 1

            # Use current time as start_time
            total_time += self.get_available_time() #  suspected i think this approach is incorrect

        if count == 0:
            return 0

        return total_time / count


    # this is the function to calculate the expected processing time of a job
    # i think there is some issue with the implemenation of the function below
    def get_exp_processing_time(self, idx, job: Job):

        if job.current_op_idx >= len(job.processing_time):
            return 0

        operation = job.processing_time[job.current_op_idx]
        count = 0
        total_time = 0
        for machine_id, processing_time in operation.items():
            count += 1
            total_time += processing_time
        if count == 0:
            return 0

        return total_time / count

    # calclulating the expected slack (E(st+1,i))
    #as TDD(i) = DD(i) - Now
    def expected_slack(self, job: Job, start_index: int):
        sigma_tji = 0

        for op_index in range(start_index, len(job.processing_time)):
            sigma_tji += self.get_exp_processing_time(op_index, job)

        exp_mc_av = self.get_expected_available_time(job)

        exp_t = job.due_date - self.env.now - sigma_tji - exp_mc_av
        # print(f"job.due_date {job.due_date} - self.env.now {self.env.now} - sigma_tji{sigma_tji} exp_mc_av {exp_mc_av}")
        return exp_t


    def expected_slack_sequencing(self, job: Job, start_index: int):
        sigma_tji = 0
        que =  self.get_sorted_queue(self.machine, self.strategy[self.cur_st -1])

        for op_index in range(start_index, len(job.processing_time)):
            sigma_tji += self.get_exp_processing_time(op_index, job)

        exp_mc_av = self.get_expected_available_time(job)

        exp_t = job.due_date - self.env.now - sigma_tji - exp_mc_av
        # print(f"job.due_date {job.due_date} - self.env.now {self.env.now} - sigma_tji{sigma_tji} exp_mc_av {exp_mc_av}")
        return exp_t

    def actual_slack(self, job: Job, start_index: int):
        if start_index >= len(job.processing_time) : return job.due_date - self.env.now
        sigma_tji = 0

        #  just call this funtion after the process completes then there will be an increment in the current operation index
        for op_index in range(start_index, len(job.processing_time)):

            sigma_tji += self.get_exp_processing_time(op_index, job)

        exp_t = job.due_date - self.env.now - sigma_tji

        return exp_t


    def add_to_machine_queue(self, job: Job):
        self.queue.append(job)
        # print(f"Queue in front of machine{self.machine_id}")
        # for j in self.queue:
        #   print(f"---------------------- Job ID---{j.job_id} PT---{j.processing_time[j.current_op_idx][self.machine_id]}")
        # print(f"Job {job.job_id} added to queue of machine {self.machine_id}")

    def total_mc_pt(self):
        return sum(j.processing_time[j.current_op_idx][self.machine_id] for j in self.queue)

    def get_queue_status(self):
      print(f"Queue in front machine {self.machine_id}")
      for job in self.queue:
          if self.machine_id in job.processing_time[job.current_op_idx]:
              print(f" Time : {self.env.now} Job Id---", job.job_id," PT---", job.processing_time[job.current_op_idx][self.machine_id], "DD---", job.due_date)

    # working fine as commented the breakdown thing and rework thing # i thing rework is not important enought
    def process_jobs(self):

        while True and self.env.now > 120:
            if self.is_idle == True:
              print(f"Machine Starting time is : {self.env.now}")
            # self.get_queue_status()
            # Check for shift change
            # if self.env.now >= 60:
            #     self.get_queue_status()

                # if self.queue : self.get_queue_status()
                # else : print("Empty Queue")
                # Print slack times if queue exists
                # queue_sorted = self.get_sorted_queue(self.queue, self.strategy, self.machine_id)
                # self.get_expected_slack_sequencing( self, queue_sorted, self.env.now)

            # if self.queue:
            #     queue_sorted = self.get_sorted_queue(self, self.strategy)
            #     slack_times = self.get_expected_slack_sequencing(
            #         self, queue_sorted, self.env.now, self.env.now,
            #         self.get_exp_processing_time, self.get_available_time_for_job
            #     )
            # else:
            #     print("No jobs in queue at shift change.")



            # Wait if queue is empty

            while not self.queue:
                self.is_idle = True
                yield self.env.timeout(0.01)  # Small timeout to prevent busy waiting

            # Process next job
            if self.queue:
                self.is_idle = False
                # job = self.queue.pop(0)
                # self.get_queue_status()
                # queue_sorted = self.get_sorted_queue(self.queue, self.strategy, self.machine_id)
                # self.get_expected_slack_sequencing( self, queue_sorted, self.env.now)
            # else:
            #     print("No jobs in queue at shift change.")

                # job = self.sequenceing_agent.select(self.strategy)
                # self.get_queue_status()
                # print(self.strategy)
                job = self.sequenceing_agent.select(self, self.strategy)
                # print(f"---Time {self.env.now}: Strategy : {self.strategy} Job {job.job_id} Selected on Machine {self.machine_id} (WC {self.wc_id}) DD--- {job.due_date}")
                if self.machine_id not in job.processing_time[job.current_op_idx]:continue
                    # print(f"ERROR: Machine {self.machine_id} not eligible for Job {job.job_id} operation {job.current_op_idx}")
                    # print()
                    # continue

                processing_time = job.processing_time[job.current_op_idx][self.machine_id]

                try:
                    # Request resource for this specific job
                    with self.resource.request(priority=0) as req:
                        yield req
                        self.start_time = self.env.now
                        # Now we have the resource, process the job
                        # print(f"Time {self.env.now}: Job {job.job_id} starts on Machine {self.machine_id} (WC {self.wc_id})")

                        job.record_operation_start(self.env.now, self.wc_id, self.machine_id)
                        self.processing_job = job
                        start_time = self.env.now
                        # print("---------------START TIME-----------------------",self.start_time)
                        self.next_available_time = start_time + processing_time

                        if self.last_activity_time < self.env.now:
                            self.total_idle_time += self.env.now - self.last_activity_time

                        # Process the job
                        yield self.env.timeout(processing_time)
                        # yield self.env.timeout(2)
                        self.scheduled_jobs.append({
                            'job_id': job.job_id,
                            'start': start_time,
                            'end': self.env.now
                        })


                        if processing_time > 5:
                            self.count_upper += 1
                            self.temp_upper += 1
                        else:
                            self.count_lower += 1
                            self.temp_lower += 1

                        # Job completed
                        if not self.is_broken:
                            self.total_working_time += processing_time
                            self.last_activity_time = self.env.now
                            self.processing_job = None
                            # self.start_time = self.env.now


                            job.record_operation_end(self.env.now)
                            # print(f"-----------Time {self.env.now}: Job {job.job_id} completed on Machine {self.machine_id} (WC {self.wc_id})")

                            if not job.is_completed():
                                self.job_creator.route_job(job)

                            # commented for removing print
                            # if job.is_completed() :

                              # print(f"-------------------------------Job {job.job_id} has completed all operations----------------------")
                              # print(f"Due date : {job.due_date}")
                              # print(f"Compeletion_time = {job.end_time}  current time =  {self.env.now}   tardiness = {job.due_date  -job.end_time}")
                            # else :
                            #    prob = random.uniform(0.1, 1.0)
                            #    if  prob <= 0.7 and not job.rework :
                            #       job.rework = True
                            #       job.current_op_idx -= 1
                            #       print(f"---------------------------------------------------------------------------{job.current_op_idx}--------------------------------------")
                            #       job.route_job()

                        # Resource is automatically released when exiting 'with' block

                except simpy.Interrupt:
                    self.queue.insert(0, job)
                    self.processing_job = None
                    print(f"Time {self.env.now}: Breakdown interrupted Job {job.job_id} on Machine {self.machine_id}")

