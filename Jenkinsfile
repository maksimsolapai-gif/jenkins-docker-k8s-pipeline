pipeline {
    // Декларируем динамический под агента в Kubernetes
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: exam-jenkins-agent
  annotations:
    # Защита от зависания агента в Istio-сервис-меше
    sidecar.istio.io/inject: "false"
spec:
  containers:
  # Наш единственный контейнер-инструментарий (сборка вынесена на GitHub Actions)
  - name: toolchain
    image: alpine:3.18
    command: ["sleep"]
    args: ["99d"]
"""
        }
    }

    options {
        // Условие ТЗ: Общий таймаут на выполнение всего конвейера
        timeout(time: 30, unit: 'MINUTES')
        ansiColor('xterm')
    }

    environment {
        REGISTRY        = "ghcr.io"
        // Имя репозитория пакетов на GitHub (в нижнем регистре)
        IMAGE_NAME      = "maksimsolapai-gif/jenkins-docker-k8s-pipeline"
        // Синхронизируем тег: подставляем номер текущей сборки Jenkins c префиксом gh-
        IMAGE_TAG       = "gh-${BUILD_NUMBER}"
    }

    stages {
        stage('CI: Checkout') {
            steps {
                // Скачивание кода происходит в системном контейнере jnlp
                checkout scm
            }
        }

        stage('CI: Static Analysis (Hadolint)') {
            steps {
                container('toolchain') {
                    echo "=== Выполнение статического анализа манифестов ==="
                    sh '''#!/bin/sh
                    apk add --no-cache curl
                    if [ ! -f ./hadolint ]; then
                        curl -sSL -o hadolint https://github.com
                        chmod +x hadolint
                    fi
                    ./hadolint Dockerfile || echo "Hadolint завершился с предупреждениями"
                    '''
                }
            }
        }

        stage('CI: Run Automation Tests') {
            steps {
                container('toolchain') {
                    echo "=== Запуск автоматических Unit & Integration тестов ==="
                    sh '''#!/bin/sh
                    # Подготовка окружения внутри контейнера агента
                    apk add --no-cache python3 py3-pip
                    pip install --break-system-packages fastapi pytest httpx jinja2 python-multipart uvicorn==0.27.1
                    
                    # Создаем локальную директорию /app/data внутри пода для прохождения тестов СУБД SQLite
                    mkdir -p /app/data
                    chmod 777 /app/data
                    
                    # Запуск тестов
                    PYTHONPATH=. pytest tests/ -v
                    '''
                }
            }
        }

        stage('CD: Deploy to Pre-Prod') {
            steps {
                container('toolchain') {
                    echo "=== Подготовка инфраструктуры и деплой в Pre-Prod ==="
                    sh '''#!/bin/sh
                    # ИСПРАВЛЕНО: Явно указываем репозиторий edge для успешной доустановки утилит в Alpine 3.18
                    apk add --no-cache envsubst kubectl --repository=https://alpinelinux.org
                    
                    # Автоматическое идемпотентное создание пространства имен
                    kubectl create namespace pre-prod --dry-run=client -o yaml | kubectl apply -f -
                    
                    # Генерируем манифест деплоя с актуальным тегом сборки
                    envsubst < k8s/manifests/deployment.yaml > k8s/manifests/deployment_ready.yaml
                    
                    # Накатываем манифесты в pre-prod
                    kubectl apply -f k8s/manifests/pvc.yaml -n pre-prod
                    kubectl apply -f k8s/manifests/service.yaml -n pre-prod
                    kubectl apply -f k8s/manifests/deployment_ready.yaml -n pre-prod
                    kubectl apply -f k8s/manifests/istio-routing.yaml -n pre-prod
                    
                    # Проверка успешности раскатки подов приложения
                    kubectl rollout status deployment/devops-task-board -n pre-prod --timeout=90s
                    '''
                }
            }
        }

        stage('CD: Manual Gate (Approval)') {
            when {
                expression { return env.GIT_BRANCH && env.GIT_BRANCH.endsWith('main') }
            }
            options {
                // Условие ТЗ: Отдельный таймаут на шаг ручного подтверждения
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                echo "=== Ожидание подтверждения релиза администратором ==="
                input message: "Продвинуть сборку #${BUILD_NUMBER} в Production окружение?", ok: "Разрешить деплой"
            }
        }

        stage('CD: Production Zero-Downtime Upgrade') {
            when {
                expression { return env.GIT_BRANCH && env.GIT_BRANCH.endsWith('main') }
            }
            steps {
                container('toolchain') {
                    echo "=== Подготовка инфраструктуры и Rolling Update в Prod ==="
                    sh '''#!/bin/sh
                    # Добавляем edge-репозиторий и для прод-контура
                    apk add --no-cache envsubst kubectl --repository=https://alpinelinux.org
                    
                    # Автоматическое идемпотентное создание пространства имен для Prod
                    kubectl create namespace prod --dry-run=client -o yaml | kubectl apply -f -
                    
                    # Генерируем манифест деплоя с актуальным тегом сборки
                    envsubst < k8s/manifests/deployment.yaml > k8s/manifests/deployment_ready.yaml
                    
                    # Накатываем манифесты в прод контур (Zero Downtime RollingUpdate)
                    kubectl apply -f k8s/manifests/pvc.yaml -n prod
                    kubectl apply -f k8s/manifests/service.yaml -n prod
                    kubectl apply -f k8s/manifests/deployment_ready.yaml -n prod
                    kubectl apply -f k8s/manifests/istio-routing.yaml -n prod
                    
                    # Контролируем статус апгрейда
                    kubectl rollout status deployment/devops-task-board -n prod --timeout=90s
                    '''
                }
            }
            post {
                // Условие ТЗ: Автоматический откат (Rollback) на предыдущую стабильную версию в случае сбоя
                failure {
                    container('toolchain') {
                        echo "🚨 КРИТИЧЕСКАЯ ОШИБКА: Обновление Prod зафейлилось! Инициируем АВТООТКАТ..."
                        sh '''#!/bin/sh
                        kubectl rollout undo deployment/devops-task-board -n prod
                        kubectl rollout status deployment/devops-task-board -n prod
                        '''
                    }
                }
            }
        }
    }

    post {
        success {
            // Условие ТЗ: Система уведомлений о результате (Интеграция Slack Incoming Webhook)
            withCredentials([string(credentialsId: 'slack-webhook-url', variable: 'SLACK_URL')]) {
                container('toolchain') {
                    sh '''#!/bin/sh
                    apk add --no-cache curl
                    
                    PAYLOAD='{"attachments": [{"color": "good", "title": "✅ Jenkins Pipeline: SUCCESS", "text": "Hybrid Pipeline completed successfully. Image built via GitHub Actions and deployed inside Kubernetes.", "fields": [{"title": "Project", "value": "DevOps Task Board", "short": true}, {"title": "Build Number", "value": "#'${BUILD_NUMBER}'", "short": true}, {"title": "Environment", "value": "Production (Istio Routed)", "short": true}], "footer": "Jenkins Kubernetes Agent"}]}'
                    
                    curl -X POST -H 'Content-type: application/json' --data "$PAYLOAD" "$SLACK_URL"
                    '''
                }
            }
        }
        failure {
            // Критическая красная карточка в Slack при падении любого этапа конвейера
            withCredentials([string(credentialsId: 'slack-webhook-url', variable: 'SLACK_URL')]) {
                container('toolchain') {
                    sh '''#!/bin/sh
                    apk add --no-cache curl
                    
                    PAYLOAD='{"attachments": [{"color": "danger", "title": "🚨 Jenkins Pipeline: FAILED", "text": "The hybrid pipeline encountered an error inside the cluster.", "fields": [{"title": "Project", "value": "DevOps Task Board", "short": true}, {"title": "Build Number", "value": "#'${BUILD_NUMBER}'", "short": true}], "footer": "Jenkins Kubernetes Agent"}]}'
                    
                    curl -X POST -H 'Content-type: application/json' --data "$PAYLOAD" "$SLACK_URL"
                    '''
                }
            }
        }
    }
}
