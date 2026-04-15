pipeline {
    agent any

    environment {
        EC2_HOST     = "${env.EC2_HOST}"
        SSH_KEY_PATH = "${env.SSH_KEY_PATH}"
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out source...'
                checkout scm
            }
        }

        stage('Install') {
            steps {
                echo 'Installing Python dependencies...'
                sh 'pip3 install -r backend/requirements.txt'
            }
        }

        stage('Test') {
            steps {
                echo 'Running pytest...'
                sh 'pytest backend/tests/ -v --tb=short'
            }
            post {
                failure {
                    echo 'Tests failed — aborting deploy.'
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo "Deploying to EC2: ${env.EC2_HOST}"
                sh 'chmod +x infra/deploy.sh && bash infra/deploy.sh'
            }
        }
    }

    post {
        success {
            echo 'Pipeline succeeded.'
        }
        failure {
            echo 'Pipeline failed.'
        }
        always {
            echo 'Pipeline finished.'
        }
    }
}
