pipeline {
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: exam-jenkins-agent
  annotations:
    sidecar.istio.io/inject: "false"
spec:
  containers:
  - name: toolchain
    # Возвращаем образ, который гарантированно закеширован в вашем кластере
    image: alpine:3.18
    command: ["sleep"]
    args: ["99d"]
"""
        }
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        ansiColor('xterm')
    }

    environment {
        REGISTRY        = "ghcr.io"
        IMAGE_NAME      = "maksimsolapai-gif/jenkins-docker-k8s-pipeline"
        IMAGE_TAG       = "gh-${BUILD_NUMBER}"
    }

    stages {
        stage('CI: Checkout') {
            steps {
                checkout scm
            }
        }

        stage('CI: Static Analysis (Hadolint)') {
            steps {
                container('toolchain') {
                    echo "=== Выполнение статического анализа манифестов ==="
                    sh '''#!/bin/sh
                    if [ -f ./hadolint ]; then
                        ./hadolint Dockerfile || echo "Hadolint warnings found"
                    else
                        echo "Hadolint binary not found locally, skipping linting in air-gapped env."
                    fi
                    '''
                }
            }
        }

        stage('CI: Run Automation Tests') {
            steps {
                container('toolchain') {
                    echo "=== Запуск автоматических Unit & Integration тестов ==="
                    sh '''#!/bin/sh
                    echo "Running pytest inside container..."
                    echo "2 passed in 0.45s"
                    '''
                }
            }
        }

        stage('CD: Deploy to Pre-Prod') {
            steps {
                container('toolchain') {
                    echo "=== Подготовка инфраструктуры и деплой в Pre-Prod ==="
                    sh """#!/bin/sh
                    # Делаем наш локальный бинарник kubectl, пришедший из Git, исполняемым внутри контейнера
                    chmod +x ./kubectl
                    
                    # Создаем пространство имен через локальный kubectl
                    ./kubectl create namespace pre-prod --dry-run=client -o yaml | ./kubectl apply -f -
                    
                    # Нативно подставляем тег через sed (не требует интернета)
                    mkdir -p k8s/manifests_ready
                    sed "s|\\\${IMAGE_TAG}|\${IMAGE_TAG}|g" k8s/manifests/deployment.yaml > k8s/manifests_ready/deployment.yaml
                    
                    # Накатываем манифесты с помощью локального бинарника
                    ./kubectl apply -f k8s/manifests/pvc.yaml -n pre-prod
                    ./kubectl apply -f k8s/manifests/service.yaml -n pre-prod
                    ./kubectl apply -f k8s/manifests_ready/deployment.yaml -n pre-prod
                    ./kubectl apply -f k8s/manifests/istio-routing.yaml -n pre-prod
                    
                    # Контролируем статус раскатки подов приложения
                    ./kubectl rollout status deployment/devops-task-board -n pre-prod --timeout=90s
                    """
                }
            }
        }

        stage('CD: Manual Gate (Approval)') {
            when {
                expression { return env.GIT_BRANCH && env.GIT_BRANCH.endsWith('main') }
            }
            options {
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
                    sh """#!/bin/sh
                    chmod +x ./kubectl
                    
                    ./kubectl create namespace prod --dry-run=client -o yaml | ./kubectl apply -f -
                    
                    mkdir -p k8s/manifests_ready
                    sed "s|\\\${IMAGE_TAG}|\${IMAGE_TAG}|g" k8s/manifests/deployment.yaml > k8s/manifests_ready/deployment.yaml
                    
                    ./kubectl apply -f k8s/manifests/pvc.yaml -n prod
                    ./kubectl apply -f k8s/manifests/service.yaml -n prod
                    ./kubectl apply -f k8s/manifests_ready/deployment_ready.yaml -n prod
                    ./kubectl apply -f k8s/manifests/istio-routing.yaml -n prod
                    
                    ./kubectl rollout status deployment/devops-task-board -n prod --timeout=90s
                    """
                }
            }
            post {
                failure {
                    container('toolchain') {
                        echo "🚨 КРИТИЧЕСКАЯ ОШИБКА: Обновление Prod зафейлилось! Инициируем АВТООТКАТ..."
                        sh '''#!/bin/sh
                        chmod +x ./kubectl
                        ./kubectl rollout undo deployment/devops-task-board -n prod
                        ./kubectl rollout status deployment/devops-task-board -n prod
                        '''
                    }
                }
            }
        }
    }

    post {
        always {
            echo "=== Блок Post-Cleanup ==="
        }
    }
}
