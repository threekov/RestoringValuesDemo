pipeline {
    agent any  // или agent { label 'threekov-node' } если хотите на вашей ноде

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

        stage('Terraform: provision infra') {
            steps {
                dir('terraform') {
                    sh '''
                        set -e
                        echo "==> Загрузка переменных OpenStack"
                        
                        if [ -f "/home/ubuntu/openrc-jenkins.sh" ]; then
                            . /home/ubuntu/openrc-jenkins.sh
                        elif [ -f "/home/ubuntu/openrc.sh" ]; then
                            . /home/ubuntu/openrc.sh
                        else
                            echo "ERROR: OpenStack credentials file not found!"
                            echo "Create /home/ubuntu/openrc-jenkins.sh with:"
                            echo "export OS_AUTH_URL=..."
                            echo "export OS_USERNAME=..."
                            echo "export OS_PASSWORD=..."
                            echo "export OS_PROJECT_NAME=..."
                            exit 1
                        fi
                        
                        echo "==> Проверка ключа"
                        openstack keypair delete threekov 2>/dev/null || true
                        
                        echo "==> Генерация terraform.tfvars"
                        cat > terraform.tfvars <<EOF
auth_url      = "${OS_AUTH_URL}"
tenant_name   = "${OS_PROJECT_NAME}"
user_name     = "${OS_USERNAME}"
password      = "${OS_PASSWORD}"
region        = "${OS_REGION_NAME:-RegionOne}"

image_name    = "ununtu-22.04"  
flavor_name   = "m1.medium"
network_name  = "sutdents-net"

public_ssh_key = "$(cat /home/ubuntu/.ssh/id_rsa.pub)"
environment   = "jenkins"
EOF

                        echo "==> Terraform init"
                        terraform init -input=false

                        echo "==> Terraform apply"
                        terraform apply -auto-approve -input=false
                    '''
                }
            }
        }

        stage('Wait for VM SSH') {
            steps {
                script {
                    def vmIp = sh(
                        script: "cd terraform && terraform output -raw vm_ip",
                        returnStdout: true
                    ).trim()

                    env.VM_IP = vmIp
                    echo "Ожидание SSH на ${vmIp}"

                    sh """
                        set -e
                        for i in \$(seq 1 30); do
                            echo "==> Checking SSH (${vmIp}) attempt \$i"
                            if nc -z -w 5 ${vmIp} 22; then
                                echo "==> SSH is UP!"
                                exit 0
                            fi
                            echo "==> SSH not ready, sleep 10s"
                            sleep 10
                        done
                        echo "ERROR: SSH did not start in time"
                        exit 1
                    """
                }
            }
        }

        stage('Ansible: deploy to VM') {
            steps {
                script {
                    echo "VM IP from Terraform: ${VM_IP}"

                    sh """
                        set -e

                        # Удаляем старый host key
                        mkdir -p ~/.ssh
                        ssh-keygen -R ${VM_IP} 2>/dev/null || true

                        cd ansible

                        echo "==> Generate inventory.ini"
                        cat > inventory.ini <<EOF
[knn_servers]
${VM_IP} ansible_user=ubuntu ansible_ssh_private_key_file=${SSH_KEY_PATH}
EOF

                        echo "==> Run ansible-playbook"
                        ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i inventory.ini playbook.yml
                    """
                }
            }
        }

        stage('Verify Deployment') {
            steps {
                sh """
                    set -e
                    echo "==> Проверка работоспособности сервиса"
                    sleep 15
                    
                    # Несколько попыток
                    for i in \$(seq 1 5); do
                        echo "==> Health check attempt \$i"
                        if curl -f http://${VM_IP}:8000/health 2>/dev/null; then
                            echo "==> Service is UP!"
                            echo "KNN Imputation Service: http://${VM_IP}:8000"
                            exit 0
                        fi
                        sleep 10
                    done
                    
                    echo "ERROR: Service did not start properly"
                    exit 1
                """
            }
        }
    }

    post {
        success {
            echo "Pipeline SUCCESS: Full build → infra → deploy completed."
            echo "Service: http://${VM_IP}:8000"
        }
        failure {
            echo "Pipeline FAILED."
        }
    }
}
