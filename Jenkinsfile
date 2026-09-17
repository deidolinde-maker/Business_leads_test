pipeline {
  agent any
  options {
    disableConcurrentBuilds()
    timestamps()
    timeout(time: 15, unit: 'MINUTES')
  }
  parameters {
    choice(name: 'MODE', choices: ['representative', 'local', 'collect', 'live'], description: 'representative is the default non-submitting preflight of reviewed brand/type cases; live needs one exact verified CASE_ID.')
    choice(name: 'TARGET_ENV', choices: ['unset', 'stage', 'prod'], description: 'Required for collect/live. City is always Samara.')
    string(name: 'PROVIDER', defaultValue: '', description: 'Provider filter for collect only. Leave empty for representative and live.')
    string(name: 'CASE_ID', defaultValue: '', description: 'Required for live: one exact active case ID. Leave empty for representative.')
    string(name: 'DATA_FILE', defaultValue: 'config/data/samara.json', description: 'Path to an environment-confirmed data profile on the agent.')
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Dependencies') {
      steps {
        script {
          def cacheBase = env.JENKINS_HOME ?: env.HOME ?: env.WORKSPACE
          if (isUnix()) {
            env.PIP_CACHE_DIR = "${cacheBase}/.cache/business-leads-test/pip"
            env.PLAYWRIGHT_BROWSERS_PATH = "${cacheBase}/.cache/business-leads-test/playwright"
            sh '''
              mkdir -p "$PIP_CACHE_DIR" "$PLAYWRIGHT_BROWSERS_PATH"
              if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
              .venv/bin/python -m pip install --cache-dir "$PIP_CACHE_DIR" --prefer-binary -e .
              .venv/bin/python -m playwright install chromium
            '''
          } else {
            env.PIP_CACHE_DIR = "${cacheBase}\\.cache\\business-leads-test\\pip"
            env.PLAYWRIGHT_BROWSERS_PATH = "${cacheBase}\\.cache\\business-leads-test\\playwright"
            bat '''
              if not exist "%PIP_CACHE_DIR%" mkdir "%PIP_CACHE_DIR%"
              if not exist "%PLAYWRIGHT_BROWSERS_PATH%" mkdir "%PLAYWRIGHT_BROWSERS_PATH%"
              if not exist ".venv\\Scripts\\python.exe" python -m venv .venv
              .venv\\Scripts\\python.exe -m pip install --cache-dir "%PIP_CACHE_DIR%" --prefer-binary -e .
              .venv\\Scripts\\python.exe -m playwright install chromium
            '''
          }
        }
      }
    }
    stage('Checks') {
      steps {
        script {
          withEnv(["BIZ_MODE=${params.MODE}", "BIZ_ENV=${params.TARGET_ENV}",
                   "BIZ_PROVIDER=${params.PROVIDER}", "BIZ_CASE_ID=${params.CASE_ID}",
                   "BIZ_DATA_FILE=${params.DATA_FILE}"]) {
            if (isUnix()) { sh '.venv/bin/python tools/ci_run.py' }
            else { bat '.venv\\Scripts\\python.exe tools/ci_run.py' }
          }
        }
      }
    }
  }
  post {
    always {
      archiveArtifacts artifacts: 'artifacts/**,allure-results/**', allowEmptyArchive: true
      junit testResults: 'artifacts/results.xml', allowEmptyResults: true
    }
  }
}
