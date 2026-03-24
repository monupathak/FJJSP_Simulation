import argparse
import os
import random
from typing import Dict, List

# Workaround for macOS / Conda OpenMP duplication when importing PyTorch
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

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
        "--rule",
        choices=["static", "dynamic"],
        default="dynamic",
        help="Set the rule type to either static or dynamic.",
    )
    parser.add_argument(
        "--intervals",
        type=int,
        default=6,
        help="Number of intervals to run (both train and infer modes).",
    )
    parser.add_argument(
        "--machines",
        default="2,3,2",
        help="Comma-separated machine counts per workcenter (e.g. '2,3,2').",
    )
    parser.add_argument(
        "--distributions",
        default="",
        help=(
            "Per-workcenter processing-time distributions. Format: "
            "'wc:dist:param1:param2,...' e.g. '1:normal:5:0.5,2:uniform:3:6'."
        ),
    )
    parser.add_argument(
        "--static-rules",
        default="",
        help=(
            "Only used when --rule static. Comma-separated list of 'wc:STRAT' "
            "(e.g. '1:SPT,2:EDD,3:FIS')."
        ),
    )
    parser.add_argument(
        "--target-utilization",
        type=float,
        default=1.02,
        help="Target system utilization used to derive job arrival rate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility.",
    )
    return parser.parse_args()


def _parse_machine_layout(machines_arg: str) -> List[int]:
    try:
        machines = [int(x) for x in machines_arg.split(',') if x.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--machines must be a comma separated list of integers"
        ) from exc
    if not machines:
        raise argparse.ArgumentTypeError("--machines cannot be empty")
    if any(m <= 0 for m in machines):
        raise argparse.ArgumentTypeError("Machine counts must be positive")
    return machines


def _parse_distributions(dist_arg: str, num_work_centers: int) -> Dict[int, Dict]:
    """Return per-WC distribution config with sensible defaults."""
    default = {
        wc_id: {"type": "uniform", "low": 3.0, "high": 6.0}
        for wc_id in range(1, num_work_centers + 1)
    }
    if not dist_arg:
        return default

    for item in dist_arg.split(','):
        parts = [p.strip() for p in item.split(':') if p.strip()]
        if len(parts) < 2:
            raise argparse.ArgumentTypeError(
                "Distribution entry must be 'wc:dist:param1:param2'"
            )
        wc_id = int(parts[0])
        dist_type = parts[1].lower()
        if wc_id < 1 or wc_id > num_work_centers:
            raise argparse.ArgumentTypeError(f"Invalid workcenter id {wc_id}")

        if dist_type in {"normal", "gaussian"}:
            if len(parts) != 4:
                raise argparse.ArgumentTypeError(
                    "Normal distribution requires mean and std (wc:normal:mean:std)"
                )
            mean = float(parts[2])
            std = float(parts[3])
            default[wc_id] = {"type": "normal", "mean": mean, "std": std}
        elif dist_type == "uniform":
            if len(parts) != 4:
                raise argparse.ArgumentTypeError(
                    "Uniform distribution requires low and high (wc:uniform:low:high)"
                )
            low = float(parts[2])
            high = float(parts[3])
            default[wc_id] = {"type": "uniform", "low": low, "high": high}
        elif dist_type in {"const", "constant"}:
            if len(parts) != 3:
                raise argparse.ArgumentTypeError(
                    "Constant distribution requires a single value (wc:const:value)"
                )
            val = float(parts[2])
            default[wc_id] = {"type": "constant", "value": val}
        else:
            raise argparse.ArgumentTypeError(f"Unsupported distribution '{dist_type}'")

    return default


def _parse_static_rules(rule_arg: str, num_work_centers: int) -> Dict[int, str]:
    if not rule_arg:
        return {}
    mapping: Dict[int, str] = {}
    for item in rule_arg.split(','):
        parts = [p.strip() for p in item.split(':') if p.strip()]
        if len(parts) != 2:
            raise argparse.ArgumentTypeError(
                "Static rule entry must be 'wc:STRATEGY'"
            )
        wc_id = int(parts[0])
        if wc_id < 1 or wc_id > num_work_centers:
            raise argparse.ArgumentTypeError(f"Invalid workcenter id {wc_id}")
        mapping[wc_id] = parts[1].upper()
    return mapping


def main():
    """Main function to run training or inference."""
    args = parse_args()
    random.seed(args.seed)

    num_machines = _parse_machine_layout(args.machines)
    num_work_centers = len(num_machines)
    processing_distributions = _parse_distributions(args.distributions, num_work_centers)
    static_rules = _parse_static_rules(args.static_rules, num_work_centers)

    # Display system layout before initialization
    WorkshopLayout.display_configuration(num_work_centers, num_machines)

    # Create coordinator
    trainer = PauseResumeTrainingCoordinator(
        num_work_centers=num_work_centers,
        num_machines=num_machines,
        rule_mode=args.rule,
        static_strategies=static_rules,
        processing_distributions=processing_distributions,
        target_utilization=args.target_utilization,
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
