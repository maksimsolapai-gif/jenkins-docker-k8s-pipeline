pipeline {
    agent any

    options {
        // Условие задания: общий таймаут на весь пайплайн — 1 час
        timeout(time: 1, unit: 'HOURS') 
        ansiColor('xterm')
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
                echo "=== Шаг 1.2: Валидация Dockerfile линтером hadolint ==="
                // Запускаем hadolint через официальный Docker-контейнер, передавая локальный Dockerfile
                sh 'docker run --rm -i hadolint/hadolint < Dockerfile'
            }
        }

        stage('Build Image') {
            steps {
                echo "=== Шаг 1.3: Сборка Docker-образа приложения ==="
                // Собираем локальный образ с тегом текущей сборки Jenkins
                sh 'docker build -t local-app-test:${BUILD_NUMBER} .'
            }
        }
    }
}
