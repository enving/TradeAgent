---
description: Review completed work from previous agent, verify tasks, update review status
agent: general
---

# Review: Code & Task Review Workflow

⚠️ **CRITICAL - THIS IS A REVIEW COMMAND:**
- DO NOT review your own work (violates review policy)
- ONLY review work from PREVIOUS agents
- You MUST verify files/functions exist before marking reviewed
- This is a verification workflow - be thorough

---

## Review Policy Reminder

**From tasks.json rules**:
> "Reviews can only be done by NEXT agent, not same agent"

**This means**:
- ✅ You review work from previous agent sessions
- ❌ You cannot review work you just completed
- ✅ Set `requires_review: true` for NEXT agent to review your work

---

## Review Workflow

### 1. Read tasks.json

```bash
# First, understand what needs review
cat .opencode/tasks.json | jq '.tasks[] | select(.requires_review == true and .reviewed_by == null)'
```

**Look for**:
- Tasks with `requires_review: true`
- Tasks with `reviewed_by: null`
- Features with `status: "implemented"` but not `reviewed`

### 2. Identify Review Targets

Create a review checklist:
- Which tasks need review?
- Which features need review?
- Who was the previous agent? (check `meta.last_agent`)
- What files were changed? (check git log)

### 3. Perform Code Review

For each task requiring review:

**a) Verify Files Exist**
```bash
# Check if referenced files actually exist
# NEVER mark as reviewed without verification!
```

**b) Check Implementation Quality**
- Does code match task requirements?
- Are there tests?
- Is documentation updated?
- Any obvious bugs or issues?
- Follows coding standards? (check dev-rules.md)

**c) Test Functionality**
```bash
# Run tests if available
npm test
# or
pytest
# or
go test
```

**d) Check Git History**
```bash
# See what was actually changed
git log --oneline --since="1 day ago"
git diff HEAD~5 HEAD
```

### 4. Document Review Findings

For each reviewed task, create review notes:

**If APPROVED**:
```json
{
  "id": "TASK-001",
  "reviewed_by": "your-agent-name",
  "review_date": "2026-01-16T12:00:00Z",
  "review_status": "approved",
  "review_notes": "Implementation verified. Tests pass. Code quality good."
}
```

**If ISSUES FOUND**:
```json
{
  "id": "TASK-002",
  "reviewed_by": "your-agent-name",
  "review_date": "2026-01-16T12:00:00Z",
  "review_status": "changes_requested",
  "review_notes": "Issues found: 1) Missing error handling in auth.py:42, 2) No tests for edge cases, 3) Documentation incomplete",
  "status": "in_progress"  // ← Revert to in_progress if issues found
}
```

### 5. Update tasks.json

Update each reviewed task:

```json
{
  "tasks": [
    {
      "id": "TASK-001",
      "title": "Implement login feature",
      "status": "completed",
      "verified": true,
      "verified_by": "previous-agent",
      "verified_date": "2026-01-15",
      "requires_review": true,
      "reviewed_by": "current-agent",  // ← ADD THIS
      "review_date": "2026-01-16T12:00:00Z",  // ← ADD THIS
      "review_status": "approved",  // ← ADD THIS
      "review_notes": "Implementation verified and approved"  // ← ADD THIS
    }
  ],
  "features": [
    {
      "id": "FEAT-001",
      "title": "User Authentication",
      "status": "reviewed",  // ← UPDATE STATUS
      "reviewed_by": "current-agent",
      "review_date": "2026-01-16T12:00:00Z",
      "review_notes": "Feature complete and tested"
    }
  ],
  "meta": {
    "last_updated": "2026-01-16T12:00:00Z",
    "last_agent": "current-agent"
  }
}
```

### 6. Create Review Summary

Generate a markdown summary:

```markdown
# Code Review Summary - 2026-01-16

**Reviewer**: current-agent
**Previous Agent**: previous-agent
**Tasks Reviewed**: 3
**Features Reviewed**: 1

## Approved Tasks ✅

### TASK-001: Implement login feature
- **Status**: Approved
- **Files**: src/auth.py, tests/test_auth.py
- **Tests**: ✅ All passing
- **Notes**: Clean implementation, good error handling

### TASK-002: Add logout endpoint
- **Status**: Approved
- **Files**: src/auth.py
- **Tests**: ✅ Passing
- **Notes**: Simple and correct

## Changes Requested ⚠️

### TASK-003: Password reset flow
- **Status**: Changes requested
- **Issues**:
  1. Missing rate limiting on reset endpoint
  2. Email template not found (templates/reset.html)
  3. No tests for token expiration
- **Action**: Reverted to in_progress, added subtasks

## Features Reviewed

### FEAT-001: User Authentication
- **Status**: Reviewed ✅
- **Coverage**: Login, Logout complete | Password reset needs work
- **Overall**: 80% ready, minor fixes needed

---

**Next Steps**:
1. Address TASK-003 issues
2. Add rate limiting
3. Create email template
4. Write expiration tests
```

