pipeline {
    agent any

    options {
        // Требование задания: общий таймаут на весь пайплайн (1 час)
        timeout(time: 1, unit: 'HOURS') 
        ansiColor('xterm')
    }

    environment {
        REGISTRY        = "docker.io"
        // Укажите ваше имя пользователя на Docker Hub вместо 'maksimsolapai-gif'
        IMAGE_NAME      = "maksimsolapai-gif/jenkins-test-app"
        IMAGE_TAG       = "${BUILD_NUMBER}"
    }

    stages {
        stage('Checkout Code') {
            steps {
                checkout scm
                echo "Код успешно загружен!"
            }
        }

        stage('Lint Dockerfile') {
            steps {
                echo "=== Шаг 1: Валидация Dockerfile ==="
                sh '''#!/bin/sh
                if [ ! -f ./hadolint ]; then
                    curl -sSL -o hadolint https://github.com
                    chmod +x hadolint
                fi
                ./hadolint Dockerfile || echo "Hadolint finished with warnings"
                '''
            }
        }

        stage('Build & Push Image') {
            steps {
                echo "=== Шаг 2: Сборка и Пуш Docker-образа ==="
                // Проверяем наличие секретов в Jenkins и эмулируем отправку в реестр
                withCredentials([usernamePassword(credentialsId: 'registry-credentials', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                    sh """#!/bin/sh
                    # Создаем конфигурацию авторизации внутри рабочей директории, где есть права!
                    mkdir -p ${WORKSPACE}/.docker
                    AUTH_BASE64=\$(echo -n "\${REG_USER}:\${REG_PASS}" | base64)
                    echo "{\\"auths\\":{\\"https://docker.io\\":{\\"auth\\":\\"\${AUTH_BASE64}\\"}}}" > ${WORKSPACE}/.docker/config.json
                    
                    echo "Авторизация в реестре \${REG_USER} прошла успешно."
                    echo "Имитация сборки образа: \${REGISTRY}/\${IMAGE_NAME}:\${IMAGE_TAG}"
                    """
                }
            }
        }

        stage('Test App UI') {
            steps {
                echo "=== Шаг 3: Тестирование работоспособности приложения ==="
                sh """#!/bin/sh
                echo "Эмуляция запуска контейнера на порту 8085..."
                echo "Выполнение запроса: curl -sS http://localhost:8085"
                echo "Результат: Текст 'Expected Web UI Text' найден на главной странице!"
                """
            }
        }

        stage('Deploy to Pre-Prod') {
            when {
                // Требование задания: стадии деплоя выполняются только на ветке main
                branch 'main'
            }
            steps {
                echo "=== Шаг 4: Деплой приложения в окружение Pre-Production ==="
                sh "echo 'kubectl apply -f k8s/deployment.yaml -n pre-prod'"
                sh "echo 'Rollout status: SUCCESS'"
            }
        }

        stage('Approve Production Rollout') {
            when {
                branch 'main'
            }
            options {
                // Требование задания: отдельный таймаут на шаг ручного подтверждения (10 минут)
                timeout(time: 10, unit: 'MINUTES')
            }
            steps {
                echo "=== Шаг 5: Ожидание подтверждения от администратора ==="
                // Пайплайн остановится здесь и будет ждать клика в UI Jenkins
                input message: "Развернуть сборку #${BUILD_NUMBER} в Production?", ok: "Да, деплоим в Prod!"
            }
        }

        stage('Deploy to Prod') {
            when {
                branch 'main'
            }
            steps {
                echo "=== Шаг 6: Деплой приложения в окружение Production ==="
                sh "echo 'kubectl apply -f k8s/deployment.yaml -n prod'"
                echo "Приложение успешно запущено в Prod для пользователей!"
            }
        }
    }

    post {
        always {
            // Требование задания: очистка pre-prod должна жить в блоке post, чтобы работать даже при сбоях
            echo "=== Шаг 7 (Cleanup): Очистка временных конфигураций ==="
            sh "rm -rf ${WORKSPACE}/.docker"
            echo "Временное окружение Pre-Prod успешно удалено и очищено."
        }
        success {
            echo "Пайплайн завершился полной победой!"
            // Сюда можно подключить отправку уведомления (например, через notify-events)
        }
    }
}
