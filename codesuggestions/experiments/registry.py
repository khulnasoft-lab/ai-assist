import random
from typing import Any, NamedTuple, Optional

import structlog

log = structlog.stdlib.get_logger("codesuggestions")


class ExperimentOutput(NamedTuple):
    name: str
    selected_variant: int
    output: Any


class Experiment:
    def __init__(
        self, name: str, description: str, variants: list = [], weights: list = []
    ):
        self.name = name
        self.description = description
        self.variants = variants
        self.weights = weights

    def run(self, **kwargs):
        (variant_idx,) = random.choices(range(len(self.variants)), weights=self.weights)
        log.debug("running experiment", exp=self.name, variant=variant_idx)
        return ExperimentOutput(
            name=self.name,
            selected_variant=variant_idx,
            output=self.variants[variant_idx](**kwargs),
        )


class ExperimentRegistry:
    def __init__(self):
        self.experiments = {}

    def add_experiment(self, experiment: Experiment):
        log.info(
            "registering experiment",
            exp=experiment.name,
            variants=len(experiment.variants),
        )
        self.experiments[experiment.name] = experiment

    def get_experiment(self, experiment_name: str) -> Optional[Experiment]:
        return self.experiments.get(experiment_name)
