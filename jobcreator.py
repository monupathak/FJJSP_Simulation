import simpy
import random   
from typing import Dict, Optional
from job import Job
from workcenter import WorkCenter
# from routing_agent import DRLAwareRoutingAgent      



class JobCreator:
    def __init__(self, env: simpy.Environment, work_centers: Dict[int, 'WorkCenter'],
                 num_work_centers: int, target_utilization: float = 1.02,
                 current_time: int = 0):
        self.env = env
        self.work_centers = work_centers
        self.num_work_centers = num_work_centers
        self.target_utilization = target_utilization
        self.job_counter = 0
        # self.rng = random.seed(2)
        self.created_jobs = []
        # self.routing_agent = routing_agent
        self.env.process(self.create_jobs())
        self.collect =  True

    def create_jobs(self):
        while True:
            mean_processing_time = 4.5
            mean_operations = 3
            total_machines = sum(len(wc.machines) for wc in self.work_centers.values())

            arrival_rate = 0.9*(self.target_utilization * total_machines) / \
                          (mean_processing_time * mean_operations)
            inter_arrival_time = max(0.01, random.expovariate(arrival_rate))
            # inter_arrival_time = max(0.01, random.expovariate(0.533))
            # inter_arrival_time = random.expovariate(0.533)
            # inter_arrival_time  = 1/0.5
            yield self.env.timeout(inter_arrival_time)
            job = self.generate_random_job()
            job.start_time = self.env.now
            self.created_jobs.append(job)
            self.route_job(job)



    def route_job(self, job):
        if job.current_op_idx >= len(job.routing):
            print(f"-------------------------------Job {job.job_id} has completed all operations----------------------")
            return -1
        # if job.completion_status : print(f"-------------------------------Job {job.job_id} has completed all operations----------------------")

        selected_wc = job.routing[job.current_op_idx]


        # print(f"Processing Job ID {self.job_id} operation {self.current_op_idx} at WC({selected_wc}) ")
        # selected_mc = self.all_work_centers[selected_wc].shortest_queue_pt()
        # selected_mc = self.all_work_centers[selected_wc].earliest_available()
        # self.all_work_centers[selected_wc].queue_status()

        # selected_mc = self.all_work_centers[selected_wc].shortest_queue_length()
        selected_mc = self.work_centers[selected_wc].shortest_queue_length()

        selected_mc.add_to_machine_queue(job)

        # print(f"-----Job with job {job.job_id} is added to the queue of machine {selected_mc.machine_id}")
        # selected_mc.get_queue_status()
        # if selected_mc.is_idle :
          # print(f"Inside job creator and activating from here at {self.env.now}")
          # selected_mc.env.process(selected_mc.process_jobs())


    def generate_random_job(self) -> Job:
        self.job_counter += 1
        num_operations = random.randint(1, self.num_work_centers)

        # route for different job
        type_a = [1,2,3]
        type_b = [2,3,1]
        type_c = [3,1,2]
        prob= random.random()
        # prob = 0.1
        typ_ = 0

        if prob<= 0.33:
          routing = type_a
          typ_ = 1

        elif prob > 0.33 and prob <= 0.66 :
          routing = type_b
          typ_ = 2
        else :
          routing = type_c
          typ_ = 3

        processing_time = []

        for wc_id in routing:
            wc = self.work_centers[wc_id]
            # num_eligible = random.randint(1, len(wc.machines))
            eligible_machines = wc.machines

            pt_dict = {}

            for machine in eligible_machines:
                pt_dict[machine.machine_id] = random.uniform(3, 6)
                # pt_dict[machine.machine_id] = 4.5


            processing_time.append(pt_dict)

        # Calculate due date based on slack
        slack = sum(min(pt.values()) for pt in processing_time) * 9
        due_date = self.env.now + slack
        # due_date = self.env.now + 6
        # print(f"Time :{self.env.now} Job {self.job_counter}: Route {routing}, Processing Times: {processing_time}, Due: {due_date:.2f}")


        return Job(
            job_id=self.job_counter,
            routing=routing,
            processing_time=processing_time,
            due_date=due_date,
            # Remove this line: all_work_centers=self.work_centers,
            # routing_agent=None,  # Also remove routing_agent if it contains generators
            typ=typ_)

