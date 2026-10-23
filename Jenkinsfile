pipeline {
    agent any

    options {
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
            // Говорим Jenkins выполнить этот конкретный шаг ВНУТРИ контейнера Hadolint
            agent {
                docker { 
                    image 'hadolint/hadolint:latest-alpine'
                    // Этот аргумент заставляет контейнер запуститься во временном режиме
                    args '-u root'
                }
            }
            steps {
                echo "=== Шаг 1.2: Валидация Dockerfile линтером hadolint ==="
                // Внутри контейнера hadolint бинарник доступен напрямую!
                sh 'hadolint Dockerfile'
            }
        }

        stage('Build Image') {
            steps {
                echo "=== Шаг 1.3: Сборка Docker-образа приложения ==="
                echo "На этом шаге мы настроим Docker-сборщик (Kaniko или Docker-в-K8s)"
            }
        }
    }
}