### 7. Update Markdown Docs

**agents.md**:
```markdown
## 2026-01-16 - Review Agent (your-name)

**Type**: Code Review
**Duration**: 45 minutes
**Tasks Reviewed**: 3
**Approved**: 2/3

### Review Summary
- TASK-001 ✅ Approved
- TASK-002 ✅ Approved
- TASK-003 ⚠️ Changes requested (see review notes)

### Issues Found
- Missing rate limiting in password reset
- Template file not created
- Edge case tests missing

### Next Agent Instructions
Focus on TASK-003 issues. Everything else is approved and ready.
```

Update priorities based on review findings.

### 8. Git Commit (Optional)

If you made fixes during review:

```bash
git commit -m "$(cat <<'EOF'
review: complete code review of previous agent work

Reviewed:
- TASK-001: Approved ✅
- TASK-002: Approved ✅
- TASK-003: Changes requested ⚠️

Issues found in TASK-003:
- Missing rate limiting
- Template file missing
- Edge case tests incomplete

Updated tasks.json with review status and notes.

Authored-By: Tristan Häfele
LinkedIn: https://de.linkedin.com/in/tristan-wilms-812b8011b
EOF
)"
```

### 9. Handoff for Next Agent (If Issues Found)

If you found issues that need fixing:

```markdown
=== HANDOFF FOR NEXT AGENT ===

🔍 REVIEW COMPLETED - ISSUES FOUND

I completed a code review of the previous agent's work.

**Approved Tasks** (no action needed):
- ✅ TASK-001: Implement login feature
- ✅ TASK-002: Add logout endpoint

**Tasks Requiring Fixes**:
- ⚠️ TASK-003: Password reset flow

**Issues to Fix**:
1. **Rate Limiting**: Add rate limiting to /auth/reset endpoint
   - Suggestion: 5 requests per hour per IP
   - File: src/auth.py:67

2. **Missing Template**: Create templates/reset.html
   - Should include: reset link, expiration notice, branding

3. **Missing Tests**: Add tests for token expiration
   - File: tests/test_auth.py
   - Test cases: expired token, invalid token, already-used token

**Priority**: HIGH - Password reset is critical security feature

**Next Steps**:
1. Fix the 3 issues above
2. Run full test suite
3. Mark TASK-003 as completed
4. Request review again (requires_review: true)

See detailed review notes in .opencode/tasks.json
```

---

## Anti-Halluzination Checklist

Before marking any task as `reviewed`:

- [ ] I verified the files exist (`ls`, `cat`)
- [ ] I read the actual code (not just assumed it's there)
- [ ] I ran tests if available
- [ ] I checked git history to see changes
- [ ] I am NOT the agent who created this task (review policy)
- [ ] I documented specific findings (not vague "looks good")
- [ ] I updated tasks.json with concrete review notes

**If you can't check all boxes → DO NOT mark as reviewed**

---

## When to Use /review

✅ **Use /review when**:
- Starting a session and previous agent left `requires_review: true` tasks
- Before deploying/merging code
- After major features completed by previous agent
- As part of quality assurance workflow

❌ **Don't use /review when**:
- Reviewing your own work (violates policy)
- No tasks have `requires_review: true`
- You're in the middle of implementing features

---

## Summary

/review command:
1. ✓ Reads tasks.json for review targets
2. ✓ Verifies files and code exist
3. ✓ Tests functionality
4. ✓ Documents findings (approved / changes requested)
5. ✓ Updates tasks.json with review status
6. ✓ Updates markdown docs
7. ✓ Creates handoff if issues found

**Next Command**: If review approved everything → `/checkpoint`
**Next Command**: If issues found → work on fixes, then `/checkpoint`

---

**Last Updated**: 2026-01-16
**Maintained by**: Tristan Häfele
**LinkedIn**: https://de.linkedin.com/in/tristan-wilms-812b8011b
