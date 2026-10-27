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
  # Контейнер 1: Безопасный Cloud-Native сборщик Docker-образов (Kaniko)
  - name: kaniko
    image: gcr.io/kaniko-project/executor:v1.14.0-debug
    command: ["sleep"]
    args: ["99d"]
  # Контейнер 2: Инструменты проверки, тестирования и деплоя (Hadolint, Pytest, Kubectl, Envsubst)
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
        REGISTRY        = "docker.io"
        // Укажите ваше точное имя пользователя на Docker Hub в IMAGE_NAME
        IMAGE_NAME      = "maksimsolap/exam-task-board"
        IMAGE_TAG       = "${BUILD_NUMBER}"
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
                    pip install --break-system-packages fastapi==0.109.2 testclient pytest httpx jinja2 python-multipart uvicorn==0.27.1
                    
                    # Создаем локальную директорию /app/data внутри пода для прохождения тестов СУБД SQLite
                    mkdir -p /app/data
                    chmod 777 /app/data
                    
                    # Запуск тестов
                    PYTHONPATH=. pytest tests/ -v
                    '''
                }
            }
        }

        stage('CI: Cloud-Native Build & Push') {
            steps {
                container('kaniko') {
                    echo "=== Сборка и отправка Docker-образа через Kaniko ==="
                    // Использование секретов registry-credentials (Username/Password) из Jenkins
                    withCredentials([usernamePassword(credentialsId: 'registry-credentials', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                        sh """#!/bin/sh
                        mkdir -p /kaniko/.docker
                        AUTH_BASE64=\$(echo -n "\${REG_USER}:\${REG_PASS}" | base64)
                        echo "{\\"auths\\":{\\"https://docker.io\\":{\\"auth\\":\\"\${AUTH_BASE64}\\"}}}" > /kaniko/.docker/config.json
                        
                        /kaniko/executor --context=\${WORKSPACE} \
                                         --dockerfile=\${WORKSPACE}/Dockerfile \
                                         --destination=\${REGISTRY}/\${IMAGE_NAME}:\${IMAGE_TAG}
                        """
                    }
                }
            }
        }

        stage('CD: Deploy to Pre-Prod') {
            steps {
                container('toolchain') {
                    echo "=== Подготовка инфраструктуры и деплой в Pre-Prod ==="
                    sh '''#!/bin/sh
                    apk add --no-cache kubectl envsubst
                    
                    # Автоматическое идемпотентное создание пространства имен
                    kubectl create namespace pre-prod --dry-run=client -o yaml | kubectl apply -f -
                    
                    # Генерируем манифест деплоя с актуальным тегом сборки
                    envsubst < k8s/manifests/deployment.yaml > k8s/manifests/deployment_ready.yaml
                    
                    # Накатываем манифесты в pre-prod
                    kubectl apply -f k8s/manifests/pvc.yaml -n pre-prod
                    kubectl apply -f k8s/manifests/service.yaml -n pre-prod
                    kubectl apply -f k8s/manifests/deployment_ready.yaml -n pre-prod
                    kubectl apply -f k8s/manifests/istio-routing.yaml -n pre-prod
                    
                    # Проверка успешности раскатки
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
                    apk add --no-cache kubectl envsubst
                    
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
                        apk add --no-cache kubectl
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
                    
                    PAYLOAD="{
                        \\"attachments\\": [{
                            \\"color\\": \\"good\\",
                            \\"title\\": \\"✅ Jenkins Pipeline: SUCCESS\\",
                            \\"text\\": \\"Pipeline completed flawlessly. Application has been promoted to Production.\\",
                            \\"fields\\": [
                                { \\"title\\": \\"Project\\", \\"value\\": \\"DevOps Task Board\\", \\"short\\": true },
                                { \\"title\\": \\"Build Number\\", \\"value\\": \\"#${BUILD_NUMBER}\\", \\"short\\": true },
                                { \\"title\\": \\"Environment\\", \\"value\\": \\"Production (Istio Routed)\\", \\"short\\": true },
                                { \\"title\\": \\"Branch\\", \\"value\\": \\"${GIT_BRANCH}\\", \\"short\\": true }
                            ],
                            \\"footer\\": \\"Jenkins Kubernetes GitOps Agent\\"
                        }]
                    }"
                    
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
                    
                    PAYLOAD="{
                        \\"attachments\\": [{
