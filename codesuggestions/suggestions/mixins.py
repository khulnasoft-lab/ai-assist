from typing import Dict, List

from codesuggestions.suggestions.detectors import (
    Detected,
    DetectorBasicAuthSecrets,
    DetectorKeywordsSecrets,
    DetectorKind,
    DetectorRegexEmail,
    DetectorRegexIPV4,
    DetectorRegexIPV6,
    DetectorTokenSecrets,
)

__all__ = [
    "DEFAULT_REPLACEMENT_EMAIL",
    "DEFAULT_REPLACEMENT_IPV4",
    "DEFAULT_REPLACEMENT_IPV6",
    "DEFAULT_REPLACEMENT_SECRET",
]

DEFAULT_REPLACEMENT_EMAIL = "<email placeholder|email@example.com>"
DEFAULT_REPLACEMENT_IPV4 = "<ipv4 placeholder|x.x.x.x>"
DEFAULT_REPLACEMENT_IPV6 = "<ipv6 placeholder|x:x:x:x:x:x:x:x>"
DEFAULT_REPLACEMENT_SECRET = "<secret placeholder|secret>"

PII_DETECTORS = [
    DetectorRegexEmail(),
    # a different order of IPVx detectors may change the output
    DetectorRegexIPV6(),
    DetectorRegexIPV4(),
    DetectorBasicAuthSecrets(),
    DetectorTokenSecrets(),
    DetectorKeywordsSecrets(),
]

PII_REPLACEMENTS = {
    DetectorKind.EMAIL: DEFAULT_REPLACEMENT_EMAIL,
    DetectorKind.IPV4: DEFAULT_REPLACEMENT_IPV4,
    DetectorKind.IPV6: DEFAULT_REPLACEMENT_IPV6,
    DetectorKind.SECRET: DEFAULT_REPLACEMENT_SECRET,
}


class RedactPiiMixin:
    def __init__(self, detectors: List, replacements: Dict):
        self.pii_detectors = detectors
        self.pii_replacements = replacements

    def _detect_pii(self, content: str) -> list[Detected]:
        detected = []
        for detector in self.pii_detectors:
            detected.extend(detector.detect_all(content))

        return detected

    def _redact_pii(self, content: str, detected: list[Detected]):
        detected = sorted(detected, key=lambda x: (x.start, -x.end))

        step = 0
        subparts = []
        for d in detected:
            if step > d.start:
                # skip: the previous detection overlaps the current one
                continue
            if subtext := content[step : d.start]:
                subparts.append(subtext)

            subparts.append(self.pii_replacements[d.kind])
            step = d.end

        # add remaining content
        if step < len(content):
            subparts.append(content[step:])

        redacted = "".join(subparts)

        return redacted

    def redact_pii(self, content: str) -> str:
        pii_detected = self._detect_pii(content)
        return self._redact_pii(content, pii_detected)
