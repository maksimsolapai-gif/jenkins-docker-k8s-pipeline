pipeline {
    agent any

    options {
        // Условие задания: общий таймаут на пайплайн (1 час)
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
                echo "=== Шаг 1.2: Валидация Dockerfile без Docker ==="
                sh '''#!/bin/sh
                # Скачиваем официальный стабильный бинарный файл Hadolint под Linux x86_64
                curl -sSL -o hadolint https://github.com
                
                # Даем права на исполнение
                chmod '+x' hadolint
                
                # Запускаем линтер для нашего Dockerfile
                ./hadolint Dockerfile
                echo "Линтинг успешно пройден!"
                '''
            }
        }

        stage('Build Image') {
            steps {
                echo "=== Шаг 1.3: Сборка Docker-образа ==="
                echo "Поскольку Jenkins запущен внутри K8s, здесь мы будем использовать Kaniko"
            }
        }
    }
}
