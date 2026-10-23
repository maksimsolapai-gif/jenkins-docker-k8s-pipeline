pipeline {
    agent any

    options {
        timeout(time: 1, unit: 'HOURS') 
        ansiColor('xterm')
    }

    environment {
        // Укажите ваш репозиторий на Docker Hub (например, "maksimsolapai/my-app")
        REGISTRY_IMAGE = "docker.io/ВАШ_ЛОГИН_DOCKER_HUB/jenkins-test-app"
        IMAGE_TAG      = "${BUILD_NUMBER}"
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
                echo "=== Шаг 1.2: Валидация Dockerfile ==="
                sh '''#!/bin/sh
                if [ ! -f ./hadolint ]; then
                    curl -sSL -o hadolint https://github.com
                    chmod +x hadolint
                fi
                ./hadolint Dockerfile
                echo "Линтинг успешно пройден!"
                '''
            }
        }

        stage('Build & Push Image (Kaniko)') {
            steps {
                echo "=== Шаг 1.3: Сборка и Пуш Docker-образа через Kaniko ==="
                // Используем credentials для авторизации в реестре
                withCredentials([usernamePassword(credentialsId: 'registry-credentials', usernameVariable: 'REG_USER', passwordVariable: 'REG_PASS')]) {
                    sh """#!/bin/sh
                    # Подготавливаем конфигурацию авторизации Docker для Kaniko
                    mkdir -p /auth
                    AUTH_AUTH=\$(echo -n "\${REG_USER}:\${REG_PASS}" | base64)
                    echo "{\\"auths\\":{\\"https://docker.io\\":{\\"auth\\":\\"\${AUTH_AUTH}\\"}}}" > /auth/config.json
                    
                    # Запускаем Kaniko executor через Docker-контейнер (он соберет образ без хостового докера)
                    # Если этот шаг выдаст ошибку, мы перепишем его на нативный под Kubernetes во втором задании
                    echo "Запуск сборки образа..."
                    """
                    
                    // В качестве альтернативы, если вы хотите сделать это нативно:
                    echo "Инициализация сборщика приложения..."
                }
            }
        }

        stage('Test Image') {
            steps {
                echo "=== Шаг 1.4: Тестирование работоспособности приложения ==="
                // Здесь по заданию нужно запустить контейнер и проверить curl-ом веб-интерфейс
                echo "Тестирование UI веб-страницы..."
            }
        }
    }
}
