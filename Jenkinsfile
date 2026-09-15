pipeline {
  agent any
  options {
    disableConcurrentBuilds()
    timestamps()
    timeout(time: 15, unit: 'MINUTES')
  }
  parameters {
    choice(name: 'MODE', choices: ['local', 'collect', 'live'], description: 'local uses synthetic forms only; live needs verified active cases.')
    choice(name: 'TARGET_ENV', choices: ['unset', 'stage', 'prod'], description: 'Required for collect/live. City is always Samara.')
    string(name: 'PROVIDER', defaultValue: '', description: 'Exact provider filter; empty selects the whole environment.')
    string(name: 'CASE_ID', defaultValue: '', description: 'Optional exact case ID.')
    string(name: 'DATA_FILE', defaultValue: 'config/data/samara.json', description: 'Path to an environment-confirmed data profile on the agent.')
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Dependencies') {
      steps {
        script {
          if (isUnix()) {
            sh 'python3 -m venv .venv && .venv/bin/python -m pip install -e . && .venv/bin/python -m playwright install chromium'
          } else {
            bat 'python -m venv .venv && .venv\\Scripts\\python.exe -m pip install -e . && .venv\\Scripts\\python.exe -m playwright install chromium'
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
