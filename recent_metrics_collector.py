
import simpy
import statistics
from jobcreator import JobCreator



class RecentMetricsCollector:
    def __init__(self, env: simpy.Environment, job_creator: JobCreator, time_window: int = 240):
        self.env = env
        self.job_creator = job_creator
        self.time_window = time_window
        self.metrics = {}

    def calculate(self):
        """Calculate metrics for jobs completed in the last `time_window` time units."""
        recent_jobs = []
        if self.env.now < 240: recent_jobs = [
            job for job in self.job_creator.created_jobs
            if job.completion_status  ]
        else :
          recent_jobs = [
              job for job in self.job_creator.created_jobs
              if job.completion_status and job.end_time >= self.env.now - self.time_window
          ]

        print(f"\n--- Recently Completed Jobs (last {self.time_window} time units): {len(recent_jobs)} ---")

        if not recent_jobs:
            print("No recently completed jobs.")
            self.metrics.clear()
            return {}

        tardiness_list = [job.calculate_tardiness() for job in recent_jobs]
        flow_times = [job.calculate_flow_time() for job in recent_jobs]

        self.metrics = {
            'recent_total_tardiness': sum(tardiness_list),
            'recent_max_tardiness': max(tardiness_list),
            'recent_mean_tardiness': statistics.mean(tardiness_list),
            'recent_total_flow_time': sum(flow_times),
            'recent_avg_flow_time': statistics.mean(flow_times),
            'recent_throughput': len(recent_jobs) / self.time_window
        }

        return self.metrics

    def print_metrics(self):
        if not self.metrics:
            print("No recent metrics to display.")
            return

        print("\n=== Recent Metrics ===")
        print(f"Total Tardiness: {self.metrics['recent_total_tardiness']:.2f}")
        print(f"Max Tardiness: {self.metrics['recent_max_tardiness']:.2f}")
        print(f"Mean Tardiness: {self.metrics['recent_mean_tardiness']:.2f}")
        print(f"Total Flow Time: {self.metrics['recent_total_flow_time']:.2f}")
        print(f"Average Flow Time: {self.metrics['recent_avg_flow_time']:.2f}")
        print(f"Throughput: {self.metrics['recent_throughput']:.2f} jobs/time unit")

