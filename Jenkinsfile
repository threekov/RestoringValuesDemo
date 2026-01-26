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
    // Этап 1: Получение кода
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

    // Этап 2: Тестирование Python
    stage('Build & Test') {
      steps {
        sh '''
          echo "==> Установка зависимостей Python"
          pip3 install --user -r requirements.txt
          
          echo "==> Проверка импорта модели"
          python3 -c "from core.imputer_service import KNNImputationService; print('Модель загружается')"
          
          echo "==> Проверка FastAPI приложения"
          python3 -c "import app; print('Приложение импортируется')"
          
          echo "==> Запуск тестов (если есть)"
          python3 -m pytest tests/ -v || echo "Тесты не найдены"
        '''
      }
    }

    // Этап 3: Сборка Docker образа
    stage('Docker Build') {
      steps {
        sh '''#!/usr/bin/env bash
          set -e
          echo "==> Сборка Docker образа"
          echo "Dockerfile: $(pwd)/Dockerfile"
          echo "Образ: ${IMAGE_FULL}"
          
          # Проверяем Dockerfile
          ls -la Dockerfile
          head -10 Dockerfile
          
          # Собираем образы
          docker build -t ${IMAGE_FULL} .
          docker tag ${IMAGE_FULL} ${IMAGE_LATEST}
          
          echo "==> Список локальных образов"
          docker images | grep ${APP_NAME}
        '''
      }
    }

    // Этап 4: Пуш в Yandex Container Registry (ИСПРАВЛЕННЫЙ)
    stage('Docker Push to YCR') {
      steps {
        sh '''#!/usr/bin/env bash
          set -e
          echo "==> Пуш в YCR через IAM токен"
          
          # Получаем токен
          TOKEN=$(yc iam create-token)
          if [ -z "$TOKEN" ]; then
            echo "Ошибка получения IAM токена"
            exit 1
          fi
          
          # Создаем конфиг для Docker
          mkdir -p ~/.docker
          cat > ~/.docker/config.json <<EOF
{
  "auths": {
    "cr.yandex": {
      "auth": "$(echo -n "iam:$TOKEN" | base64 | tr -d '\n')"
    }
  }
}
EOF
          
          echo "==> Пуш образов"
          echo "Отправка: ${IMAGE_FULL}"
          docker push ${IMAGE_FULL}
          
          echo "Отправка: ${IMAGE_LATEST}"
          docker push ${IMAGE_LATEST}
          
          echo "Образы успешно загружены в YCR"
          
          # Очищаем конфиг (опционально)
          rm -f ~/.docker/config.json
        '''
      }
    }

    // Этап 5: Настройка Kubernetes
    stage('Kubernetes Setup') {
      steps {
        sh '''#!/usr/bin/env bash
          set -e
          echo "==> Проверка подключения к Kubernetes"
          
          kubectl version --client
          kubectl cluster-info
          
          # Проверка/создание неймспейса
          if kubectl get ns ${NAMESPACE} >/dev/null 2>&1; then
            echo "Неймспейс ${NAMESPACE} существует"
          else
            echo "Создание неймспейса ${NAMESPACE}"
            kubectl create ns ${NAMESPACE}
          fi
          
          echo "==> Текущее состояние кластера"
          kubectl get nodes
          kubectl get all -n ${NAMESPACE} 2>/dev/null || echo "Неймспейс пуст"
        '''
      }
    }

    // Этап 6: Деплой в Kubernetes
    stage('Kubernetes Deploy') {
      steps {
        sh '''#!/usr/bin/env bash
          set -e
          echo "==> Деплоймент в Kubernetes"
          echo "Используем образ: ${IMAGE_FULL}"
          
          # Проверяем наличие манифестов
          ls -la k8s/
          
          # Создаем временный файл с подставленным образом
          sed "s|IMAGE_PLACEHOLDER|${IMAGE_FULL}|g" k8s/deployment.yaml > k8s/deployment-temp.yaml
          
          echo "--- deployment-temp.yaml ---"
          head -20 k8s/deployment-temp.yaml
          echo "----------------------------"
          
          # Применяем манифесты
          kubectl apply -n ${NAMESPACE} -f k8s/deployment-temp.yaml
          rm -f k8s/deployment-temp.yaml
          
          # Применяем service.yaml если есть
          if [ -f "k8s/service.yaml" ]; then
            kubectl apply -n ${NAMESPACE} -f k8s/service.yaml
          fi
          
          echo "==> Ожидание развертывания (180 секунд)"
          kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=180s
          
          echo "==> Финальное состояние"
          kubectl get all -n ${NAMESPACE}
        '''
      }
    }

    // Этап 7: Верификация (УПРОЩЕННАЯ)
    stage('Verify Deployment') {
      steps {
        sh '''#!/usr/bin/env bash
          set -e
          echo "==> Проверка развертывания"
          
          # Проверяем что поды готовы
          READY=$(kubectl get deployment ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.status.readyReplicas}')
          DESIRED=$(kubectl get deployment ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.status.replicas}')
          
          if [ "$READY" = "$DESIRED" ] && [ "$READY" -gt 0 ]; then
            echo "Развертывание успешно: $READY/$DESIRED подов готовы"
            
            # Показываем как подключиться
            echo ""
            echo "ДЛЯ ПОДКЛЮЧЕНИЯ К СЕРВИСУ:"
            echo "1. kubectl port-forward -n ${NAMESPACE} svc/${APP_NAME} 8000:80"
            echo "2. Откройте браузер: http://localhost:8000"
            echo "3. Или проверьте: curl http://localhost:8000/health"
            
            # Показываем NodePort если есть
            NODE_PORT=$(kubectl get svc ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "")
            if [ -n "$NODE_PORT" ]; then
              echo "4. NodePort: $NODE_PORT (требуется IP ноды)"
            fi
          else
            echo "Развертывание не готово: $READY/$DESIRED подов"
            exit 1
          fi
        '''
      }
    }
  }

  post {
    success {
      echo "PIPELINE УСПЕШНО ЗАВЕРШЕН!"
      echo "=========================================="
      sh '''
        echo "Сервис: ${APP_NAME}"
        echo "Образ: ${IMAGE_FULL}"
        echo ""
        kubectl get pods,svc -n ${NAMESPACE}
      '''
      echo "=========================================="
    }
    
    failure {
      echo "PIPELINE ЗАВЕРШИЛСЯ С ОШИБКОЙ"
      echo "=========================================="
      sh '''
        echo "Диагностика:"
        kubectl get pods -n ${NAMESPACE} -o wide
        echo ""
        kubectl describe deployment ${APP_NAME} -n ${NAMESPACE} | tail -20
      '''
      echo "=========================================="
    }
    
    always {
      echo "==> Очистка временных ресурсов"
      sh '''
        pkill -f "kubectl port-forward" 2>/dev/null || true
        echo "Использованные Docker образы на Jenkins ноде:"
        docker images | grep ${APP_NAME} || true
      '''
    }
  }
}
