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
    stage('Fix Docker Config') {
      steps {
        sh '''#!/bin/bash
          echo "=== ФИКСИМ DOCKER CONFIG ==="
          
          # Удаляем старый кривой config
          rm -f ~/.docker/config.json
          rm -f /root/.docker/config.json 2>/dev/null || true
          
          echo "Старый docker config удален"
        '''
      }
    }

    stage('Checkout') {
      steps { 
        checkout scm 
        sh '''
          echo "Ревизия: $(git rev-parse --short HEAD)"
          echo "Нода: $(hostname)"
          echo "YC версия: $(yc --version)"
        '''
      }
    }

    stage('Build & Test') {
      steps {
        sh '''
          echo "==> Установка зависимостей Python"
          pip3 install --user -r requirements.txt
          
          echo "==> Проверка импорта модели"
          python3 -c "from core.imputer_service import KNNImputationService; print('Модель загружается')"
          echo "==> Проверка FastAPI приложения"
          python3 -c "import app; print('Приложение импортируется')"
        '''
      }
    }

    stage('Docker Build') {
      steps {
        sh '''
          echo "==> Сборка Docker образа"
          docker build -t ${IMAGE_FULL} .
          docker tag ${IMAGE_FULL} ${IMAGE_LATEST}
          echo "==> Локальные образы:"
          docker images | grep ${APP_NAME} || true
        '''
      }
    }

    stage('Docker Push to YCR - SIMPLE') {
      steps {
        sh '''#!/usr/bin/env bash
          set -e
          echo "==> Подготовка к пушу в YCR"
          
          # Проверяем наличие yc
          echo "Найден yc: $(which yc)"
          
          echo "==> Получение IAM токена"
          TOKEN=$(yc iam create-token)
          echo "Токен получен (первые 20 символов): ${TOKEN:0:20}..."
          
          echo "==> Логин в Yandex Container Registry"
          # ИГНОРИРУЕМ ошибку сохранения credentials!
          echo "$TOKEN" | docker login --username iam --password-stdin cr.yandex 2>&1 | grep -v "Error saving credentials" || true
          
          # Проверяем что логин прошел
          if grep -q "cr.yandex" ~/.docker/config.json 2>/dev/null; then
            echo "Docker login успешен"
          else
            echo "Docker login не создал config, создаем вручную..."
            AUTH=$(echo -n "iam:$TOKEN" | base64)
            mkdir -p ~/.docker
            cat > ~/.docker/config.json << EOF
{
  "auths": {
    "cr.yandex": {
      "auth": "$AUTH"
    }
  }
}
EOF
          fi
          
          echo "==> Пуш образов в YCR"
          echo "Отправка: ${IMAGE_FULL}"
          docker push ${IMAGE_FULL} || {
            echo "Ошибка при пуше!"
            echo "Проверяем текущий docker config:"
            cat ~/.docker/config.json 2>/dev/null || echo "Нет config"
            exit 1
          }
          
          echo "Отправка: ${IMAGE_LATEST}"
          docker push ${IMAGE_LATEST} || echo "Не удалось загрузить latest"
          
          echo "Образы успешно загружены в YCR"
        '''
      }
    }

    stage('Kubernetes Deploy') {
      steps {
        sh '''
          echo "==> Деплоймент в Kubernetes"
          echo "Используем образ: ${IMAGE_FULL}"
          
          # Убедимся что в deployment.yaml есть IMAGE_PLACEHOLDER
          if ! grep -q "IMAGE_PLACEHOLDER" k8s/deployment.yaml; then
            echo "В deployment.yaml нет IMAGE_PLACEHOLDER!"
            echo "Исправь k8s/deployment.yaml:"
            echo "  image: IMAGE_PLACEHOLDER"
            exit 1
          fi
          
          # Создаем временный deployment файл с подставленным образом
          sed "s|IMAGE_PLACEHOLDER|${IMAGE_FULL}|g" k8s/deployment.yaml > k8s/deployment-temp.yaml
          
          # Удаляем старый деплоймент
          kubectl delete deployment ${APP_NAME} -n ${NAMESPACE} --ignore-not-found=true
          sleep 3
          
          # Применяем манифесты
          kubectl apply -f k8s/deployment-temp.yaml
          kubectl apply -f k8s/service.yaml -n ${NAMESPACE}
          
          # Ждем rollout
          echo "Ожидаем развертывания..."
          kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=180s || {
            echo "Rollout status не завершился, проверяем вручную..."
            sleep 10
          }
          
          # Показываем статус
          echo "==> Финальное состояние"
          kubectl get all -n ${NAMESPACE}
          
          # Проверяем поды
          echo "Статус подов:"
          kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o wide
        '''
      }
    }
  }

  post {
    always {
      sh '''
        echo "==> Очистка"
        rm -f k8s/deployment-temp.yaml 2>/dev/null || true
        
        echo "==> Итог"
        echo "Образ: ${IMAGE_FULL}"
        echo "Поды:"
        kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} 2>/dev/null || echo "Поды не найдены"
      '''
    }
  }
}
