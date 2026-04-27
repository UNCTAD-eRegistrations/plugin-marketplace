# Verbose Output Patterns Reference

This document contains the standard verbose output patterns for GitHub Actions workflows. These patterns are MANDATORY for UNCTAD standard compliance.

## Table of Contents

1. [Commit Subject Output](#1-commit-subject-output)
2. [Build Configuration Summary](#2-build-configuration-summary)
3. [Per-Job Summary Templates](#3-per-job-summary-templates)
4. [Verbose Echo Statements](#4-verbose-echo-statements)
5. [Standard Emoji Reference](#5-standard-emoji-reference)
6. [Slack Notification Enhancement](#6-slack-notification-enhancement)

---

## 1. Commit Subject Output

Add `commit_subject` output to the `set-build-variables` job for tracking in summaries and notifications.

### Implementation

```yaml
outputs:
  tag_name: ${{ steps.vars.outputs.tag_name }}
  version: ${{ steps.vars.outputs.version }}
  commit_subject: ${{ steps.vars.outputs.commit_subject }}  # Add this

- name: Set build variables
  id: vars
  run: |
    # Extract commit subject for display
    COMMIT_SUBJECT=$(git log -1 --format=%s)
    echo "commit_subject=${COMMIT_SUBJECT}" >> $GITHUB_OUTPUT
```

---

## 2. Build Configuration Summary

Add this step at the end of `set-build-variables` job to provide visibility into build decisions.

### Implementation

```yaml
- name: Build configuration summary
  run: |
    echo "## Build Configuration" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo "### Branch Information" >> $GITHUB_STEP_SUMMARY
    echo "- **Branch:** \`${{ github.ref_name }}\`" >> $GITHUB_STEP_SUMMARY
    echo "- **Commit:** ${{ steps.vars.outputs.commit_subject }}" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo "### Build Variables" >> $GITHUB_STEP_SUMMARY
    echo "- **Docker Tag:** \`${{ steps.vars.outputs.tag_name }}\`" >> $GITHUB_STEP_SUMMARY
    echo "- **Version:** \`${{ steps.vars.outputs.version }}\`" >> $GITHUB_STEP_SUMMARY
    echo "- **Environment:** \`${{ steps.vars.outputs.env_profile }}\`" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    echo "### Pipeline Decisions" >> $GITHUB_STEP_SUMMARY
    if [ "${{ steps.vars.outputs.should_bump_version }}" == "true" ]; then
      echo "- **Version Bump:** Enabled" >> $GITHUB_STEP_SUMMARY
    else
      echo "- **Version Bump:** Skipped" >> $GITHUB_STEP_SUMMARY
    fi
    if [ "${{ steps.vars.outputs.should_build_docker }}" == "true" ]; then
      echo "- **Docker Build:** Enabled" >> $GITHUB_STEP_SUMMARY
    else
      echo "- **Docker Build:** Skipped" >> $GITHUB_STEP_SUMMARY
    fi
    if [ "${{ steps.vars.outputs.should_tag_production }}" == "true" ]; then
      echo "- **Production Tag:** Enabled" >> $GITHUB_STEP_SUMMARY
    else
      echo "- **Production Tag:** Skipped" >> $GITHUB_STEP_SUMMARY
    fi
```

---

## 3. Per-Job Summary Templates

### Version Bump Summary

Add at end of bump-version job:

```yaml
- name: Version bump summary
  if: always()
  run: |
    echo "## Version Bump Results" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    if [ "${{ steps.bump.outcome }}" == "success" ]; then
      echo "**Status:** Success" >> $GITHUB_STEP_SUMMARY
      echo "- **Previous Version:** \`${{ steps.bump.outputs.old_version }}\`" >> $GITHUB_STEP_SUMMARY
      echo "- **New Version:** \`${{ steps.bump.outputs.new_version }}\`" >> $GITHUB_STEP_SUMMARY
    elif [ "${{ steps.bump.outcome }}" == "skipped" ]; then
      echo "**Status:** Skipped" >> $GITHUB_STEP_SUMMARY
    else
      echo "**Status:** Failed" >> $GITHUB_STEP_SUMMARY
    fi
```

### Docker Build Summary

Add at end of build-and-push-docker job:

```yaml
- name: Docker build summary
  if: always()
  run: |
    echo "## Docker Build Results" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    if [ "${{ job.status }}" == "success" ]; then
      echo "**Status:** Success" >> $GITHUB_STEP_SUMMARY
      echo "" >> $GITHUB_STEP_SUMMARY
      echo "### Image Details" >> $GITHUB_STEP_SUMMARY
      echo "- **Image:** \`<image-name>:${{ needs.set-build-variables.outputs.tag_name }}\`" >> $GITHUB_STEP_SUMMARY
      echo "- **Registry:** Docker Hub" >> $GITHUB_STEP_SUMMARY
    else
      echo "**Status:** Failed" >> $GITHUB_STEP_SUMMARY
    fi
```

### Production Tag Summary

Add at end of tag-production job:

```yaml
- name: Production tag summary
  if: always()
  run: |
    echo "## Production Tag Results" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    if [ "${{ job.status }}" == "success" ]; then
      echo "**Status:** Success" >> $GITHUB_STEP_SUMMARY
      echo "- **Tag:** \`v${{ needs.set-build-variables.outputs.version }}\`" >> $GITHUB_STEP_SUMMARY
    else
      echo "**Status:** Failed" >> $GITHUB_STEP_SUMMARY
    fi
```

### Helm Chart Summary

Add at end of helm-chart-update job:

```yaml
- name: Summary
  run: |
    echo "## Helm Chart Update" >> $GITHUB_STEP_SUMMARY
    echo "- Helm chart repository updated on GitHub" >> $GITHUB_STEP_SUMMARY
```

Note: The helm chart summary uses a simple two-line format. The idempotency check in the "Update Helm chart repository" step adds a skip message to the summary when the chart is unchanged.

### Jenkins Deploy Summary

Add at end of trigger-jenkins-deploy job:

```yaml
- name: Jenkins deploy summary
  if: always()
  run: |
    echo "## Jenkins Deploy Trigger Results" >> $GITHUB_STEP_SUMMARY
    echo "" >> $GITHUB_STEP_SUMMARY
    if [ "${{ job.status }}" == "success" ]; then
      echo "**Status:** Triggered" >> $GITHUB_STEP_SUMMARY
      echo "- **Target:** Jenkins deploy job" >> $GITHUB_STEP_SUMMARY
    elif [ "${{ job.status }}" == "skipped" ]; then
      echo "**Status:** Skipped (branch not configured for deploy)" >> $GITHUB_STEP_SUMMARY
    else
      echo "**Status:** Failed" >> $GITHUB_STEP_SUMMARY
    fi
```

---

## 4. Verbose Echo Statements

Within each job step, use status indicators for visibility:

### Success Indicators

```bash
echo "Configuration loaded successfully"
echo "Docker image built: ${IMAGE_NAME}:${TAG}"
echo "Pushed to registry"
echo "Version bumped from $OLD_VERSION to $NEW_VERSION"
```

### Error/Skip Indicators

```bash
echo "Build failed: ${ERROR_MESSAGE}"
echo "Skipping: condition not met"
echo "Warning: Optional step skipped"
```

### Progress Indicators

```bash
echo "Starting version bump..."
echo "Attempt $((i + 1)) of $MAX_RETRIES"
echo "Building Docker image..."
echo "Pushing to registry..."
```

---

## 5. Standard Emoji Reference

Use these emojis consistently in `$GITHUB_STEP_SUMMARY` sections:

| Emoji | Code | Usage |
|-------|------|-------|
| Build Config | `## Build Configuration` | Build Configuration section header |
| Version | `## Version Bump` | Version Bump section header |
| Docker | `## Docker Build` | Docker Build section header |
| Tag | `## Production Tag` | Production Tag section header |
| Helm | `## Helm Chart Update` | Helm Chart Update section header |
| Success | `**Status:** Success` | Feature/step enabled or succeeded |
| Failed | `**Status:** Failed` | Feature/step disabled or failed |
| Skipped | `**Status:** Skipped` | Step was skipped |

### Inline Status (for echo statements)

Use simple text indicators for inline status messages in logs:

```bash
# Success
echo "Success: Version bumped to $NEW_VERSION"

# Failure
echo "Failed: Build error - $ERROR_MESSAGE"

# Skipped
echo "Skipped: Condition not met"
```

---

## 6. Slack Notification Enhancement

Include workflow URL and commit info in failure notifications for quick debugging.

### Implementation

```yaml
- name: Slack notification
  if: failure()
  uses: slackapi/slack-github-action@v2.1.0
  with:
    webhook: ${{ secrets.SLACK_WEBHOOK_URL }}
    webhook-type: incoming-webhook
    payload: |
      {
        "text": "CI/CD Pipeline Failed",
        "attachments": [
          {
            "color": "danger",
            "fields": [
              {"title": "Repository", "value": "${{ github.repository }}", "short": true},
              {"title": "Branch", "value": "${{ github.ref_name }}", "short": true},
              {"title": "Commit", "value": "${{ needs.set-build-variables.outputs.commit_subject }}", "short": false},
              {"title": "Workflow", "value": "<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Run>", "short": true}
            ]
          }
        ]
      }
```

### Key Elements

1. **Repository** - Which repo failed
2. **Branch** - Which branch was being built
3. **Commit** - What change triggered the failure
4. **Workflow Link** - Direct link to the failed run

---

## Usage Notes

- All workflows converted from Jenkinsfile MUST include these verbose output patterns
- The `$GITHUB_STEP_SUMMARY` is viewable in the GitHub Actions UI under "Summary"
- Summaries persist after the workflow completes for debugging
- Use consistent formatting across all jobs for readability
