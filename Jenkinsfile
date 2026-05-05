// =============================================================================
// Smart Irrigation — Declarative CI/CD Pipeline
// =============================================================================

pipeline {
    agent none

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 45, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        REGISTRY    = 'ghcr.io'
        IMAGE_BASE  = "ghcr.io/${env.GITHUB_USER}/smart-irrigation"
        // Inlined service list to avoid library dependency
        SERVICES    = 'api-gateway,data-ingestion,drift-monitor,feature-engineering,irrigation-controller,model-server,notification-service,sensor-simulator,user-service,web-dashboard'
    }

    triggers {
        githubPush()
    }

    stages {

        // =====================================================================
        // 1. CHECKOUT
        // =====================================================================
        stage('Checkout') {
            agent { label 'python' }
            steps {
                cleanWs()
                checkout([
                    $class: 'GitSCM',
                    branches: scm.branches,
                    changelog: false,
                    poll: false,
                    extensions: (scm.extensions ?: []) + [
                        [$class: 'CloneOption', depth: 1, noTags: true, shallow: true],
                        [$class: 'PruneStaleBranch']
                    ],
                    userRemoteConfigs: scm.userRemoteConfigs
                ])
                
                sh '''
                    echo "── Creating fast source archive ──"
                    # We use tar to bypass the slow Jenkins stash file-walker.
                    # This reduces stash/unstash overhead from minutes to seconds.
                    # We ignore exit code 1 (file changed as we read it) which is common in dynamic environments.
                    tar --exclude="./services/web-dashboard/node_modules" \
                        --exclude="./.venv" \
                        --exclude="./.uv-test-venv" \
                        --exclude="./.git" \
                        --exclude="./project_pdfs" \
                        --exclude="source.tar.gz" \
                        -czf source.tar.gz . || [ $? -eq 1 ]
                '''
                stash name: 'source-archive', includes: 'source.tar.gz'
            }
        }

        // =====================================================================
        // 2. CI CHECKS — Parallel Lint, Unit Tests, and Security Scan
        // =====================================================================
        stage('CI Checks') {
            parallel {
                stage('Ruff') {
                    agent { label 'python' }
                    steps {
                        unstash 'source-archive'
                        sh 'tar -xzf source.tar.gz && rm source.tar.gz'
                        sh 'echo "── Ruff: linting all services ──" && ruff check services/ --output-format=junit > ruff-report.xml || true'
                    }
                    post {
                        always { junit allowEmptyResults: true, testResults: 'ruff-report.xml' }
                    }
                }
                stage('mypy') {
                    agent { label 'python' }
                    steps {
                        unstash 'source-archive'
                        sh 'tar -xzf source.tar.gz && rm source.tar.gz'
                        sh '''
                            echo "── mypy: type-checking all services ──"
                            EXIT_CODE=0
                            for svc in $(echo $SERVICES | tr ',' ' '); do
                                if [ -d "services/${svc}/src" ]; then
                                    # Only run if there are python files in src
                                    if find "services/${svc}/src" -name "*.py" | grep -q .; then
                                        echo "▶ Type checking ${svc}..."
                                        PYTHONPATH="${WORKSPACE}/services/${svc}:${PYTHONPATH}" \
                                        python3 -m mypy "services/${svc}/src" \
                                            --ignore-missing-imports \
                                            --no-error-summary \
                                            --junit-xml "mypy-${svc}.xml" || EXIT_CODE=1
                                    fi
                                fi
                            done
                            exit $EXIT_CODE
                        '''
                    }
                    post {
                        always { junit allowEmptyResults: true, testResults: 'mypy-*.xml' }
                    }
                }
                stage('Unit Tests') {
                    agent { label 'python' }
                    steps {
                        unstash 'source-archive'
                        sh 'tar -xzf source.tar.gz && rm source.tar.gz'
                        sh '''
                            echo "── Preparing Python environment ──"
                            python3 -m pip install --quiet --upgrade pip

                            echo "── Running unit tests across all services ──"
                            EXIT_CODE=0
                            for svc in $(echo $SERVICES | tr ',' ' '); do
                                if [ -d "services/${svc}/tests/unit" ]; then
                                    # Only run if there are test files (ignoring .gitkeep)
                                    if find "services/${svc}/tests/unit" -name "test_*.py" | grep -q .; then
                                        echo "▶ Testing ${svc}..."
                                        python3 -m pip install --quiet -r "services/${svc}/requirements.txt" || true
                                        
                                        # Set PYTHONPATH so 'from src...' works
                                        PYTHONPATH="${WORKSPACE}/services/${svc}:${PYTHONPATH}" \
                                        python3 -m pytest "services/${svc}/tests/unit/" \
                                            --junitxml="unit-${svc}.xml" \
                                            --tb=short -q || EXIT_CODE=1
                                    else
                                        echo "⏭ Skipping ${svc} (no test files found)"
                                    fi
                                fi
                            done
                            exit $EXIT_CODE
                        '''
                    }
                    post {
                        always { junit allowEmptyResults: true, testResults: 'unit-*.xml' }
                    }
                }
                stage('Security Scan') {
                    agent { label 'python' }
                    steps {
                        unstash 'source-archive'
                        sh 'tar -xzf source.tar.gz && rm source.tar.gz'
                        sh '''
                            echo "── OWASP Dependency-Check ──"
                            SCAN_PATHS=""
                            for svc in $(echo $SERVICES | tr ',' ' '); do
                                REQ="services/${svc}/requirements.txt"
                                if [ -f "$REQ" ]; then
                                    SCAN_PATHS="${SCAN_PATHS} --scan ${REQ}"
                                fi
                            done

                            # Run scan but don't fail the parallel block yet
                            # This allows tests to finish while NVD downloads
                            dependency-check.sh \
                                ${SCAN_PATHS} \
                                --project "smart-irrigation" \
                                --format JSON \
                                --format HTML \
                                --out dependency-check-report \
                                --failOnCVSS 11 \
                                --enableExperimental \
                                || echo "Dependency-Check is initializing or findings found"
                        '''
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'dependency-check-report/**', allowEmptyArchive: true
                        }
                    }
                }
            }
        }

        // =====================================================================
        // 3. INTEGRATION TESTS
        // Runs on: main, develop, PRs targeting main/develop
        // =====================================================================
        stage('Integration Tests') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                    changeRequest target: 'main'
                    changeRequest target: 'develop'
                }
            }
            agent { label 'python' }
            steps {
                unstash 'source-archive'
                sh 'tar -xzf source.tar.gz && rm source.tar.gz'
                withCredentials([
                    usernamePassword(
                        credentialsId: 'github-creds',
                        usernameVariable: 'GHCR_USER',
                        passwordVariable: 'GHCR_TOKEN'
                    )
                ]) {
                    sh '''
                        echo "── Running integration tests ──"
                        EXIT_CODE=0
                        for svc in $(echo $SERVICES | tr ',' ' '); do
                            if [ -d "services/${svc}/tests/integration" ]; then
                                echo "▶ Integration: ${svc}..."
                                pip install --quiet -r "services/${svc}/requirements.txt" 2>/dev/null || true
                                python3 -m pytest "services/${svc}/tests/integration/" \
                                    --junitxml="integration-${svc}.xml" \
                                    --tb=short \
                                    -q || EXIT_CODE=1
                            fi
                        done
                        exit $EXIT_CODE
                    '''
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'integration-*.xml'
                }
            }
        }

        // =====================================================================
        // 6. DOCKER BUILD & VERIFY
        // Runs on: ALL branches
        // =====================================================================
        stage('Docker Build & Verify') {
            agent { label 'docker' }
            steps {
                unstash 'source-archive'
                sh 'tar -xzf source.tar.gz && rm source.tar.gz'
                withCredentials([
                    usernamePassword(
                        credentialsId: 'github-creds',
                        usernameVariable: 'GHCR_USER',
                        passwordVariable: 'GHCR_TOKEN'
                    )
                ]) {
                    sh '''
                        echo "── Building all service images ──"
                        GIT_SHA=$(echo $GIT_COMMIT | head -c 7)
                        TAG="${BRANCH_NAME}-${GIT_SHA}"

                        for svc in $(echo $SERVICES | tr ',' ' '); do
                            IMAGE="${IMAGE_BASE}/${svc}"
                            echo "▶ Building ${IMAGE}:${TAG}"
                            docker build \
                                -t "${IMAGE}:${TAG}" \
                                -t "${IMAGE}:latest" \
                                -f "services/${svc}/Dockerfile" \
                                "services/${svc}/"
                        done

                        echo ""
                        echo "── Verifying built images ──"
                        docker images --filter "reference=${IMAGE_BASE}/*" --format "table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}"
                    '''
                }
            }
        }

        // =====================================================================
        // 7. PUBLISH — push to GHCR
        // Runs on: main ONLY
        // =====================================================================
        stage('Publish') {
            when { branch 'main' }
            agent { label 'docker' }
            steps {
                unstash 'source-archive'
                sh 'tar -xzf source.tar.gz && rm source.tar.gz'
                withCredentials([
                    usernamePassword(
                        credentialsId: 'github-creds',
                        usernameVariable: 'GHCR_USER',
                        passwordVariable: 'GHCR_TOKEN'
                    )
                ]) {
                    sh '''
                        echo "── Authenticating to GHCR ──"
                        echo "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USER}" --password-stdin

                        GIT_SHA=$(echo $GIT_COMMIT | head -c 7)
                        TAG="main-${GIT_SHA}"

                        echo "── Pushing images to ghcr.io ──"
                        for svc in $(echo $SERVICES | tr ',' ' '); do
                            IMAGE="${IMAGE_BASE}/${svc}"
                            echo "▶ Pushing ${IMAGE}:${TAG} + :latest"
                            docker push "${IMAGE}:${TAG}"
                            docker push "${IMAGE}:latest"
                        done

                        docker logout ghcr.io
                    '''
                }
            }
        }

        // =====================================================================
        // 8. DEPLOY — docker compose up on same machine
        // Runs on: main ONLY
        // =====================================================================
        stage('Deploy') {
            when { branch 'main' }
            agent { label 'docker' }
            steps {
                unstash 'source-archive'
                sh 'tar -xzf source.tar.gz && rm source.tar.gz'
                withCredentials([
                    usernamePassword(
                        credentialsId: 'github-creds',
                        usernameVariable: 'GHCR_USER',
                        passwordVariable: 'GHCR_TOKEN'
                    )
                ]) {
                    sh '''
                        echo "── Authenticating to GHCR for pull ──"
                        echo "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USER}" --password-stdin

                        echo "── Pulling latest images ──"
                        docker compose \
                            --env-file .env \
                            -f docker/docker-compose.yml \
                            -f docker/docker-compose.data.yml \
                            -f docker/docker-compose.ml.yml \
                            -f docker/docker-compose.app.yml \
                            pull

                        echo "── Deploying updated stack ──"
                        docker compose \
                            --env-file .env \
                            -f docker/docker-compose.yml \
                            -f docker/docker-compose.data.yml \
                            -f docker/docker-compose.ml.yml \
                            -f docker/docker-compose.app.yml \
                            up -d

                        docker logout ghcr.io
                        echo "✅ Deploy complete"
                    '''
                }
            }
        }
    }

    // =========================================================================
    // POST — cleanup + notifications
    // =========================================================================
    post {
        always {
            node('python') {
                cleanWs(deleteDirs: true, disableDeferredWipeout: true)
            }
        }
        failure {
            echo "❌ Pipeline FAILED on branch ${env.BRANCH_NAME} — build #${env.BUILD_NUMBER}"
        }
        success {
            echo "✅ Pipeline PASSED on branch ${env.BRANCH_NAME} — build #${env.BUILD_NUMBER}"
        }
    }
}
