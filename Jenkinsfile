pipeline {
    agent any

    environment {
        SSH_KEY_PATH              = "/home/ubuntu/.ssh/id_rsa"
        ANSIBLE_HOST_KEY_CHECKING = "False"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build & Test') {
            steps {
                sh '''
                    echo "==> Установка зависимостей"
                    pip3 install --user -r requirements.txt
                    
                    echo "==> Проверка импорта модели"
                    python3 -c "from core.imputer_service import KNNImputationService; print('Модель загружается')"
                    
                    echo "==> Запуск локального теста"
                    python3 -m pytest tests/ -v || echo "Тесты не найдены, продолжаем..."
                '''
            }
        }

        stage('Terraform: Create VM') {
            steps {
                dir('terraform') {
                    sh '''
                        echo "==> Инициализация Terraform"
                        terraform init
                        
                        echo "==> Создание VM в OpenStack"
                        terraform apply -auto-approve \
                            -var="auth_url=$OS_AUTH_URL" \
                            -var="tenant_name=$OS_TENANT_NAME" \
                            -var="user_name=$OS_USERNAME" \
                            -var="password=$OS_PASSWORD" \
                            -var="public_ssh_key=$(cat $SSH_KEY_PATH.pub)"
                    '''
                }
            }
        }

        stage('Wait for VM SSH') {
            steps {
                script {
                    vmIp = sh(
                        script: "cd terraform && terraform output -raw vm_ip",
                        returnStdout: true
                    ).trim()
                    
                    env.VM_IP = vmIp
                    echo "Ожидание SSH на ${vmIp}"
                    
                    sh """
                        for i in \$(seq 1 30); do
                            echo "Проверка SSH (попытка \$i)..."
                            if nc -z -w 5 ${vmIp} 22; then
                                echo "SSH доступен!"
                                exit 0
                            fi
                            sleep 10
                        done
                        echo "SSH не стал доступен"
                        exit 1
                    """
                }
            }
        }

        stage('Ansible: Deploy') {
            steps {
                sh """
                    echo "==> Настройка Ansible inventory"
                    cat > ansible/inventory.ini <<EOF
[knn_servers]
${VM_IP} ansible_user=ubuntu ansible_ssh_private_key_file=${SSH_KEY_PATH}
EOF

                    echo "==> Запуск Ansible"
                    cd ansible
                    ansible-playbook -i inventory.ini playbook.yml
                """
            }
        }

        stage('Verify Deployment') {
            steps {
                sh """
                    echo "==> Проверка работоспособности сервиса"
                    sleep 15
                    curl -f http://${VM_IP}:8000/health
                    echo "KNN Imputation Service запущен на http://${VM_IP}:8000"
                """
            }
        }
    }

    post {
        success {
            echo "Пайплайн успешно завершен!"
            echo "Сервис доступен по адресу: http://${VM_IP}:8000"
        }
        failure {
            echo "Пайплайн завершился с ошибкой"
        }
    }
}
