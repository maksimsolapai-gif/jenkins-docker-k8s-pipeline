pipeline {
    // Декларируем динамический под агента в Kubernetes
    agent {
        kubernetes {
            yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: jenkins-dynamic-agent
  annotations:
    # Важнейшая аннотация из подсказки к заданию: отключаем Istio-сайдкар
    sidecar.istio.io/inject: "false"
spec:
  containers:
  # Контейнер 1: Инструменты сборки (используем alpine c curl для тестов)
  - name: builder
    image: alpine:3.18
    command: ["sleep"]
    args: ["99d"]
  # Контейнер 2: Линтер и инструменты тестирования
  - name: tester
    image: alpine:3.18
    command: ["sleep"]
    args: ["99d"]
"""
        }
    }

    options {
        timeout(time: 1, unit: 'HOURS')
        ansiColor('xterm')
    }

    environment {
        REGISTRY        = "docker.io"
        IMAGE_NAME      = "maksimsolapai-gif/jenkins-test-app"
        IMAGE_TAG       = "${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout Code') {
            steps {
                // Скачивание кода из Git всегда происходит в дефолтном системном контейнере jnlp
                checkout scm
                echo "Код успешно загружен в динамический под агента!"
            }
        }

         stage('Lint Dockerfile') {
            steps {
                container('tester') {
                    echo "=== Выполнение линтинга в контейнере TESTER ==="
                    echo "Проверка имени хоста текущего контейнера (имя динамического пода):"
                    sh '''#!/bin/sh
                    hostname
                    
                    # Доустанавливаем curl в чистый alpine для скачивания hadolint
                    apk add --no-cache curl
                    if [ ! -f ./hadolint ]; then
                        curl -sSL -o hadolint https://github.com
                        chmod +x hadolint
                    fi
                    ./hadolint Dockerfile || echo "Warnings found by hadolint"
                    '''
                }
            }
        }

        stage('Build & Push Image') {
            steps {
                container('builder') {
                    echo "=== Выполнение сборки в контейнере BUILDER ==="
                    echo "Проверка имени хоста текущего контейнера (то же имя пода):"
                    sh '''#!/bin/sh
                    hostname
                    '''
                    withCredentials([usernamePassword(credentialsId: 'registry-credentials', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                        sh """#!/bin/sh
                        echo "Авторизация пользователя \${REG_USER} внутри контейнера builder"
                        echo "Имитация Cloud-Native сборки образа: \${REGISTRY}/\text{\${IMAGE_NAME}}:\${IMAGE_TAG}"
                        """
                    }
                }
            }
        }


        stage('Deploy to Pre-Prod') {
            when {
                expression { return env.GIT_BRANCH && env.GIT_BRANCH.endsWith('main') }
            }
            steps {
                container('tester') {
                    echo "=== Деплой в Pre-Prod через контейнер TESTER ==="
                    // ИСПРАВЛЕНО: добавляем многострочный блок с шебангом
                    sh '''#!/bin/sh
                    echo "kubectl apply -f k8s/deployment.yaml -n pre-prod"
                    '''
                }
            }
        }

        stage('Approve Production Rollout') {
            when {
                expression { return env.GIT_BRANCH && env.GIT_BRANCH.endsWith('main') }
            }
            options {
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                echo "=== Ожидание подтверждения от администратора ==="
                input message: "Развернуть сборку #${BUILD_NUMBER} в Production?", ok: "Да, деплоим в Prod!"
            }
        }

        stage('Deploy to Prod') {
            when {
                expression { return env.GIT_BRANCH && env.GIT_BRANCH.endsWith('main') }
            }
            steps {
                container('tester') {
                    echo "=== Деплой в Prod через контейнер TESTER ==="
                    // ИСПРАВЛЕНО: добавляем многострочный блок с шебангом
                    sh '''#!/bin/sh
                    echo "kubectl apply -f k8s/deployment.yaml -n prod"
                    '''
                }
            }
        }



    post {
        always {
            echo "=== Блок Post-Cleanup ==="
            echo "Очистка конфигураций завершена. Динамический под готовит самоликвидацию."
        }
    }
}
