# requirements - docker desktop, kubernetes, git bash

# create namespaces in kubernetes
kubectl create ns my-kafka-project
kubectl create ns my-postgres-project
kubectl create ns my-spark-project
kubectl create ns my-prometheus-grafana-project #optional
kubectl create ns my-elastic-project            #optional


# install kafka-operator
kubectl create -f strimzi-0.31.1/cluster-operator/020-RoleBinding-strimzi-cluster-operator.yaml -n my-kafka-project
kubectl create -f strimzi-0.31.1/cluster-operator/031-RoleBinding-strimzi-cluster-operator-entity-operator-delegation.yaml -n my-kafka-project
kubectl create -f strimzi-0.31.1/cluster-operator/ -n my-kafka-project

# create kafka cluster
kubectl apply -f kubernetes/kafka-myproject-kafkacluster.yaml
kubectl wait kafka/my-cluster-kafka --for=condition=Ready --timeout=600s -n my-kafka-project
# OR (if want to install prometheus & grafana as well)
kubectl apply -f kubernetes/kafka-myproject-kafkacluster-exporter.yaml
kubectl wait kafka/my-cluster-kafka --for=condition=Ready --timeout=600s -n my-kafka-project



# optional, create a kafka topic for testing purpose
kubectl apply -f kubernetes/kafka-myproject-kafkatopic.yaml
kubectl wait kafkatopic/my-topic-testing --for=condition=Ready --timeout=300s -n my-kafka-project
kubectl run kafka-topiclist -it --image=strimzi/kafka:0.20.0-rc1-kafka-2.6.0 --rm=true --restart=Never -- bin/kafka-topics.sh --bootstrap-server my-cluster-kafka-kafka-bootstrap.my-kafka-project:9092 --list
kubectl run kafka-producer -ti --image=strimzi/kafka:0.20.0-rc1-kafka-2.6.0 --rm=true --restart=Never -- bin/kafka-console-producer.sh --broker-list my-cluster-kafka-kafka-bootstrap.my-kafka-project:9092 --topic my-topic-testing
kubectl run kafka-consumer -ti --image=strimzi/kafka:0.20.0-rc1-kafka-2.6.0 --rm=true --restart=Never -- bin/kafka-console-consumer.sh --bootstrap-server my-cluster-kafka-kafka-bootstrap.my-kafka-project:9092 --topic my-topic-testing --from-beginning



# create kafka-connect to connect to debezium and elasticsearch
kubectl create secret generic elasticsearch-cluster-keystore --from-file=elastic-2.5.0/cert/keystore.jks -n my-kafka-project
kubectl apply -f kubernetes/kafka-myproject-kafkaconnect-elasticsearch.yaml -n my-kafka-project
kubectl wait kafkaconnect/my-cluster-kafkaconnect-dbz --for=condition=Ready --timeout=300s -n my-kafka-project

# create postgres-db
kubectl apply -f kubernetes/kafka-myproject-postgres.yaml -n my-postgres-project
kubectl wait deployment/my-postgresdb --for=condition=Available=True --timeout=300s -n my-postgres-project

# connect postgres-db to debezium
kubectl apply -f kubernetes/kafka-myproject-debezium.yaml -n my-kafka-project
kubectl wait kafkaconnector/my-connector-dbz --for=condition=Ready --timeout=300s -n my-kafka-project

# login to postgres-db and insert some data to a table
kubectl get pod -n my-postgres-project
kubectl exec -it $(kubectl get pod -l app=postgresql -n my-postgres-project -o jsonpath="{.items[0].metadata.name}") -n my-postgres-project -- psql -U debezium -d debezium_db



