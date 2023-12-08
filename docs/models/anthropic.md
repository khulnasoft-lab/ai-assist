# Handling Anthropic API Rate Limit

When the AI Gateway hits the rate limit of the Anthropic API, we need to request an increase in the quota from Anthropic. This process is as follows:

1. Measure the maximum number of requests we see in a 1-minute slice. This is to provide Anthropic with our previous utilization data.
2. Contact `Amir Kashanchi` in the `#ext-anthropic` Slack channel. Request an increase to a reasonable limit and specify the account that needs the increase (either GitLab Dev or GitLab Pro).

Please note that Anthropic can easily increase the quota to anything up to six digits. They just need to see our previous utilization before increasing our quota.

This process should be initiated as soon as possible when we hit the rate limit to minimize disruption to the AI Gateway service.