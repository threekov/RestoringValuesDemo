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
    
    // Явно добавляем путь к yc
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
          
          # Проверяем и настраиваем PATH
          echo "Текущий PATH: $PATH"
          echo "Добавляем yc в PATH..."
          export PATH="/home/ubuntu/yandex-cloud/bin:$PATH"
          echo "Новый PATH: $PATH"
          
          # Проверяем инструменты
          echo "Проверка инструментов:"
          which python3 || echo "python3 не найден"
          which docker || echo "docker не найден"
          which kubectl || echo "kubectl не найден"
          which yc || echo "yc не найден"
          
          # Если yc не найден, ищем его
          if ! command -v yc &> /dev/null; then
            echo "Ищем yc..."
            if [ -f "/home/ubuntu/yandex-cloud/bin/yc" ]; then
              echo "yc найден по пути: /home/ubuntu/yandex-cloud/bin/yc"
              export PATH="/home/ubuntu/yandex-cloud/bin:$PATH"
            elif [ -f "$HOME/yandex-cloud/bin/yc" ]; then
              echo "yc найден по пути: $HOME/yandex-cloud/bin/yc"
              export PATH="$HOME/yandex-cloud/bin:$PATH"
            else
              echo "yc не найден, устанавливаем..."
              curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
              export PATH="$HOME/yandex-cloud/bin:$PATH"
            fi
          fi
          
          echo "Версия yc: $(yc --version 2>/dev/null || echo 'не найден')"
          
          # Фиксим docker config
          rm -f ~/.docker/config.json 2>/dev/null || true
          echo "✅ Окружение настроено"
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
          echo "✅ Образ собран: ${IMAGE_FULL}"
        '''
      }
    }

    stage('Docker Push - Direct Method') {
      steps {
        sh '''#!/bin/bash
          echo "=== ПУШ В YCR (прямой метод) ==="
          
          # Явный путь к yc
          YC="/home/ubuntu/yandex-cloud/bin/yc"
          echo "Используем yc: $YC"
          
          if [ ! -x "$YC" ]; then
            echo "❌ yc не найден по пути: $YC"
            echo "Ищем в системе..."
            YC=$(find /home -name yc -type f -executable 2>/dev/null | head -1)
            if [ -z "$YC" ]; then
              echo "Устанавливаем yc..."
              curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
              YC="$HOME/yandex-cloud/bin/yc"
            fi
          fi
          
          echo "Найден yc: $YC"
          
          # Получаем токен
          echo "Получаем IAM токен..."
          TOKEN=$($YC iam create-token 2>/dev/null || echo "")
          
          if [ -z "$TOKEN" ]; then
            echo "❌ Не удалось получить токен!"
            echo "Проверь конфигурацию yc:"
            $YC config list 2>/dev/null || echo "Не удалось получить конфигурацию"
            exit 1
          fi
          
          echo "Токен получен (длина: ${#TOKEN})"
          
          # Прямая аутентификация в Docker
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
          
          echo "Проверяем аутентификацию..."
          if docker login cr.yandex --username iam --password-stdin <<< "$TOKEN" 2>&1 | grep -q "Login Succeeded"; then
            echo "✅ Docker аутентификация успешна"
          else
            echo "⚠️ Docker login не прошел, используем ручную аутентификацию"
          fi
          
          # Пушим образ
          echo "Пушим ${IMAGE_FULL}..."
          if docker push ${IMAGE_FULL}; then
            echo "✅ Образ успешно загружен"
          else
            echo "❌ Ошибка при пуше!"
            echo "Проверяем docker config:"
            cat ~/.docker/config.json 2>/dev/null || echo "Нет config"
            echo "Пробуем альтернативный метод..."
            
            # Альтернатива: используем docker-credential-yc напрямую
            if [ -f "/home/ubuntu/yandex-cloud/bin/docker-credential-yc" ]; then
              echo "Используем docker-credential-yc..."
              cat > ~/.docker/config.json << EOF
{
  "auths": {},
  "credHelpers": {
    "cr.yandex": "yc"
  },
  "credsStore": "yc"
}
EOF
              docker push ${IMAGE_FULL} || {
                echo "❌ Ошибка после всех попыток"
                exit 1
              }
            else
              echo "❌ docker-credential-yc не найден"
              exit 1
            fi
          fi
          
          # Пушим latest
          echo "Пушим latest..."
          docker push ${IMAGE_LATEST} || echo "⚠️ Не удалось загрузить latest"
          
          echo "✅ Образы загружены в YCR!"
        '''
      }
    }

    stage('Deploy to K8S') {
      steps {
        sh '''
          echo "=== ДЕПЛОЙ В K8S ==="
          echo "Используем образ: ${IMAGE_FULL}"
          
          # Проверяем deployment.yaml
          if ! grep -q "IMAGE_PLACEHOLDER" k8s/deployment.yaml; then
            echo "❌ В deployment.yaml нет IMAGE_PLACEHOLDER!"
            echo "Содержимое deployment.yaml:"
            head -20 k8s/deployment.yaml
            exit 1
          fi
          
          # Удаляем старые поды
          echo "Удаляем старые поды..."
          kubectl delete pods -n ${NAMESPACE} -l app=${APP_NAME} --ignore-not-found=true
          sleep 5
          
          # Обновляем deployment
          echo "Обновляем deployment..."
          sed -i "s|IMAGE_PLACEHOLDER|${IMAGE_FULL}|g" k8s/deployment.yaml
          
          # Применяем
          kubectl apply -f k8s/deployment.yaml -n ${NAMESPACE}
          kubectl apply -f k8s/service.yaml -n ${NAMESPACE}
          
          # Ждем
          echo "Ожидаем развертывания..."
          sleep 15
          
          echo "Статус:"
          kubectl get all -n ${NAMESPACE}
          
          echo "Поды:"
          kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o wide
          
          # Проверяем ошибки
          echo "Проверяем ошибки:"
          kubectl describe pods -n ${NAMESPACE} -l app=${APP_NAME} | grep -A5 -B5 "Error\|Failed\|BackOff" || echo "Ошибок не найдено"
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
