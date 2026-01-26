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
          find . -maxdepth 2 -type f -name "*.py" -o -name "*.yaml" -o -name "Dockerfile" | sort
        '''
      }
    }

    stage('Build & Test') {
      steps {
        sh '''
          pip3 install --user -r requirements.txt
          python3 -c "from core.imputer_service import KNNImputationService; print('Модель загружается')"
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
          echo "==> Список локальных образов"
          docker images | grep ${APP_NAME} || true
        '''
      }
    }

    stage('Docker login + push to YCR') {
      steps {
        sh '''#!/usr/bin/env bash
          set -euo pipefail

          # Явный путь к yc
          YC="/home/ubuntu/yandex-cloud/bin/yc"

          # если yc не найден — сразу понятная ошибка
          test -x "$YC" || (echo "yc not found at $YC" && exit 1)

          echo "==> Get IAM token"
          TOKEN="$($YC iam create-token)"

          echo "==> Docker login to YCR"
          echo "$TOKEN" | docker login --username iam --password-stdin cr.yandex

          echo "==> Push image"
          docker push ${IMAGE_FULL}
          docker push ${IMAGE_LATEST}
        '''
      }
    }

    stage('Kubernetes Deploy') {
      steps {
        sh '''#!/usr/bin/env bash
          set -e
          kubectl get ns ${NAMESPACE} >/dev/null 2>&1 || kubectl create ns ${NAMESPACE}

          # Заменяем образ в deployment.yaml
          sed "s|image:.*knn-vm-lab7.*|image: ${IMAGE_FULL}|g" k8s/deployment.yaml > k8s/deployment-temp.yaml
          
          kubectl apply -n ${NAMESPACE} -f k8s/deployment-temp.yaml
          kubectl apply -n ${NAMESPACE} -f k8s/service.yaml

          kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=180s
          kubectl get all -n ${NAMESPACE}
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
