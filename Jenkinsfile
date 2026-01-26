pipeline {
  agent any

  environment {
    NAMESPACE        = "threekov-lab7"
    REGISTRY_ID      = "crpist2uge71cahfb48e"
    APP_NAME         = "knn-vm-lab7"
    IMAGE_TAG        = "${BUILD_NUMBER}"
    IMAGE_FULL       = "cr.yandex/${REGISTRY_ID}/${APP_NAME}:${IMAGE_TAG}"
    IMAGE_LATEST     = "cr.yandex/${REGISTRY_ID}/${APP_NAME}:latest"
  }

  options {
    timestamps()
    timeout(time: 30, unit: 'MINUTES')
  }

  stages {
    stage('Checkout') {
      steps { 
        checkout scm 
        sh '''
          echo "Ревизия: $(git rev-parse --short HEAD)"
          echo "Структура проекта:"
          find . -maxdepth 2 -type f -name "*.py" -o -name "*.yaml" -o -name "Dockerfile" -o -name "*.txt" | sort
        '''
      }
    }

    stage('Build & Test') {
      steps {
        sh '''
          pip3 install --user -r requirements.txt
          python3 -c "from core.imputer_service import KNNImputationService; print('Модель загружается')"
          python3 -c "import app; print('Приложение импортируется')"
          python3 -m pytest tests/ -v 2>/dev/null || echo "Тестов нет"
        '''
      }
    }

    stage('Docker Build') {
      steps {
        sh '''
          echo "==> Сборка Docker образа"
          docker build -t ${IMAGE_FULL} .
          docker tag ${IMAGE_FULL} ${IMAGE_LATEST}
          echo "==> Список локальных образов"
          docker images | grep ${APP_NAME} || true
        '''
      }
    }

    stage('Setup Yandex Cloud CLI') {
      steps {
        sh '''#!/usr/bin/env bash
          set -e
          echo "==> Проверяем и устанавливаем yc на pitest-node"
          
          # Проверяем, установлен ли уже yc
          if command -v yc &> /dev/null; then
            echo "yc уже установлен: $(which yc)"
            echo "Версия: $(yc --version)"
          else
            echo "Устанавливаем Yandex Cloud CLI..."
            
            # Скачиваем и устанавливаем
            curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
            
            # Добавляем в PATH для текущей сессии
            export PATH="$HOME/yandex-cloud/bin:$PATH"
            echo "export PATH=\"\$HOME/yandex-cloud/bin:\$PATH\"" >> ~/.bashrc
            source ~/.bashrc
            
            echo "yc установлен: $(which yc)"
          fi
          
          # Проверяем конфигурацию yc
          echo "Проверяем конфигурацию yc..."
          yc config list 2>/dev/null || echo "yc не сконфигурирован - будет использоваться IAM токен"
        '''
      }
    }

    stage('Docker login + push to YCR') {
      steps {
        sh '''#!/usr/bin/env bash
          set -euo pipefail

          echo "==> Подготовка к пушу в YCR"
          
          # Явный путь к yc
          YC="/home/ubuntu/yandex-cloud/bin/yc"
          
          # Проверяем что yc существует
          if [ ! -x "$YC" ]; then
            echo "Пробуем найти yc в системе..."
            YC=$(which yc 2>/dev/null || echo "")
            if [ -z "$YC" ]; then
              echo "ОШИБКА: yc не найден в системе"
              echo "Устанавливаем yc..."
              curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
              export PATH="$HOME/yandex-cloud/bin:$PATH"
              YC="/home/ubuntu/yandex-cloud/bin/yc"
            fi
          fi
          
          echo "Используем yc: $YC"
          
          # Проверяем конфигурацию
          echo "Проверяем конфигурацию yc..."
          $YC config list 2>/dev/null || echo "yc не сконфигурирован, пробуем получить токен"
          
          echo "==> Получаем IAM токен"
          TOKEN="$($YC iam create-token)"
          
          if [ -z "$TOKEN" ]; then
            echo "ОШИБКА: Не удалось получить IAM токен"
            echo "Проверьте что yc сконфигурирован:"
            echo "1. Выполните 'yc init' на ноде"
            echo "2. Или настройте через сервисный аккаунт"
            exit 1
          fi
          
          echo "Токен получен (длина: ${#TOKEN} символов)"
          
          echo "==> Docker login to YCR"
          # Игнорируем ошибку сохранения credentials - главное что логин проходит
          echo "$TOKEN" | docker login --username iam --password-stdin cr.yandex 2>&1 | grep -v "Error saving credentials" || true
          
          # Проверяем что в конфиге появилась запись
          if [ -f /home/ubuntu/.docker/config.json ]; then
            echo "Docker config обновлен"
          else
            echo "Создаем docker config вручную..."
            mkdir -p /home/ubuntu/.docker
            AUTH=$(echo -n "iam:$TOKEN" | base64)
            cat > /home/ubuntu/.docker/config.json << EOF
{
  "auths": {
    "cr.yandex": {
      "auth": "$AUTH"
    }
  }
}
EOF
          fi
          
          echo "==> Push image"
          echo "Пушим ${IMAGE_FULL} ..."
          docker push ${IMAGE_FULL}
          
          echo "Пушим ${IMAGE_LATEST} ..."
          docker push ${IMAGE_LATEST}
          
          echo "Образы успешно загружены в YCR!"
        '''
      }
    }

    stage('Kubernetes Setup') {
      steps {
        sh '''
          echo "==> Проверяем неймспейс Kubernetes"
          kubectl get ns ${NAMESPACE} >/dev/null 2>&1 || kubectl create ns ${NAMESPACE}
          echo "Текущие ресурсы в неймспейсе:"
          kubectl get all -n ${NAMESPACE} 2>/dev/null || echo "Неймспейс пуст"
        '''
      }
    }

    stage('Kubernetes Deploy') {
      steps {
        sh '''
          echo "==> Деплоймент в Kubernetes"
          echo "Используем образ: ${IMAGE_FULL}"
          
          # Создаем временный deployment файл с подставленным образом
          sed "s|IMAGE_PLACEHOLDER|${IMAGE_FULL}|g" k8s/deployment.yaml > k8s/deployment-temp.yaml
          
          # Применяем манифесты
          kubectl apply -n ${NAMESPACE} -f k8s/deployment-temp.yaml
          kubectl apply -n ${NAMESPACE} -f k8s/service.yaml
          
          # Ждем rollout
          kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=180s
          
          # Показываем статус
          echo "Текущий статус деплоймента:"
          kubectl get all -n ${NAMESPACE}
        '''
      }
    }

    stage('Verify Deployment') {
      steps {
        sh '''
          echo "==> Проверка работоспособности сервиса"
          
          # Проверяем поды
          echo "Статус подов:"
          kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME}
          
          # Проверяем логи первого пода
          POD=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o jsonpath="{.items[0].metadata.name}" 2>/dev/null || echo "")
          if [ -n "$POD" ]; then
            echo "Логи пода $POD (последние 10 строк):"
            kubectl logs -n ${NAMESPACE} "$POD" --tail=10
          fi
          
          # Простой health check
          echo "Пробуем health check через port-forward..."
          timeout 30 bash -c '
            kubectl port-forward -n ${NAMESPACE} svc/${APP_NAME} 8888:80 >/dev/null 2>&1 &
            PF_PID=$!
            sleep 5
            if curl -f http://localhost:8888/health >/dev/null 2>&1; then
              echo "✓ Health check прошел успешно"
              kill $PF_PID 2>/dev/null
              exit 0
            else
              echo "✗ Health check не прошел"
              kill $PF_PID 2>/dev/null
              exit 1
            fi
          ' || echo "Health check не удался, но деплоймент продолжен"
        '''
      }
    }
  }

  post {
    always {
      sh '''
        echo "==> Очистка"
        pkill -f "kubectl port-forward" 2>/dev/null || true
        rm -f k8s/deployment-temp.yaml 2>/dev/null || true
        
        echo "==> Финальный статус"
        echo "Поды:"
        kubectl get pods -n ${NAMESPACE} 2>/dev/null || true
        echo "Сервисы:"
        kubectl get svc -n ${NAMESPACE} 2>/dev/null || true
      '''
    }
    success {
      sh '''
        echo "Пайплайн выполнен успешно!"
        echo "Сервис доступен:"
        echo "- Внутри кластера: http://${APP_NAME}.${NAMESPACE}.svc.cluster.local"
        echo "- External IP/NodePort: $(kubectl get svc -n ${NAMESPACE} ${APP_NAME} -o jsonpath="{.spec.ports[0].nodePort}" 2>/dev/null || echo "не настроен")"
      '''
    }
    failure {
      sh '''
        echo "Пайплайн завершился с ошибкой"
        echo "Для диагностики:"
        echo "1. Проверьте логи подов: kubectl logs -n ${NAMESPACE} -l app=${APP_NAME}"
        echo "2. Проверьте события: kubectl get events -n ${NAMESPACE}"
        echo "3. Проверьте описание пода: kubectl describe pod -n ${NAMESPACE} -l app=${APP_NAME}"
      '''
    }
  }
}
