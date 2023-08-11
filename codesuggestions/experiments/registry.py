import random
from typing import Any, NamedTuple, Optional

import structlog
from dependency_injector import providers

import codesuggestions.experiments.exp_truncate_suffix_python as exp_truncate_suffix_python

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
    def __init__(self, experiments: Optional[list[Experiment]] = []):
        self.experiments = {exp.name: exp for exp in experiments}

    def add_experiment(self, experiment: Experiment):
        log.info(
            "registering experiment",
            exp=experiment.name,
            variants=len(experiment.variants),
        )
        self.experiments[experiment.name] = experiment

    def get_experiment(self, experiment_name: str) -> Optional[Experiment]:
        return self.experiments.get(experiment_name)


def experiments_provider() -> list[Experiment]:
    return [Experiment(**exp_truncate_suffix_python.experiment_details())]


def create_experiment_registry_provider() -> providers.Singleton:
    return providers.Singleton(
        ExperimentRegistry,
        experiments=providers.List(*experiments_provider()),
    )
