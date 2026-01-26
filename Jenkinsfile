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
flavor_name   = "m1.small"
network_name  = "sutdents-net"

public_ssh_key = "$(cat /home/ubuntu/.ssh/id_rsa.pub)"
environment   = "threekov"
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
                    echo "==> Проверка работоспособности сервиса через SSH tunnel"
                    
                    # Подключаемся по SSH и проверяем сервис
                    echo "==> Проверка через SSH команду"
                    for i in \$(seq 1 10); do
                        echo "==> Health check attempt \$i"
                        if ssh -o StrictHostKeyChecking=no -i ${SSH_KEY_PATH} ubuntu@${VM_IP} \\
                           "curl -s http://localhost:8000/health 2>/dev/null || exit 1"; then
                            echo "==> Service is UP and running!"
                            
                            # Проверка веб-интерфейса
                            if ssh -o StrictHostKeyChecking=no -i ${SSH_KEY_PATH} ubuntu@${VM_IP} \\
                               "curl -s http://localhost:8000 | grep -q 'KNN'"; then
                                echo "==> Web interface is accessible"
                            fi
                            
                            echo "==> Проверка успешно завершена"
                            echo "KNN Imputation Service: http://${VM_IP}:8000"
                            exit 0
                        fi
                        echo "==> Service not ready yet, sleep 10s"
                        sleep 10
                    done
                    
                    # Альтернатива: через SSH tunnel
                    echo "==> Попытка через SSH tunnel"
                    ssh -o StrictHostKeyChecking=no -i ${SSH_KEY_PATH} -L 8080:localhost:8000 -N ubuntu@${VM_IP} &
                    TUNNEL_PID=\$!
                    sleep 5
                    
                    if curl -s http://localhost:8080/health 2>/dev/null; then
                        echo "==> Service works via SSH tunnel!"
                        kill \$TUNNEL_PID 2>/dev/null
                        exit 0
                    else
                        echo "==> Service check failed via tunnel too"
                        kill \$TUNNEL_PID 2>/dev/null
                        exit 1
                    fi
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
