import random
from running_coordinator import PauseResumeTrainingCoordinator

def main():
    """Main function to run the pause-resume training"""
    random.seed(42)

    # Create and run trainer
    trainer = PauseResumeTrainingCoordinator(num_work_centers=3, num_machines=2)
    trainer.train()

if __name__ == "__main__":
    main()