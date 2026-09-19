# ==============================================================================
# 🐙 GITHUB / PULL REQUEST COMMANDS
# ==============================================================================
# Requires authenticated `gh` (GitHub CLI): gh auth status

# Default base branch for PRs (overridable: make gh_pr_create BASE_BRANCH=develop)
BASE_BRANCH ?= main

# .PHONY ensures make doesn't confuse these commands with actual files in the directory
.PHONY: gh_pr_create gh_pr_toreview gh_pr_wip gh_pr_ls

gh_pr_create: ## Pushes the current branch and creates a non-interactive PR (title/description auto-filled from commits)
	@echo "🚀 Pushing the current branch to origin..."
	git push -u origin HEAD
	@echo "📬 Creating the PR (base: $(BASE_BRANCH))..."
	gh pr create --base $(BASE_BRANCH) --fill

gh_pr_toreview: ## Adds the 'toreview' label to the PR of the current branch
	@echo "🏷️ Adding the 'toreview' label..."
	@gh label create toreview --color 86CAAD --force >/dev/null 2>&1 || true
	gh pr edit --add-label toreview

gh_pr_wip: ## Removes the 'toreview' label from the PR of the current branch (back to WIP)
	@echo "🚧 Removing the 'toreview' label..."
	gh pr edit --remove-label toreview

gh_pr_ls: ## Lists open PRs in the repository
	@echo "📋 Listing open PRs..."
	gh pr list
