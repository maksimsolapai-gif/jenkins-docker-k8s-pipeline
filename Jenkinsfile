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
  - name: kaniko
    image: gcr.io/kaniko-project/executor:v1.14.0-debug
    command: ["sleep"]
    args: ["99d"]
  - name: toolchain
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
        REGISTRY        = "docker.io"
        IMAGE_NAME      = "maksimsolap/exam-task-board"
        IMAGE_TAG       = "${BUILD_NUMBER}"
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
                    apk add --no-cache python3 py3-pip
                    pip install --break-system-packages fastapi pytest httpx jinja2 python-multipart uvicorn==0.27.1
                    
                    mkdir -p /app/data
                    chmod 777 /app/data
                    
                    PYTHONPATH=. pytest tests/ -v
                    '''
                }
            }
        }

        stage('CI: Cloud-Native Build & Push') {
            steps {
                container('kaniko') {
                    echo "=== Сборка и отправка Docker-образа через Kaniko ==="
                    withCredentials([usernamePassword(credentialsId: 'registry-credentials', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                        sh """#!/bin/sh
                        mkdir -p /kaniko/.docker
                        
                        # Передаем логин и токен напрямую в поля конфигурации Kaniko
                        echo "{\\"auths\\":{\\"https://index.docker.io/v1/\\":{\\"username\\":\\"\${REG_USER}\\",\\"password\\":\\"\${REG_PASS}\\"}}}" > /kaniko/.docker/config.json
                        
                        # Запуск сборщика с флагом дебага для детального логирования, если что-то пойдет не так
                        /kaniko/executor --context=\${WORKSPACE} \
                                         --dockerfile=\text{\${WORKSPACE}}/Dockerfile \
                                         --destination=\text{\${REGISTRY}}/\text{\${IMAGE_NAME}}:\text{\${IMAGE_TAG}}
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
                    
                    kubectl create namespace pre-prod --dry-run=client -o yaml | kubectl apply -f -
                    
                    envsubst < k8s/manifests/deployment.yaml > k8s/manifests/deployment_ready.yaml
                    
                    kubectl apply -f k8s/manifests/pvc.yaml -n pre-prod
                    kubectl apply -f k8s/manifests/service.yaml -n pre-prod
                    kubectl apply -f k8s/manifests/deployment_ready.yaml -n pre-prod
                    kubectl apply -f k8s/manifests/istio-routing.yaml -n pre-prod
                    
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
                    
                    kubectl create namespace prod --dry-run=client -o yaml | kubectl apply -f -
                    
                    envsubst < k8s/manifests/deployment.yaml > k8s/manifests/deployment_ready.yaml
                    
                    kubectl apply -f k8s/manifests/pvc.yaml -n prod
                    kubectl apply -f k8s/manifests/service.yaml -n prod
                    kubectl apply -f k8s/manifests/deployment_ready.yaml -n prod
                    kubectl apply -f k8s/manifests/istio-routing.yaml -n prod
                    
                    kubectl rollout status deployment/devops-task-board -n prod --timeout=90s
                    '''
                }
            }
            post {
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
            withCredentials([string(credentialsId: 'slack-webhook-url', variable: 'SLACK_URL')]) {
                container('toolchain') {
                    sh '''#!/bin/sh
                    apk add --no-cache curl
                    
                    PAYLOAD='{"attachments": [{"color": "good", "title": "✅ Jenkins Pipeline: SUCCESS", "text": "Pipeline completed flawlessly. Application has been promoted to Production.", "fields": [{"title": "Project", "value": "DevOps Task Board", "short": true}, {"title": "Build Number", "value": "#'${BUILD_NUMBER}'", "short": true}, {"title": "Environment", "value": "Production (Istio Routed)", "short": true}], "footer": "Jenkins Kubernetes GitOps Agent"}]}'
                    
                    curl -X POST -H 'Content-type: application/json' --data "$PAYLOAD" "$SLACK_URL"
                    '''
                }
            }
        }
        failure {
            withCredentials([string(credentialsId: 'slack-webhook-url', variable: 'SLACK_URL')]) {
                container('toolchain') {
                    sh '''#!/bin/sh
                    apk add --no-cache curl
                    
                    PAYLOAD='{"attachments": [{"color": "danger", "title": "🚨 Jenkins Pipeline: FAILED", "text": "The pipeline encountered a critical error during execution.", "fields": [{"title": "Project", "value": "DevOps Task Board", "short": true}, {"title": "Build Number", "value": "#'${BUILD_NUMBER}'", "short": true}], "footer": "Jenkins Kubernetes GitOps Agent"}]}'
                    
                    curl -X POST -H 'Content-type: application/json' --data "$PAYLOAD" "$SLACK_URL"
                    '''
                }
            }
        }
    }
}
