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
      }
    }

    stage('Build Docker') {
      steps {
        sh '''
          echo "=== СБОРКА DOCKER ==="
          docker build -t ${IMAGE_FULL} .
          docker tag ${IMAGE_FULL} ${IMAGE_LATEST}
        '''
      }
    }

    stage('Push to YCR') {
      steps {
        sh '''#!/bin/bash
          echo "=== ПУШ В YCR ==="
          # Просто логинимся и пушим - как РАНЬШЕ РАБОТАЛО!
          yc iam create-token | docker login --username iam --password-stdin cr.yandex
          docker push ${IMAGE_FULL}
          docker push ${IMAGE_LATEST}
          echo "✅ ОБРАЗЫ ЗАПУШЕНЫ"
        '''
      }
    }

    stage('Deploy to K8S') {
      steps {
        sh '''
          echo "=== ДЕПЛОЙ В K8S ==="
          # Простая замена образа в деплойменте
          sed -i "s|image:.*knn-vm-lab7.*|image: ${IMAGE_FULL}|g" k8s/deployment.yaml
          
          # Применяем
          kubectl apply -f k8s/deployment.yaml -n ${NAMESPACE}
          kubectl apply -f k8s/service.yaml -n ${NAMESPACE}
          
          # Ждём
          sleep 10
          kubectl get pods -n ${NAMESPACE}
        '''
      }
    }
  }

  post {
    always {
      sh '''
        echo "=== ФИНИШ ==="
        kubectl get all -n ${NAMESPACE} || echo "K8s недоступен"
      '''
    }
  }
}
