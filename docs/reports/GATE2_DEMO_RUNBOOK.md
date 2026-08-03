# Gate 2 Demo Runbook

## Purpose

Reproduce and review Gate 2 reliability evidence without exposing credentials, changing production state, or claiming results before they exist.

## Preconditions

- Repository access to `KinguYume-G/AegisFlow`.
- `main` is protected and contains merge commit `5a5b6a33e4cdf0750a5e3f2d86ddf0766c06d016` or a reviewed successor.
- GitHub Environment `model-development` is restricted to protected branches.
- Variables `MODEL_PRIMARY_NAME` and `MODEL_FALLBACK_NAME` exist.
- Secrets `MODEL_PRIMARY_API_KEY` and `MODEL_FALLBACK_API_KEY` exist; never copy their values into an Issue, PR, log, shell history, or document.

## Demo A — Worker-loss recovery

1. Open **Actions → Gate 2 fault injection**.
2. Select **Run workflow**, branch `main`.
3. Wait for `fault-injection` to finish.
4. Verify all steps pass, including the 20-iteration matrix and evidence upload.
5. Record the run URL, commit SHA, artifact name/ID, iteration count, duplicate count, lost-Signal count, p50, and p95.
6. Download the artifact only if detailed review is required; treat it as test evidence, not a repository input.

Expected result:

- `iterations=20`;
- `accepted=true`;
- duplicate external effects `0`;
- lost Signals `0`;
- p50 below 5 seconds;
- p95 below 15 seconds.

Reference success: [run 30801262477](https://github.com/KinguYume-G/AegisFlow/actions/runs/30801262477).

## Demo B — Protected provider smoke

1. Confirm only the names—not values—of the required Environment entries.
2. Open **Actions → Model gateway smoke**.
3. Select **Run workflow**, branch `main`.
4. Wait for `model-gateway-smoke` to finish.
5. Inspect only the final redacted JSON metadata.

Expected result:

- status `ok`;
- one or two bounded route attempts;
- a resolved model identifier;
- token status `measured` or honestly `not_available`;
- cost source `provider_reported` or honestly `not_available`;
- no API Key or response content.

Reference success: [run 30804037539](https://github.com/KinguYume-G/AegisFlow/actions/runs/30804037539). It exercised the DeepSeek primary route only.

## Review Checklist

- [ ] Both runs execute from a protected `main` commit.
- [ ] Fault metrics meet Gate targets.
- [ ] Duplicate effects and lost Signals are zero.
- [ ] Provider output is redacted and Secret-safe.
- [ ] Real and deterministic evidence are labeled separately.
- [ ] Limitations are stated during the demo.
- [ ] Human Reviewer accepts or rejects Gate 2 explicitly.

## Stop Conditions

Stop and report rather than retry blindly when:

- a workflow runs from an unexpected commit or branch;
- an artifact or log contains a credential or model response body;
- any duplicate effect or lost Signal is non-zero;
- recovery exceeds a Gate target;
- the provider fails because configuration is absent or inconsistent;
- evidence conflicts with the published report.

Do not rotate, reveal, replace, or test Secret values from the demo. Do not approve Gate 2 automatically.
