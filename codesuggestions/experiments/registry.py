import random
from typing import Optional

import structlog

log = structlog.stdlib.get_logger("codesuggestions")


class Experiment:
    def __init__(self, name: str, variants: list = [], weights: list = []):
        self.name = name
        self.variants = variants
        self.weights = weights

    def run(self, **kwargs):
        (variant_idx,) = random.choices(range(len(self.variants)), weights=self.weights)
        log.info("running experiment", exp=self.name, variant=variant_idx)
        return self.variants[variant_idx](**kwargs)


class ExperimentRegistry:
    def __init__(self):
        self.experiments = {}

    def add_experiment(self, experiment: Experiment):
        log.info("registering experiment", exp=experiment.name, variants=len(experiment.variants))
        self.experiments[experiment.name] = experiment

    def get_experiment(self, experiment_name: str) -> Optional[Experiment]:
        if experiment_name not in self.experiments:
            return None
        return self.experiments[experiment_name]
