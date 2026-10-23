pipeline {
    agent any
    
    stages {
        stage('Checkout Code') {
            steps {
                checkout scm
                echo "Код успешно скачан из репозитория!"
            }
        }
        stage('Test Trigger') {
            steps {
                echo "Ура! Пайплайн автоматически запустился по вебхуку из GitHub!"
            }
        }
    }
}
