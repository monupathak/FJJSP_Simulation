import simpy
import pickle
import statistics
from typing import Dict
from jobcreator import JobCreator
from workcenter import WorkCenter


class MetricsCollector:
    def __init__(self, env: simpy.Environment, job_creator: JobCreator,
                 work_centers: Dict[int, 'WorkCenter']):
        self.env = env
        self.job_creator = job_creator
        self.work_centers = work_centers
        self.metrics = {
            'tardiness': [],
            'recent_tardiness' :0,
            'total_tardiness': 0,
            'max_tardiness': 0,
            'mean_tardiness': 0,
            'makespan': 0,
            'total_flow_time': 0,
            'avg_flow_time': 0,
            'throughput': 0,
            'wip': [],
            'machine_utilization': [],
            'machine_idle_ratio': []
        }
        # self.env.process(self.collect_metrics())
        self.recent_metric = {}

    def save_jobs(self, filename='created_jobs.pkl'):
        """Save the created jobs list to a pickle file"""
        with open(filename, 'wb') as f:
            pickle.dump(self.job_creator.created_jobs, f)
        print(f"Jobs saved successfully to {filename}")

    def load_jobs(self, filename='created_jobs.pkl'):
        """Load the created jobs list from a pickle file"""
        try:
            with open(filename, 'rb') as f:
                self.job_creator.created_jobs = pickle.load(f)
            print(f"Jobs loaded successfully from {filename}")
        except FileNotFoundError:
            print(f"File {filename} not found")
        except Exception as e:
            print(f"Error loading jobs: {e}")


    def collect_metrics(self):
        while True:
            current_wip = sum(1 for job in self.job_creator.created_jobs if not job.completion_status)
            self.metrics['wip'].append((self.env.now, current_wip))

            for wc in self.work_centers.values():
                for machine in wc.machines:
                    total_time = machine.total_working_time + machine.total_idle_time
                    if total_time > 0:
                        utilization = machine.total_working_time / total_time
                        idle_ratio = machine.total_idle_time / total_time
                        self.metrics['machine_utilization'].append(utilization)
                        self.metrics['machine_idle_ratio'].append(idle_ratio)
            # yield self.env.timeout(10)

    def finalize_metrics(self):
        # self.save_jobs()
        completed_jobs = [job for job in self.job_creator.created_jobs if job.completion_status]
        if not completed_jobs:
            return
        if self.env.now < 240 : recent_completed_jobs = [job for job in self.job_creator.created_jobs if job.completion_status ]
        else :
          recent_completed_jobs = [job for job in self.job_creator.created_jobs if job.completion_status and job.end_time >= self.env.now -240]
        print("recenly completed jobs :", len(recent_completed_jobs))


        self.metrics['tardiness'] = [job.calculate_tardiness() for job in completed_jobs]
        self.metrics['total_tardiness'] = sum(self.metrics['tardiness'])
        self.metrics['max_tardiness'] = max(self.metrics['tardiness']) if self.metrics['tardiness'] else 0
        self.metrics['mean_tardiness'] = statistics.mean(self.metrics['tardiness'])

        flow_times = [job.calculate_flow_time() for job in completed_jobs]
        self.metrics['total_flow_time'] = sum(flow_times)
        self.metrics['avg_flow_time'] = statistics.mean(flow_times) if flow_times else 0

        simulation_time = self.env.now
        self.metrics['throughput'] = len(completed_jobs) / simulation_time if simulation_time > 0 else 0
        self.metrics['makespan'] = max(job.end_time for job in completed_jobs) if completed_jobs else 0

        # if self.metrics['wip']:
        #     times, wips = zip(*self.metrics['wip'])
        #     total_time = times[-1] - times[0]
        #     if total_time > 0:
        #         wip_integral = sum((times[i] - times[i-1]) * wips[i-1] for i in range(1, len(times)))
        #         self.metrics['avg_wip'] = wip_integral / total_time

        if self.metrics['machine_utilization']:
            # self.metrics['avg_utilization'] = statistics.mean(self.metrics['machine_utilization'])
            self.metrics['avg_utilization'] = 0

        if self.metrics['machine_idle_ratio']:
            # self.metrics['avg_idle_ratio'] = statistics.mean(self.metrics['machine_idle_ratio'])
            self.metrics['avg_idle_ratio'] = 0

        # Calculate proportional processing time metrics
        # total_over_5min = sum(m.jobs_over_5min_total for wc in self.work_centers.values() for m in wc.machines)
        # total_under_5min = sum(m.jobs_under_5min_total for wc in self.work_centers.values() for m in wc.machines)
        # total_processed = total_over_5min + total_under_5min

        # if total_processed > 0:
        #     self.metrics.update({
        #         'proportion_long_jobs': total_over_5min / total_processed,
        #         'proportion_short_jobs': total_under_5min / total_processed,
        #         'total_jobs_processed': total_processed
        #     })

    def print_metrics(self):
        print("\n=== Simulation Metrics ===")
        print(f"Total Tardiness: {self.metrics['total_tardiness']:.2f}")
        print(f"Mean Tardiness: {self.metrics['mean_tardiness']:.2f}")
        print(f"Maximum Tardiness: {self.metrics['max_tardiness']:.2f}")
        print(f"Makespan: {self.metrics['makespan']:.2f}")
        print(f"Total Flow Time: {self.metrics['total_flow_time']:.2f}")
        print(f"Average Flow Time: {self.metrics['avg_flow_time']:.2f}")
        print(f"Throughput: {self.metrics['throughput']:.2f} jobs/time unit")
        # print(f"Average WIP: {self.metrics.get('avg_wip', 0):.2f}")
        # print(f"Average Machine Utilization: {self.metrics.get('avg_utilization', 0)*100:.1f}%")
        # print(f"Average Machine Idle Ratio: {self.metrics.get('avg_idle_ratio', 0)*100:.1f}%")
        print(f"Completed Jobs: {len([j for j in self.job_creator.created_jobs if j.completion_status])}")
        print(f"Created Jobs: {len(self.job_creator.created_jobs)}")


    def get_metrics_dict(self):
        return {
            "total_tardiness": round(self.metrics['total_tardiness'], 2),
            "mean_tardiness": round(self.metrics['mean_tardiness'], 2),
            "max_tardiness": round(self.metrics['max_tardiness'], 2),
            "makespan": round(self.metrics['makespan'], 2),
            "total_flow_time": round(self.metrics['total_flow_time'], 2),
            "avg_flow_time": round(self.metrics['avg_flow_time'], 2),
            "throughput": round(self.metrics['throughput'], 2),
            # Uncomment if needed:
            # "avg_wip": round(self.metrics.get('avg_wip', 0), 2),
            # "avg_utilization": round(self.metrics.get('avg_utilization', 0) * 100, 1),
            # "avg_idle_ratio": round(self.metrics.get('avg_idle_ratio', 0) * 100, 1),
            "completed_jobs": len([j for j in self.job_creator.created_jobs if j.completion_status]),
            "created_jobs": len(self.job_creator.created_jobs)
        }


    def calculate_recent_metrics(self, time_window=240):
        """Calculate metrics for jobs completed in the last `time_window` time units."""
        recent_jobs = [
            job for job in self.job_creator.created_jobs
            if job.completion_status and job.end_time >= self.env.now - time_window
        ]

        print(f"\n--- Recently Completed Jobs (last {time_window} time units): {len(recent_jobs)} ---")

        if not recent_jobs:
            print("No recently completed jobs.")
            return {}

        recent_tardiness = [job.calculate_tardiness() for job in recent_jobs]
        recent_flow_times = [job.calculate_flow_time() for job in recent_jobs]

        recent_metrics = {
            'recent_total_tardiness': sum(recent_tardiness),
            'recent_max_tardiness': max(recent_tardiness) if recent_tardiness else 0,
            'recent_mean_tardiness': statistics.mean(recent_tardiness) if recent_tardiness else 0,
            'recent_total_flow_time': sum(recent_flow_times),
            'recent_avg_flow_time': statistics.mean(recent_flow_times) if recent_flow_times else 0,
            'recent_throughput': len(recent_jobs) / time_window if time_window > 0 else 0
        }

        self.recent_metric = recent_metrics

        return recent_metrics

