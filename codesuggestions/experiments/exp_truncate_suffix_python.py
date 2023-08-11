def variant_control(**kwargs) -> str:
    return kwargs["suffix"]


def variant_1(**kwargs) -> str:
    from typing import Optional

    from structlog import BoundLogger

    from codesuggestions.prompts.parsers.treesitter import CodeParser
    from codesuggestions.suggestions.processing.ops import LanguageId

    def _truncate_suffix_context(
        logger: BoundLogger,
        prefix: str,
        suffix: str,
        lang_id: Optional[LanguageId] = None,
    ) -> str:
        try:
            parser = CodeParser.from_language_id(prefix + suffix, lang_id)
        except ValueError as e:
            logger.warning(f"Failed to parse code: {e}")
            # default to the original suffix
            return suffix

        def _make_point(prefix: str) -> tuple[int, int]:
            lines = prefix.splitlines()
            row = len(lines) - 1
            col = len(lines[-1])
            return (row, col)

        truncated_suffix = parser.suffix_near_cursor(point=_make_point(prefix))
        return truncated_suffix or suffix

    return _truncate_suffix_context(**kwargs)


def experiment_details() -> dict:
    return {
        "name": "exp_truncate_suffix_python",
        "description": "Truncate the suffix based on the context around the cursor",
        "variants": [
            variant_control,
            variant_1,
        ],
        "weights": [50, 50],
    }