# optional, install prometheus-operator, prometheus and kibana
# install prometheus-operator
kubectl create -f prometheus-0.31.1/prometheus-myproject-operator.yaml -n my-prometheus-grafana-project
kubectl create secret generic additional-scrape-configs --from-file=prometheus-0.31.1/prometheus-additional-properties/prometheus-additional.yaml -n my-prometheus-grafana-project
kubectl apply -f prometheus-0.31.1/prometheus-additional-properties/prometheus-additional.yaml -n my-prometheus-grafana-project
kubectl apply -f prometheus-0.31.1/prometheus-alertmanager-config/alert-manager-config.yaml -n my-prometheus-grafana-project
# install prometheus
kubectl apply -f prometheus-0.31.1/prometheus-install/alert-manager.yaml -n my-prometheus-grafana-project
kubectl apply -f prometheus-0.31.1/prometheus-install/strimzi-pod-monitor.yaml -n my-prometheus-grafana-project
kubectl apply -f prometheus-0.31.1/prometheus-install/prometheus-rules.yaml -n my-prometheus-grafana-project
kubectl apply -f prometheus-0.31.1/prometheus-install/prometheus.yaml -n my-prometheus-grafana-project
# verify prometheus installation
kubectl get pods -n my-prometheus-grafana-project
kubectl get svc -n my-prometheus-grafana-project
# install grafana
kubectl apply -f grafana-0.31.1/grafana-install/grafana.yaml -n my-prometheus-grafana-project
# verify grafana installation
kubectl get pods -n my-prometheus-grafana-project
kubectl get svc -n my-prometheus-grafana-project
# forward grafana service, so you can access on your local browser
kubectl port-forward svc/grafana 3000:3000 -n my-prometheus-grafana-project
# open grafana webpage on web browser (http://localhost:3000), using this credential:
##### username: admin
##### password: admin
# add prometheus service address as a data-source inside setting tap (setting -> data source -> add data source)
##### http://prometheus-operator:8080                                                     (if same namspace with prometheus)
##### http://prometheus-operator.my-prometheus-grafana-project:8080                       (if different namspace with prometheus)
##### http://prometheus-operator.my-prometheus-grafana-project.svc.cluster.local:8080     (if different namspace with prometheus, fully qualified name)
# import these files to grafana webpage
##### grafana-0.31.1/grafana-dashboards/strimzi-kafka.json
##### grafana-0.31.1/grafana-dashboards/strimzi-kafka-exporter.json
##### grafana-0.31.1/grafana-dashboards/strimzi-operators.json
##### grafana-0.31.1/grafana-dashboards/strimzi-zookeeper.json



# install elastic-operator (install custom resource definitions, this will create custom crds for elasticsearch)
kubectl create -f elastic-2.5.0/eck-myproject-crds.yaml -n my-elastic-project
kubectl create -f elastic-2.5.0/eck-myproject-operator.yaml -n my-elastic-project
# check the installation
kubectl get all -n my-elastic-project
kubectl logs statefulset.apps/elastic-operator -n my-elastic-project

# deploy elasticsearch
kubectl apply -f elastic-2.5.0/elasticserach/elastic-myproject-elasticcluster.yaml -n my-elastic-project
# debug elasticsearch
kubectl describe elasticsearch elasticsearch-cluster -n my-elastic-project
kubectl get pods --selector='elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-cluster' -n my-elastic-project
kubectl describe pod --selector='elasticsearch.k8s.elastic.co/cluster-name=elasticsearch-cluster' -n my-elastic-project
kubectl logs $(kubectl get pod -l elasticsearch.k8s.elastic.co/version=8.5.3 -n my-elastic-project -o jsonpath="{.items[0].metadata.name}") -n my-elastic-project
# verify elasticsearch installation
kubectl get elasticsearch -n my-elastic-project
kubectl get pods -n my-elastic-project
kubectl get svc -n my-elastic-project
kubectl get pvc -n my-elastic-project
kubectl get pv -n my-elastic-project
kubectl get secret -n my-elastic-project
# get elasticsearch credentials
##### username='elastic'
##### password=
kubectl get secret elasticsearch-cluster-es-elastic-user -n my-elastic-project -o go-template='{{.data.elastic | base64decode}}'
# try to connect to elasticsearch inside a kubernetes's pod
kubectl exec -it $(kubectl get pod -l elasticsearch.k8s.elastic.co/version=8.5.3 -n my-elastic-project -o jsonpath="{.items[0].metadata.name}") -n my-elastic-project -- /bin/sh
curl -u "elastic:<paste-the-password-here>" -k "https://elasticsearch-cluster-es-http:9200"
curl -u "elastic:<paste-the-password-here>" -k "https://localhost:9200"

