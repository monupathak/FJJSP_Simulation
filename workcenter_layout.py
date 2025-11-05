from workcenter import WorkCenter
from typing import Dict

class WorkshopLayout:
    def __init__(self, work_centers: Dict[int, 'WorkCenter']):
        self.work_centers = work_centers

    def print_layout(self):
        print("\n=== Workshop Layout ===")
        for wc_id, wc in self.work_centers.items():
            print(f"\nWorkCenter {wc_id}:")
            print(f"  Machines: {len(wc.machines)}")
            print(f"  Machine IDs: {[m.machine_id for m in wc.machines]}")
            # print(f"  Sequencing: {wc.sequencing_agent.strategy}")
        print("\n")

