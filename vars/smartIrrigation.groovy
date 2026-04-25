// =============================================================================
// Smart Irrigation — Shared Pipeline Library
// =============================================================================
// Loaded automatically via Jenkinsfile: @Library('smartIrrigation') _
// Provides reusable helpers for the CI/CD pipeline.
//
// Location: vars/smartIrrigation.groovy (repo root)
// Jenkins requires the vars/ directory to be at the root of the library repo.
// =============================================================================

/**
 * Returns the list of all microservice directory names under services/.
 */
def getServices() {
    return [
        'api-gateway',
        'data-ingestion',
        'drift-monitor',
        'feature-engineering',
        'irrigation-controller',
        'model-server',
        'notification-service',
        'sensor-simulator',
        'user-service',
        'web-dashboard'
    ]
}

/**
 * Detects which services have changed files compared to the target branch.
 * Falls back to all services if detection fails (e.g. first build).
 *
 * @param targetBranch  Branch to diff against (default: 'origin/main')
 * @return              List of changed service directory names
 */
def getChangedServices(String targetBranch = 'origin/main') {
    try {
        def changes = sh(
            script: "git diff --name-only ${targetBranch}...HEAD -- services/ | cut -d'/' -f2 | sort -u",
            returnStdout: true
        ).trim()

        if (changes) {
            return changes.split('\n').toList()
        }
    } catch (Exception e) {
        echo "Could not determine changed services, running all: ${e.message}"
    }
    return getServices()
}

/**
 * Generates a Docker image tag from branch name and commit SHA.
 *
 * @return  Tag string like 'main-a1b2c3d' or 'develop-e4f5g6h'
 */
def dockerTag() {
    def branch = env.BRANCH_NAME?.replaceAll('[^a-zA-Z0-9_.-]', '-') ?: 'unknown'
    def sha    = env.GIT_COMMIT?.take(7) ?: 'latest'
    return "${branch}-${sha}"
}

/**
 * Branch predicate: true if running on the main branch.
 */
def isMainBranch() {
    return env.BRANCH_NAME == 'main'
}

/**
 * Branch predicate: true if running on main, develop, or a PR targeting them.
 */
def isIntegrationBranch() {
    if (env.BRANCH_NAME == 'main' || env.BRANCH_NAME == 'develop') {
        return true
    }
    // For PRs, CHANGE_TARGET holds the target branch name
    if (env.CHANGE_TARGET == 'main' || env.CHANGE_TARGET == 'develop') {
        return true
    }
    return false
}
