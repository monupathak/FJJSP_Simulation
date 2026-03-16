from .workcenter import WorkCenter
from typing import Dict, List

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

    def display_layout_visual(self):
        """Display a visual representation of the workshop layout with WorkCenters and Machines"""
        print("\n" + "="*70)
        print(" "*20 + "WORKSHOP LAYOUT VISUALIZATION")
        print("="*70)
        
        for wc_id, wc in sorted(self.work_centers.items()):
            num_machines = len(wc.machines)
            
            # Print WorkCenter header
            print(f"\n┌{'─'*66}┐")
            print(f"│ WorkCenter {wc_id} ({num_machines} Machine{'s' if num_machines != 1 else ''})".ljust(67) + "│")
            print(f"├{'─'*66}┤")
            
            # Print machines in a grid layout
            machines_per_row = 4
            for i, machine in enumerate(wc.machines):
                if i % machines_per_row == 0:
                    print(f"│ ", end="")
                
                machine_str = f"[M{machine.machine_id}]"
                print(f"{machine_str:<12}", end="")
                
                if (i + 1) % machines_per_row == 0 or i == len(wc.machines) - 1:
                    remaining_spaces = (machines_per_row - ((i + 1) % machines_per_row if (i + 1) % machines_per_row != 0 else machines_per_row)) * 12
                    print(" " * remaining_spaces + "│")
            
            print(f"└{'─'*66}┘")
        
        print("\n" + "="*70)

    @staticmethod
    def display_configuration(num_work_centers: int, num_machines: List[int]):
        """Display the configuration summary before simulation starts"""
        print("\n" + "="*70)
        print(" "*15 + "SIMULATION CONFIGURATION - SYSTEM LAYOUT")
        print("="*70)
        
        print(f"\n📊 Total WorkCenters: {num_work_centers}")
        print(f"📊 Machine Distribution:")
        
        total_machines = 0
        for wc_id, num_m in enumerate(num_machines, 1):
            total_machines += num_m
            machine_visual = "🔧 " * num_m
            print(f"   WorkCenter {wc_id}: {num_m} Machine{'s' if num_m != 1 else ''} {machine_visual}")
        
        print(f"\n📊 Total Machines: {total_machines}")
        print("="*70 + "\n")

    @staticmethod
    def _get_machine_visual(num_machines: int) -> str:
        """Get visual representation of machines"""
        return "🔧 " * num_machines
