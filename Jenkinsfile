pipeline {
  agent any
  options {
    disableConcurrentBuilds()
    timestamps()
    timeout(time: 15, unit: 'MINUTES')
  }
  parameters {
    choice(name: 'MODE', choices: ['representative', 'live', 'local', 'collect'], description: 'representative is a non-submitting preflight. live sends one lead for every active case selected by PROVIDER and CASE_ID; leave both empty for all active cases.')
    choice(name: 'TARGET_ENV', choices: ['prod', 'unset', 'stage'], description: 'Required for representative, collect and live. City is always Samara.')
    choice(name: 'PROVIDER', choices: ['', 'beeline', 'mts'], description: 'Optional scope for collect and live. Leave empty to use all matching cases.')
    string(name: 'CASE_ID', defaultValue: '', description: 'Optional exact active case ID for live. Leave empty to run all active cases in the selected scope.')
    string(name: 'CASE_FILE', defaultValue: 'config/place_scope_23.json', description: 'Case registry for this job. The default file contains the approved 23 Place/checkaddress cases.')
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
          if (isUnix()) { sh 'rm -rf artifacts allure-results && mkdir -p artifacts allure-results' }
          else { bat 'if exist artifacts rmdir /s /q artifacts & if exist allure-results rmdir /s /q allure-results & mkdir artifacts & mkdir allure-results' }
          withEnv(["BIZ_MODE=${params.MODE}", "BIZ_ENV=${params.TARGET_ENV}",
                   "BIZ_PROVIDER=${params.PROVIDER}", "BIZ_CASE_ID=${params.CASE_ID}",
                   "BIZ_DATA_FILE=${params.DATA_FILE}", "BIZ_CASE_FILE=${params.CASE_FILE}"]) {
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
      script {
        try {
          allure includeProperties: false, jdk: '', results: [[path: 'allure-results']]
        } catch (err) {
          echo "Allure report publishing failed: ${err}"
        }
      }
    }
  }
}
