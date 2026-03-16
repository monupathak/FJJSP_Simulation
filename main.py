import argparse
import random
from coordinator.training_coordinator import PauseResumeTrainingCoordinator
from simulation.workcenter_layout import WorkshopLayout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FJJSP simulation.")
    parser.add_argument(
        "--mode",
        choices=["train", "infer"],
        default="train",
        help="Run training loop (train) or inference-only rollout (infer).",
    )
    parser.add_argument(
        "--intervals",
        type=int,
        default=6,
        help="Number of intervals to run (both train and infer modes).",
    )
    return parser.parse_args()


def main():
    """Main function to run training or inference."""
    args = parse_args()
    random.seed(42)

    # Define configuration
    num_work_centers = 3
    num_machines = [2, 3, 2]

    # Display system layout before initialization
    WorkshopLayout.display_configuration(num_work_centers, num_machines)

    # Create coordinator
    trainer = PauseResumeTrainingCoordinator(
        num_work_centers=num_work_centers,
        num_machines=num_machines,
    )

    # Display detailed layout after WorkCenters are initialized
    layout = WorkshopLayout(trainer.work_centers)
    layout.display_layout_visual()

    # Run requested mode
    if args.mode == "train":
        trainer.train(max_intervals=args.intervals)
    else:
        trainer.run_inference(max_intervals=args.intervals)


if __name__ == "__main__":
    main()
