from pylint.checkers import BaseChecker, DeprecatedMixin
from pylint.lint import PyLinter


class DeprecatedProviderOverride(DeprecatedMixin, BaseChecker):
    name = "deprecated-provider-overrides"
    msgs = {**DeprecatedMixin.DEPRECATED_METHOD_MESSAGE}

    def deprecated_methods(self) -> set[str]:
        return {"dependency_injector.providers.Provider.override"}


def register(linter: PyLinter) -> None:
    linter.register_checker(DeprecatedProviderOverride(linter))