# deploy kibana
kubectl apply -f elastic-2.5.0/kibana/elastic-myproject-kibana.yaml -n my-elastic-project
# debug kibana
kubectl describe kibana elasticsearch-kibana -n my-elastic-project
kubectl get pods --selector='kibana.k8s.elastic.co/name=elasticsearch-kibana' -n my-elastic-project
kubectl describe pod --selector='kibana.k8s.elastic.co/name=elasticsearch-kibana' -n my-elastic-project
kubectl logs $(kubectl get pod -l kibana.k8s.elastic.co/version=8.5.3 -n my-elastic-project -o jsonpath="{.items[0].metadata.name}") -n my-elastic-project
# verify kibana installation
kubectl get kibana -n my-elastic-project
kubectl get pods -n my-elastic-project
kubectl get svc -n my-elastic-project
# forward kibana service, so you can access on your local browser
kubectl port-forward svc/elasticsearch-kibana-kb-http 5601 -n my-elastic-project
# open kibana webpage on web browser (https://localhost:5601), using this credential:
##### username: elastic
##### password: get the pwd by running - <kubectl get secret elasticsearch-cluster-es-elastic-user -n my-elastic-project -o go-template='{{.data.elastic | base64decode}}'>

# save ca.crt, tls.crt, tls.key locally elastic-2.5.0/cert/ (run in git bash)
kubectl get secret elasticsearch-cluster-es-http-certs-public -n my-elastic-project -o go-template='{{index .data "ca.crt" | base64decode }}' > elastic-2.5.0/cert/ca.crt
kubectl get secret elasticsearch-cluster-es-http-certs-public -n my-elastic-project -o go-template='{{index .data "tls.crt" | base64decode }}' > elastic-2.5.0/cert/tls.crt
kubectl get secret elasticsearch-cluster-es-http-certs-internal -n my-elastic-project -o go-template='{{index .data "tls.key" | base64decode }}' > elastic-2.5.0/cert/tls.key

# get keystore.p12
openssl pkcs12 -export \
  -in elastic-2.5.0/cert/tls.crt \
  -inkey elastic-2.5.0/cert/tls.key \
  -CAfile elastic-2.5.0/cert/ca.crt \
  -caname root \
  -out elastic-2.5.0/cert/keystore.p12 \
  -password pass:SFLzyT8DPkGGjDtn \
  -name elasticsearch-cluster-keystore

# get keystore.jks
keytool -importkeystore \
  -srckeystore elastic-2.5.0/cert/keystore.p12 \
  -srcstoretype PKCS12 \
  -srcstorepass SFLzyT8DPkGGjDtn \
  -deststorepass MPx57vkACsRWKVap \
  -destkeypass MPx57vkACsRWKVap \
  -destkeystore elastic-2.5.0/cert/keystore.jks \
  -alias elasticsearch-cluster-keystore

# adjust the secret with the new keystore.jks cred
kubectl delete secret elasticsearch-cluster-keystore -n my-kafka-project
kubectl create secret generic elasticsearch-cluster-keystore --from-file=elastic-2.5.0/cert/keystore.jks -n my-kafka-project



# optional, deploy beats filebeat
## output the log directly to elasticsearch
kubectl apply -f elastic-2.5.0/filebeats/elastic-myproject-filebeat.yaml -n my-elastic-project
## output the log to kafka topic
kubectl apply -f elastic-2.5.0/filebeats/elastic-myproject-filebeat-to-kafka.yaml -n my-elastic-project
# verify filebeat installation
kubectl get beat -n my-elastic-project
kubectl get pods -n my-elastic-project
kubectl get pods --selector='beat.k8s.elastic.co/name=elasticsearch-beats' -n my-elastic-project
kubectl logs $(kubectl get pod --selector='beat.k8s.elastic.co/name=elasticsearch-beats' -n my-elastic-project -o jsonpath="{.items[0].metadata.name}") -n my-elastic-project
# verify that filebeat captures the log
kubectl exec -it $(kubectl get pod --selector='beat.k8s.elastic.co/name=elasticsearch-beats' -n my-elastic-project -o jsonpath="{.items[0].metadata.name}") -n my-elastic-project -- bin/sh
curl -u "elastic:<paste-the-elasticsearch-password-here>" -k "https://elasticsearch-cluster-es-http.my-elastic-project:9200/filebeat-*/_search"
curl -u "elastic:<paste-the-elasticsearch-password-here>" -k "https://localhost:9200/filebeat-*/_search"



