# Dropbox storage for GitHub Actions results

Status: Prepared on the separate research branch. No OAuth credentials have been added, and no successful Dropbox upload is claimed.

## One-time owner setup

1. Create a Dropbox API app at https://www.dropbox.com/developers/apps with files.content.write scope.
2. Generate an offline OAuth refresh token for the app. The authorization request must use token_access_type=offline.
3. Add three repository Actions secrets under GitHub Settings > Secrets and variables > Actions:
   - DROPBOX_APP_KEY (the Dropbox app key)
   - DROPBOX_APP_SECRET (the app secret)
   - DROPBOX_REFRESH_TOKEN (the offline refresh token)
4. Never put credentials in source code, chat or CI logs. The Dropbox connection in ChatGPT is separate from GitHub Actions.
5. Review and merge this feature branch when ready. Test Math IR Efficient in portable-python mode, then the complete 7-engine mode.
6. Verify Dropbox outputs beneath /GitHubActions/<owner>/<repo>/<workflow>/<run>-<attempt>/<job>/ and log messages indicating that Dropbox hashes matched.

The script scripts/dropbox_actions_store.py uses Python stdlib, refreshes OAuth access tokens, supports chunked uploads and checks Dropbox size and content_hash. When secrets are missing, computations are still performed but no Dropbox copy is made. GitHub artifacts are never used as an automatic fallback.

## Storage and security

GitHub Actions in public repositories can use standard hosted runners for free even when the artifact storage allowance is exhausted, provided the workflow does not rely on artifact uploads/downloads and no account-level suspension applies.

This branch changes all nine existing workflows to avoid GitHub artifact upload and download. The former multi-job Math IR Phase 3 and Math IR Unified workflows have also been converted to single-job sequential pipelines for their original prepare, SageMath, MATLAB and verification stages. The mathematical engines remain separate, but the previous four-runner job-isolation property is no longer identical and needs regression testing. They upload generated files to Dropbox when configured.

No GitHub artifacts are deleted. Existing GitHub artifacts remain and must be reviewed before deletion. Do not publish proprietary J-CAT source data or sensitive data through a public workflow.

## Testing required

Run Python and workflow syntax checks. Confirm live OAuth upload in GitHub Actions after secrets are configured. Verify all 7 mathematical engines produce the same values as before. Main is unchanged until merge.
