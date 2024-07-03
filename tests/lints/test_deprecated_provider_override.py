import astroid
import pylint.testutils

from lints import deprecated_provider_override


class TestDirectEnvironmentVariableReference(pylint.testutils.CheckerTestCase):
    CHECKER_CLASS = deprecated_provider_override.DeprecatedProviderOverride

    def test_finds_deprecated_provider_override(self):
        node = astroid.extract_node(
            """
            from dependency_injector.providers import Provider

            Provider().override({})
        """
        )
        with self.assertAddsMessages(
            pylint.testutils.MessageTest(
                msg_id="deprecated-method",
                args=("override",),
                node=node,
            ),
            ignore_position=True,
        ):
            self.checker.visit_call(node)
