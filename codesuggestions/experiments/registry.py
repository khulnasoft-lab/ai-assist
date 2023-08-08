import random
from typing import Optional


class Experiment:
    def __init__(self, name: str, variants: list = [], weights: list = []):
        self.name = name
        self.variants = variants
        self.weights = weights

    def run(self, **kwargs):
        variant_func = random.choices(self.variants, weights=self.weights)[0]
        return variant_func(**kwargs)


class ExperimentRegistry:
    def __init__(self):
        self.experiments = {}

    def add_experiment(self, experiment: Experiment):
        self.experiments[experiment.name] = experiment

    def get_experiment(self, experiment_name: str) -> Optional[Experiment]:
        if experiment_name not in self.experiments:
            return None
        return self.experiments[experiment_name]
