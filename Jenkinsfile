pipeline {
  agent any
  options {
    disableConcurrentBuilds()
    timestamps()
    timeout(time: 15, unit: 'MINUTES')
  }
  triggers { cron('0 4 * * *') }
  parameters {
    choice(name: 'FLOW_SCOPE', choices: ['all', 'business_popup', 'forms'], description: 'all runs both business pop-up pages and business forms; forms runs Place/checkbox/select cases.')
    choice(name: 'DOMAIN', choices: ['all', 'beeline-home.online', 'beeline-internet.online', 'samara.beeline-ru.online', 'online-beeline.ru', 'dom-provider.online', 'providerdom.ru', 'mega-home-internet.ru', 'mega-premium.ru', 'moskva.mega-home-internet.ru', 'internet-mts-home.online', 'mts-home-gpon.ru', 'mts-home-online.ru', 'mts-home.online', 'samara.mts-home.online', 'mts-internet.online', 'rtk-home.ru', 'rtk-internet.online', 'rtk-ru.online', 'rt-internet.online', 'rtk-home-internet.ru', 'samara.rtk-ru.online', 't2-ru.online'], description: 'Exact landing domain. all runs the full active scope.')
    choice(name: 'PROVIDER', choices: ['all', 'beeline', 'mts', 'rostelecom', 'megafon', 'domru', 't2', 'ttk'], description: 'Optional provider filter.')
    string(name: 'CASE_FILE', defaultValue: 'config/business_cases.json', description: 'Unified active case registry.')
    string(name: 'DATA_FILE', defaultValue: 'config/data/samara.json', description: 'Path to an environment-confirmed data profile on the agent.')
    booleanParam(name: 'ALERT_SEND', defaultValue: true, description: 'Send Telegram alerts on failures and recoveries.')
    booleanParam(name: 'ALERT_RECOVERED', defaultValue: true, description: 'Include recovered domains in the alert.')
    booleanParam(name: 'USE_TELEGRAM_PROXY', defaultValue: true, description: 'Use Big_landing_test Telegram proxy credentials.')
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
          def flowKind = params.FLOW_SCOPE == 'business_popup' ? 'business_page' : (params.FLOW_SCOPE == 'forms' ? 'business_option' : '')
          def domain = params.DOMAIN == 'all' ? '' : params.DOMAIN
          def provider = params.PROVIDER == 'all' ? '' : params.PROVIDER
          withEnv(["BIZ_ENV=prod", "BIZ_FLOW_KIND=${flowKind}", "BIZ_DOMAIN=${domain}",
                   "BIZ_PROVIDER=${provider}",
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
      script {
        try {
          def notifySummary = {
            withEnv(["ALLURE_RESULTS_DIR=allure-results", "RUN_URL=${env.BUILD_URL}", "ALLURE_URL=${env.BUILD_URL}allure/",
                     "ALERT_SEND_ENABLED=${params.ALERT_SEND}", "ALERT_RECOVERED_ENABLED=${params.ALERT_RECOVERED}"]) {
              if (isUnix()) { sh '.venv/bin/python tools/notify_from_allure.py' }
              else { bat '.venv\\Scripts\\python.exe tools/notify_from_allure.py' }
            }
          }
          if (params.USE_TELEGRAM_PROXY) {
            withCredentials([
              string(credentialsId: 'telegram_proxy_url', variable: 'TELEGRAM_PROXY_URL'),
              string(credentialsId: 'telegram_proxy_auth_secret', variable: 'TELEGRAM_PROXY_AUTH_SECRET'),
              string(credentialsId: 'telegram_proxy_global_test', variable: 'TELEGRAM_PROXY_CREDS')
            ]) {
              notifySummary()
            }
          } else {
            notifySummary()
          }
        } catch (err) { echo "Alert generation failed: ${err}" }
      }
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