# deploy spark 3.2.4
## deploy spark master/driver
kubectl apply -f spark/spark-myproject-master.yaml -n my-spark-project
kubectl wait deployment/spark-master-ver324 --for=condition=Available=True --timeout=300s -n my-spark-project
## deploy spark worker
kubectl apply -f spark/spark-myproject-worker.yaml -n my-spark-project
kubectl wait deployment/spark-worker-ver324 --for=condition=Available=True --timeout=300s -n my-spark-project
# install spark dependencies
kubectl exec -it $(kubectl get pod -l app=spark-master-ver324 -n my-spark-project -o jsonpath="{.items[0].metadata.name}") -n my-spark-project -- pip install -r /opt/bitnami/spark/project/requirements.txt
kubectl exec -it $(kubectl get pod -l app=spark-worker-ver324 -n my-spark-project -o jsonpath="{.items[0].metadata.name}") -n my-spark-project -- pip install -r /opt/bitnami/spark/project/requirements.txt
kubectl exec -it $(kubectl get pod -l app=spark-worker-ver324 -n my-spark-project -o jsonpath="{.items[1].metadata.name}") -n my-spark-project -- pip install -r /opt/bitnami/spark/project/requirements.txt
# run spark code that will deploy a Machine Learning model
kubectl exec -it $(kubectl get pod -l app=spark-master-ver324 -n my-spark-project -o jsonpath="{.items[0].metadata.name}") -n my-spark-project -- spark-submit --master spark://spark:7077 --conf spark.driver.host=spark-client-master --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2 --driver-class-path /opt/bitnami/spark/project/connector/postgresql-42.5.1.jar --jars /opt/bitnami/spark/project/connector/postgresql-42.5.1.jar /opt/bitnami/spark/project/random-forest-chun-pred-model.py
# run spark code that will stream and transform the data from kafka-topic, then write the result to postgres-db and another kafka-topic
kubectl exec -it $(kubectl get pod -l app=spark-master-ver324 -n my-spark-project -o jsonpath="{.items[0].metadata.name}") -n my-spark-project -- spark-submit --master spark://spark:7077 --conf spark.driver.host=spark-client-master --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2 --driver-class-path /opt/bitnami/spark/project/connector/postgresql-42.5.1.jar --jars /opt/bitnami/spark/project/connector/postgresql-42.5.1.jar /opt/bitnami/spark/project/realtime-churn-pred.py



# deploy kafka-connector to capture the cdc messages to elasticsearch (update credentials in the file as well "connection.password: <paste-the-elasticsearch-password-here>")
kubectl apply -f kubernetes/kafka-myproject-elasticsearch-src.yaml -n my-kafka-project
kubectl wait kafkaconnector/my-connector-elasticsearch-src --for=condition=Ready --timeout=300s -n my-kafka-project
# deploy kafka-connector to capture the spark's code result to elasticsearch (update credentials in the file as well "connection.password: <paste-the-elasticsearch-password-here>")
kubectl apply -f kubernetes/kafka-myproject-elasticsearch-dst.yaml -n my-kafka-project
kubectl wait kafkaconnector/my-connector-elasticsearch-dst --for=condition=Ready --timeout=300s -n my-kafka-project



# delete all resources
kubectl delete ns my-kafka-project
kubectl delete ns my-postgres-project
kubectl delete ns my-prometheus-grafana-project
kubectl delete ns my-elastic-project
kubectl delete ns my-spark-project

kubectl delete -f strimzi-0.31.1/cluster-operator/
kubectl delete -f prometheus-0.31.1/
kubectl delete -f grafana-0.31.1/grafana-install
kubectl delete -f elastic-2.5.0/
kubectl delete -f kubernetes/
kubectl delete -f spark/