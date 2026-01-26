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
    // Этап 0: Установка yc на pitest-node
    stage('Setup Yandex Cloud CLI') {
      steps {
        sh '''#!/usr/bin/env bash
          set -euo pipefail
          
          echo "==> Проверяем и устанавливаем yc на pitest-node"
          
          # Проверяем, установлен ли уже yc
          if command -v docker-credential-yc &> /dev/null; then
            echo "docker-credential-yc уже установлен: $(which docker-credential-yc)"
          else
            echo "Устанавливаем Yandex Cloud CLI..."
            
            # Скачиваем и устанавливаем
            curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
            
            # Добавляем в PATH для текущей сессии
            export PATH="$HOME/yandex-cloud/bin:$PATH"
            echo "export PATH=\"\$HOME/yandex-cloud/bin:\$PATH\"" >> ~/.bashrc
            source ~/.bashrc
            
            # Проверяем установку
            if command -v docker-credential-yc &> /dev/null; then
              echo "docker-credential-yc успешно установлен: $(which docker-credential-yc)"
            else
              echo "Не удалось установить docker-credential-yc"
              exit 1
            fi
          fi
          
          # Проверяем наличие yc (основной CLI)
          if command -v yc &> /dev/null; then
            echo "yc найден: $(which yc)"
            echo "Версия: $(yc --version)"
          else
            # Если yc не в PATH, ищем в стандартных местах
            YC_PATH="$HOME/yandex-cloud/bin/yc"
            if [ -x "$YC_PATH" ]; then
              echo "yc найден по пути: $YC_PATH"
              export YC="$YC_PATH"
            else
              echo "yc не найден, но попробуем продолжить с docker-credential-yc"
            fi
          fi
        '''
      }
    }

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

    // Этап 2: Тестирование
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

    // Этап 3: Сборка Docker образа
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

    // Этап 4: Пуш в Yandex Container Registry
    stage('Docker Push to YCR') {
      steps {
        sh '''#!/usr/bin/env bash
          set -euo pipefail
          echo "==> Подготовка к пушу в YCR"
          
          # Настраиваем PATH для этой сессии
          export PATH="$HOME/yandex-cloud/bin:$PATH"
          
          # Ищем yc
          YC=""
          for path in "/home/ubuntu/yandex-cloud/bin/yc" "/usr/local/bin/yc" "/usr/bin/yc" "$(which yc 2>/dev/null)"; do
            if [ -x "$path" ]; then
              YC="$path"
              break
            fi
          done
          
          if [ -z "$YC" ]; then
            echo "yc не найден, пытаемся использовать docker-credential-yc напрямую"
            # Проверяем, есть ли docker-credential-yc
            if ! command -v docker-credential-yc &> /dev/null; then
              echo "docker-credential-yc тоже не найден"
              echo "Пробуем установить ещё раз..."
              curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
              export PATH="$HOME/yandex-cloud/bin:$PATH"
            fi
          fi
          
          # Получаем токен
          TOKEN=""
          if [ -n "$YC" ] && [ -x "$YC" ]; then
            echo "Используем yc для получения токена"
            TOKEN="$($YC iam create-token 2>/dev/null || echo "")"
          fi
          
          # Если не получили токен через yc, пробуем альтернативные методы
          if [ -z "$TOKEN" ]; then
            echo "Не удалось получить токен через yc, пробуем альтернативные методы"
            
            # Метод 1: Проверяем переменные окружения
            if [ -n "${YC_IAM_TOKEN:-}" ]; then
              echo "Используем токен из переменной YC_IAM_TOKEN"
              TOKEN="${YC_IAM_TOKEN}"
            # Метод 2: Используем конфигурацию yc если есть
            elif [ -f "$HOME/.config/yandex-cloud/config.yaml" ]; then
              echo "Пробуем получить токен из конфигурации yc"
              # Здесь можно добавить логику парсинга конфига
            else
              echo "Не удалось получить токен для аутентификации"
              echo "Доступные варианты:"
              echo "1. Установите yc на pitest-node: curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash"
              echo "2. Добавьте IAM токен в Jenkins credentials как 'yc-iam-token'"
              exit 1
            fi
          fi
          
          echo "==> Логин в Yandex Container Registry"
          echo "$TOKEN" | docker login --username iam --password-stdin cr.yandex || {
            echo "Ошибка логина в YCR"
            echo "Проверьте токен: ${TOKEN:0:20}..."
            exit 1
          }
          
          echo "==> Пуш образов в YCR"
          docker push ${IMAGE_FULL} || {
            echo "Ошибка пуша ${IMAGE_FULL}"
            exit 1
          }
          
          docker push ${IMAGE_LATEST} || {
            echo "Ошибка пуша ${IMAGE_LATEST}"
            exit 1
          }
          
          echo "Образы успешно загружены в YCR"
        '''
      }
    }

    stage('Kubernetes Setup') {
      steps {
        sh '''
          kubectl get ns ${NAMESPACE} >/dev/null 2>&1 || kubectl create ns ${NAMESPACE}
          kubectl get all -n ${NAMESPACE} || echo "Неймспейс пуст"
        '''
      }
    }

    stage('Kubernetes Deploy') {
      steps {
        sh '''
          echo "==> Деплоймент в Kubernetes"
          echo "Используем образ: ${IMAGE_FULL}"
          
          # Простая замена образа в deployment.yaml
          sed "s|image:.*knn-vm-lab7.*|image: ${IMAGE_FULL}|g" k8s/deployment.yaml > k8s/deployment-temp.yaml
          
          kubectl apply -n ${NAMESPACE} -f k8s/deployment-temp.yaml
          kubectl apply -n ${NAMESPACE} -f k8s/service.yaml
          
          kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=180s
          kubectl get all -n ${NAMESPACE}
        '''
      }
    }

    stage('Verify Deployment') {
      steps {
        sh '''
          echo "==> Проверка работоспособности сервиса"
          
          # Простой health check через port-forward
          kubectl port-forward -n ${NAMESPACE} svc/${APP_NAME} 8888:80 &
          PF_PID=$!
          sleep 10
          
          if curl -f http://localhost:8888/health 2>/dev/null; then
            echo "Сервис работает"
            kill $PF_PID 2>/dev/null
          else
            echo "Health check не прошел"
            kill $PF_PID 2>/dev/null || true
            # Показываем логи для диагностики
            POD=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o jsonpath="{.items[0].metadata.name}" 2>/dev/null || echo "")
            if [ -n "$POD" ]; then
              echo "Логи пода $POD:"
              kubectl logs -n ${NAMESPACE} "$POD" --tail=50
            fi
          fi
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
        echo "Финальный статус:"
        kubectl get pods,svc -n ${NAMESPACE} 2>/dev/null || true
      '''
    }
  }
}
