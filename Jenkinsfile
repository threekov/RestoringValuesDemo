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
    stage('Fix Docker Credential Helper') {
      steps {
        sh '''#!/bin/bash
          echo "=== ФИКСИМ DOCKER-CREDENTIAL-YC ==="
          # Удаляем битый docker-credential-yc если есть
          sudo rm -f /usr/local/bin/docker-credential-yc 2>/dev/null || true
          sudo rm -f /usr/bin/docker-credential-yc 2>/dev/null || true
          echo "docker-credential-yc удален"
        '''
      }
    }

    stage('Checkout') {
      steps { 
        checkout scm 
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

    stage('Push to YCR - Simple Auth') {
      steps {
        sh '''#!/bin/bash
          echo "=== ПУШ В YCR (упрощенная аутентификация) ==="
          
          # Получаем токен
          TOKEN=$(yc iam create-token)
          echo "Токен получен"
          
          # Используем простую аутентификацию без credential helper
          echo "Авторизация в Docker..."
          AUTH=$(echo -n "iam:$TOKEN" | base64)
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
          
          # Пушим
          echo "Пушим образ..."
          docker push ${IMAGE_FULL}
          docker push ${IMAGE_LATEST}
          
          echo "Образы успешно загружены в YCR!"
        '''
      }
    }

    stage('Deploy to K8S - Fix Image') {
      steps {
        sh '''
          echo "=== ДЕПЛОЙ В K8S ==="
          
          # 1. Сначала удаляем старый деплоймент с битым образом
          kubectl delete deployment ${APP_NAME} -n ${NAMESPACE} --ignore-not-found=true
          kubectl delete rs -n ${NAMESPACE} -l app=${APP_NAME} --ignore-not-found=true
          kubectl delete pods -n ${NAMESPACE} -l app=${APP_NAME} --ignore-not-found=true
          echo "Старые ресурсы удалены"
          sleep 5
          
          # 2. Создаем новый deployment.yaml с правильным образом
          cat > k8s/deployment-fixed.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${APP_NAME}
  namespace: ${NAMESPACE}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ${APP_NAME}
  template:
    metadata:
      labels:
        app: ${APP_NAME}
    spec:
      containers:
        - name: ${APP_NAME}
          image: ${IMAGE_FULL}
          imagePullPolicy: Always
          ports:
            - name: http
              containerPort: 8000
          env:
            - name: PYTHONUNBUFFERED
              value: "1"
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
EOF
          
          # 3. Применяем
          echo "Применяем исправленный deployment..."
          kubectl apply -f k8s/deployment-fixed.yaml
          kubectl apply -f k8s/service.yaml -n ${NAMESPACE}
          
          # 4. Ждем
          echo "Ожидаем развертывания..."
          sleep 15
          kubectl get pods -n ${NAMESPACE} -w &
          sleep 30
          pkill -f "kubectl get pods"
          
          echo "Деплоймент завершен!"
          kubectl get all -n ${NAMESPACE}
        '''
      }
    }

    stage('Verify') {
      steps {
        sh '''
          echo "=== ПРОВЕРКА ==="
          echo "Поды:"
          kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o wide
          
          echo "Логи первого пода:"
          POD=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o jsonpath="{.items[0].metadata.name}" 2>/dev/null || echo "")
          if [ -n "$POD" ]; then
            echo "Логи пода $POD:"
            kubectl logs -n ${NAMESPACE} $POD --tail=20
          fi
        '''
      }
    }
  }

  post {
    always {
      sh '''
        echo "=== ФИНИШ ==="
        rm -f k8s/deployment-fixed.yaml 2>/dev/null || true
        kubectl get all -n ${NAMESPACE}
      '''
    }
  }
}
