import pytest

from ai_gateway.code_suggestions.detectors import (
    DetectorRegexEmail,
    DetectorRegexIPV4,
    DetectorRegexIPV6,
    DetectorRegexSecrets,
    PiiRedactor,
)


@pytest.mark.parametrize(
    "test_content,expected_output",
    [
        (
            "no address",
            "no address",
        ),
        (
            "one address: email@ex.com",
            "one address: EMAIL",
        ),
        (
            "one: one@ex.com, two: two@ex.com",
            "one: EMAIL, two: EMAIL",
        ),
        (
            "wrong address: email@com",
            "wrong address: email@com",
        ),
        (
            "wrong address: email@.com",
            "wrong address: email@.com",
        ),
    ],
)
def test_detector_email(test_content, expected_output):
    det = DetectorRegexEmail(replacement="EMAIL")
    redacted = det.redact_all(test_content)

    assert redacted == expected_output


@pytest.mark.parametrize(
    "test_content,expected_output",
    [
        (
            "no ip address",
            "no ip address",
        ),
        (
            "no ipv6 address 33.01.33.33",
            "no ipv6 address 33.01.33.33",
        ),
        (
            "test 1:2:3:4:5:6:7:8",
            "test IPV6",
        ),
        (
            "test 1::, 1:2:3:4:5:6:7::",
            "test IPV6, IPV6",
        ),
        (
            "test 1::8, 1:2:3:4:5:6::8, 1:2:3:4:5:6::8",
            "test IPV6, IPV6, IPV6",
        ),
        (
            "test 1::7:8, 1:2:3:4:5::7:8, 1:2:3:4:5::8",
            "test IPV6, IPV6, IPV6",
        ),
        (
            "test 1::6:7:8, 1:2:3:4::6:7:8, 1:2:3:4::8",
            "test IPV6, IPV6, IPV6",
        ),
        (
            "test 1::5:6:7:8, 1:2:3::5:6:7:8, 1:2:3::8",
            "test IPV6, IPV6, IPV6",
        ),
        (
            "test 1::4:5:6:7:8, 1:2::4:5:6:7:8, 1:2::8",
            "test IPV6, IPV6, IPV6",
        ),
        (
            "test 1::3:4:5:6:7:8, 1::3:4:5:6:7:8, 1::8",
            "test IPV6, IPV6, IPV6",
        ),
        (
            "test ::2:3:4:5:6:7:8, ::2:3:4:5:6:7:8, ::8, ::",
            "test IPV6, IPV6, IPV6, IPV6",
        ),
        (
            "test fe80::7:8%eth0, fe80::7:8%1",
            "test IPV6, IPV6",
        ),
        (
            "test ::255.255.255.255, ::ffff:255.255.255.255, ::ffff:0:255.255.255.255",
            "test IPV6, IPV6, IPV6",
        ),
        (
            "test 2001:db8:3:4::192.0.2.33, 64:ff9b::192.0.2.33",
            "test IPV6, IPV6",
        ),
    ],
)
def test_detector_ipv6(test_content, expected_output):
    det = DetectorRegexIPV6(replacement="IPV6")
    redacted = det.redact_all(test_content)

    assert redacted == expected_output


@pytest.mark.parametrize(
    "test_content,expected_output",
    [
        ("test no ip", "test no ip"),
        ("test no ip 2020.10", "test no ip 2020.10"),
        ("test no ip 20.10.01", "test no ip 20.10.01"),
        ("test no ipv4 1::3:4:5:6:7:8", "test no ipv4 1::3:4:5:6:7:8"),
        (
            "test 127.0.0.1",
            "test IPV4",
        ),
        (
            "test 255.255.255.255",
            "test IPV4",
        ),
        (
            "test 10.1.1.124",
            "test IPV4",
        ),
        (
            "test 127.0.0.1, 255.255.255.255",
            "test IPV4, IPV4",
        ),
        # detect this ip even if it's invalid
        (
            "test 10.01.1.124",
            "test IPV4",
        ),
    ],
)
def test_detector_ipv4(test_content, expected_output):
    det = DetectorRegexIPV4(replacement="IPV4")
    redacted = det.redact_all(test_content)

    assert redacted == expected_output


@pytest.mark.parametrize(
    "test_content,expected_output",
    [
        ("no secrets", "no secrets"),
        (
            "sendgrid tokens: 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",
            "SECRET",
        ),
        (
            "discord: MTk4NjIyNDgzNDcxOTI1MjQ4.Cl2FMQ.ZnCjm1XVW7vRze4b7Cq4se7kKWs",
            "SECRET",
        ),
        (
            "GitLab token: glpat-xEpxjYPbvfwGX8KyBsW9\nglpat-xEpxjYPbvfwGX8KyBsW8",
            "GitLab token: SECRET\nSECRET",
        ),
        (
            "GitLab token: glpat-xEpxjYPbvfwGX8KyBsW9\nglpat-xEpxjYPbvfwGX8KyBsW8",
            "GitLab token: SECRET\nSECRET",
        ),
    ],
)
def test_detector_token_secrets_detect_all(test_content, expected_output):
    det = DetectorRegexSecrets(replacement="SECRET")
    redacted = det.redact_all(test_content)

    assert redacted == expected_output


@pytest.mark.parametrize(
    "test_content,expected_output",
    [
        (
            "The token for IP 127.0.0.1 is glpat-xEpxjYPbvfwGX8KyBsW9",
            "The token for IP <x.x.x.x> is <secret>",
        ),
    ],
)
def test_pii_redactor(test_content, expected_output):
    redactor = PiiRedactor()
    redacted = redactor.redact_pii(test_content)

    assert redacted == expected_output
