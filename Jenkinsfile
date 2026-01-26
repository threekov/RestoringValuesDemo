pipeline {
  agent {
    node {
      label 'threekov-node'
    }
  }

  environment {
    NAMESPACE        = "threekov-lab7"
    REGISTRY_ID      = "crpist2uge71cahfb48e"
    APP_NAME         = "knn-vm-lab7"
    IMAGE_TAG        = "${BUILD_NUMBER}"
    IMAGE_FULL       = "cr.yandex/${REGISTRY_ID}/${APP_NAME}:${IMAGE_TAG}"
    IMAGE_LATEST     = "cr.yandex/${REGISTRY_ID}/${APP_NAME}:latest"
    
    YC_PATH = "/home/ubuntu/yandex-cloud/bin"
    PATH = "$YC_PATH:$PATH"
  }

  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
  }

  stages {
    stage('Setup Environment') {
      steps {
        sh '''#!/bin/bash
          echo "=== НАСТРОЙКА ОКРУЖЕНИЯ ==="
          echo "Нода: $(hostname)"
          echo "Пользователь: $(whoami)"
          
          export PATH="/home/ubuntu/yandex-cloud/bin:$PATH"
          
          echo "Проверка инструментов:"
          which python3 || echo "python3 не найден"
          which docker || echo "docker не найден"
          which kubectl || echo "kubectl не найден"
          which yc || echo "yc не найден"
          
          rm -f ~/.docker/config.json 2>/dev/null || true
          echo "Окружение настроено"
        '''
      }
    }

    stage('Checkout') {
      steps { 
        checkout scm 
        sh '''
          echo "Ревизия: $(git rev-parse --short HEAD)"
        '''
      }
    }

    stage('Build Docker') {
      steps {
        sh '''
          echo "=== СБОРКА DOCKER ОБРАЗА ==="
          docker build -t ${IMAGE_FULL} .
          docker tag ${IMAGE_FULL} ${IMAGE_LATEST}
          echo "Образ собран: ${IMAGE_FULL}"
        '''
      }
    }

    stage('Docker Push - Direct Method') {
      steps {
        sh '''#!/bin/bash
          echo "=== ПУШ В YCR (прямой метод) ==="
          
          YC="/home/ubuntu/yandex-cloud/bin/yc"
          echo "Используем yc: $YC"
          
          if [ ! -x "$YC" ]; then
            echo "yc не найден по пути: $YC"
            exit 1
          fi
          
          echo "Найден yc: $YC"
          
          echo "Получаем IAM токен..."
          TOKEN=$($YC iam create-token 2>/dev/null || echo "")
          
          if [ -z "$TOKEN" ]; then
            echo "Не удалось получить токен!"
            exit 1
          fi
          
          echo "Токен получен (длина: ${#TOKEN})"
          
          echo "Аутентификация в Docker..."
          AUTH=$(echo -n "iam:$TOKEN" | base64 -w0)
          mkdir -p ~/.docker
          cat > ~/.docker/config.json << EOF
{
  "auths": {
    "cr.yandex": {
      "auth": "$AUTH"
    }
  },
  "credHelpers": {
    "cr.yandex": ""
  }
}
EOF
          
          echo "Пушим ${IMAGE_FULL}..."
          if docker push ${IMAGE_FULL}; then
            echo "Образ успешно загружен"
          else
            echo "Ошибка при пуше!"
            exit 1
          fi
          
          echo "Пушим latest..."
          docker push ${IMAGE_LATEST} || echo "Не удалось загрузить latest"
          
          echo "Образы загружены в YCR!"
        '''
      }
    }

    stage('Deploy to K8S') {
      steps {
        sh '''
          echo "=== ДЕПЛОЙ В K8S ==="
          echo "Используем образ: ${IMAGE_FULL}"
          
          if ! grep -q "IMAGE_PLACEHOLDER" k8s/deployment.yaml; then
            echo "В deployment.yaml нет IMAGE_PLACEHOLDER!"
            exit 1
          fi
          
          echo "Удаляем старые поды..."
          kubectl delete pods -n ${NAMESPACE} -l app=${APP_NAME} --ignore-not-found=true
          sleep 5
          
          echo "Обновляем deployment..."
          sed -i "s|IMAGE_PLACEHOLDER|${IMAGE_FULL}|g" k8s/deployment.yaml
          
          kubectl apply -f k8s/deployment.yaml -n ${NAMESPACE}
          kubectl apply -f k8s/service.yaml -n ${NAMESPACE}
          
          echo "Ожидаем развертывания..."
          sleep 15
          
          echo "Статус:"
          kubectl get all -n ${NAMESPACE}
          
          echo "Поды:"
          kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o wide
        '''
      }
    }
  }

  post {
    always {
      sh '''
        echo "=== ФИНИШ ==="
        echo "Образ: ${IMAGE_FULL}"
        echo "Поды:"
        kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} 2>/dev/null || echo "Поды не найдены"
      '''
    }
  }
}
