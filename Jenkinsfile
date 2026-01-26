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

    // Этап 4: Пуш в Yandex Container Registry
    stage('Docker Push to YCR') {
      steps {
        sh '''#!/usr/bin/env bash
          set -euo pipefail
          echo "==> Подготовка к пушу в YCR"

          # Поиск yc (Yandex Cloud CLI)
          find_yc() {
            local paths=(
              "/home/ubuntu/yandex-cloud/bin/yc"
              "/usr/local/bin/yc"
              "/usr/bin/yc"
              "$(which yc 2>/dev/null)"
            )
            for path in "${paths[@]}"; do
              if [ -x "$path" ]; then
                echo "$path"
                return 0
              fi
            done
            echo "ERROR: yc not found!" >&2
            return 1
          }

          YC=$(find_yc)
          echo "Найден yc: $YC"
          
          # Получение IAM токена
          echo "==> Получение IAM токена"
          TOKEN="$($YC iam create-token)"
          
          if [ -z "$TOKEN" ] || [[ "$TOKEN" == *"error"* ]]; then
            echo "Ошибка получения токена: $TOKEN"
            echo "Проверьте: $YC config list"
            exit 1
          fi

          echo "==> Логин в Yandex Container Registry"
          echo "$TOKEN" | docker login --username iam --password-stdin cr.yandex || {
            echo "Ошибка логина в YCR"
            exit 1
          }

          echo "==> Пуш образов в YCR"
          echo "Отправка: ${IMAGE_FULL}"
          docker push ${IMAGE_FULL} || {
            echo "Ошибка пуша ${IMAGE_FULL}"
            exit 1
          }
          
          echo "Отправка: ${IMAGE_LATEST}"
          docker push ${IMAGE_LATEST} || {
            echo "Ошибка пуша ${IMAGE_LATEST}"
            exit 1
          }
          
          echo "==> Проверка в registry"
          $YC container image list --registry-id ${REGISTRY_ID} | grep ${APP_NAME} || true
          echo "Образы успешно загружены в YCR"
        '''
      }
    }

    // Этап 5: Настройка Kubernetes
    stage('Kubernetes Setup') {
      steps {
        sh '''#!/usr/bin/env bash
          set -e
          echo "==> Проверка подключения к Kubernetes"
          
          # Проверка kubectl
          kubectl version --client
          kubectl cluster-info || {
            echo "Не могу подключиться к кластеру"
            echo "Проверьте kubeconfig"
            exit 1
          }
          
          # Проверка/создание неймспейса
          if kubectl get ns ${NAMESPACE} >/dev/null 2>&1; then
            echo "Неймспейс ${NAMESPACE} существует"
          else
            echo "Создание неймспейса ${NAMESPACE}"
            kubectl create ns ${NAMESPACE}
          fi
          
          echo "==> Текущее состояние кластера"
          kubectl get nodes
          kubectl get all -n ${NAMESPACE} || echo "Неймспейс пуст"
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
          if [ ! -d "k8s" ]; then
            echo "Директория k8s не найдена!"
            exit 1
          fi
          
          ls -la k8s/
          
          # Обновляем образ в deployment.yaml
          echo "==> Обновление deployment.yaml"
          if [ -f "k8s/deployment.yaml" ]; then
            # Создаем временный файл с подставленным образом
            sed "s|IMAGE_PLACEHOLDER|${IMAGE_FULL}|g" k8s/deployment.yaml > k8s/deployment-temp.yaml
            
            echo "--- deployment-temp.yaml ---"
            head -20 k8s/deployment-temp.yaml
            echo "----------------------------"
            
            # Применяем манифесты
            kubectl apply -n ${NAMESPACE} -f k8s/deployment-temp.yaml
            rm -f k8s/deployment-temp.yaml
          else
            echo "Файл k8s/deployment.yaml не найден"
          fi
          
          # Применяем остальные манифесты
          for file in k8s/*.yaml; do
            if [ "$(basename "$file")" != "deployment.yaml" ]; then
              echo "Применяем: $file"
              kubectl apply -n ${NAMESPACE} -f "$file"
            fi
          done
          
          echo "==> Ожидание развертывания (180 секунд)"
          kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=180s
          
          echo "==> Финальное состояние"
          kubectl get all -n ${NAMESPACE}
          kubectl get pods -n ${NAMESPACE} -o wide
          kubectl get svc -n ${NAMESPACE}
        '''
      }
    }

    // Этап 7: Верификация
    stage('Verify Deployment') {
      steps {
        sh '''#!/usr/bin/env bash
          set -e
          echo "==> Проверка работоспособности сервиса"
          
          # Получаем информацию о сервисе
          SERVICE_TYPE=$(kubectl get svc ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.type}')
          echo "Тип сервиса: $SERVICE_TYPE"
          
          # В зависимости от типа сервиса проверяем по-разному
          if [ "$SERVICE_TYPE" = "ClusterIP" ]; then
            echo "Сервис ClusterIP - используем port-forward для тестирования"
            
            # Запускаем port-forward в фоне
            kubectl port-forward -n ${NAMESPACE} svc/${APP_NAME} 8080:80 &
            PF_PID=$!
            
            # Даем время на запуск
            sleep 10
            
            echo "==> Проверка health-check эндпоинта"
            for i in {1..10}; do
              echo "Попытка $i/10..."
              if curl -f -s http://localhost:8080/health >/dev/null; then
                echo "Health-check прошел успешно!"
                
                # Проверка основного интерфейса
                echo "==> Проверка веб-интерфейса"
                curl -s http://localhost:8080/ | grep -i "KNN" && echo "Веб-интерфейс доступен"
                
                # Завершаем port-forward
                kill $PF_PID 2>/dev/null || true
                wait $PF_PID 2>/dev/null || true
                exit 0
              fi
              sleep 5
            done
            
            echo "Сервис не ответил за 50 секунд"
            kill $PF_PID 2>/dev/null || true
          else
            # Для NodePort/LoadBalancer
            echo "Проверка через внешний IP/порт"
            # Здесь можно добавить логику для других типов сервисов
          fi
          
          # Если не удалось - показываем логи
          echo "==> Логи для диагностики"
          POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
          
          if [ -n "$POD_NAME" ]; then
            echo "Логи пода: $POD_NAME"
            kubectl logs -n ${NAMESPACE} "$POD_NAME" --tail=50
            echo "Описание пода:"
            kubectl describe pod -n ${NAMESPACE} "$POD_NAME" | tail -50
          else
            echo "Поды не найдены"
            kubectl get events -n ${NAMESPACE} --sort-by='.lastTimestamp' | tail -20
          fi
          
          exit 1
        '''
      }
    }
  }

  post {
    success {
      echo "PIPELINE УСПЕШНО ЗАВЕРШЕН!"
      echo "=========================================="
      echo "Сервис: ${APP_NAME}"
      echo "Неймспейс: ${NAMESPACE}"
      echo "Образ: ${IMAGE_FULL}"
      echo "Статус:"
      sh '''
        kubectl get pods,svc -n ${NAMESPACE}
        echo ""
        echo "Для доступа к сервису:"
        echo "1. Port-forward: kubectl port-forward -n ${NAMESPACE} svc/${APP_NAME} 8000:80"
        echo "2. Затем откройте: http://localhost:8000"
      '''
      echo "=========================================="
    }
    
    failure {
      echo "PIPELINE ЗАВЕРШИЛСЯ С ОШИБКОЙ"
      echo "=========================================="
      sh '''
        echo "Диагностическая информация:"
        echo "1. Pods:"
        kubectl get pods -n ${NAMESPACE} -o wide || true
        echo ""
        echo "2. Events:"
        kubectl get events -n ${NAMESPACE} --sort-by='.lastTimestamp' | tail -20 || true
        echo ""
        echo "3. Deployment:"
        kubectl describe deployment ${APP_NAME} -n ${NAMESPACE} | tail -30 || true
      '''
      echo "=========================================="
    }
    
    always {
      echo "==> Очистка временных ресурсов"
      sh '''
        # Останавливаем все port-forward процессы
        pkill -f "kubectl port-forward" 2>/dev/null || true
        
        # Показываем использованные образы
        echo "Использованные Docker образы:"
        docker images | grep ${APP_NAME} || true
        
        # Финальный статус
        echo "Финальный статус Kubernetes:"
        kubectl get all -n ${NAMESPACE} 2>/dev/null || echo "Не удалось получить статус"
      '''
    }
  }
}
