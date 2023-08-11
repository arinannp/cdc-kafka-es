import os
import json
import logging
from bson import json_util
from kafka import KafkaProducer

from pyspark.sql import SparkSession
from pyspark.sql import functions as f

from pyspark.ml import Pipeline
from pyspark.ml.functions import vector_to_array
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.classification import RandomForestClassificationModel
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.feature import OneHotEncoder, VectorAssembler, StringIndexer, VectorIndexer



logging.getLogger().setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.INFO)
logging.info('Starting...')

project_dir =  os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'project')
logging.info(f"Project Directory in Pod: {project_dir}")


BOOTSTRAP_SERVER = os.getenv('BOOTSTRAP_SERVER')
TOPIC_NAME = os.getenv('TOPIC_NAME')
TOPIC_NAME_DEST = os.getenv('TOPIC_NAME_DEST')

POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
TABLE_DEST = os.getenv('TABLE_DEST')


spark = SparkSession \
    .builder \
    .config('spark.driver.extraClassPath', os.path.join(project_dir, 'connector/postgresql-42.5.1.jar')) \
    .appName("Spark Streaming ML Inference App") \
    .getOrCreate()

spark.sparkContext.setLogLevel('WARN')

# https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", BOOTSTRAP_SERVER) \
    .option("subscribe", TOPIC_NAME) \
    .option("startingOffsets", "earliest") \
    .load()


# string connection to postgres-db
conn: str = f"jdbc:postgresql://{POSTGRES_HOST}/{POSTGRES_DB}"
properties: dict = {
    "user": POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
    "driver": "org.postgresql.Driver"
}

# import random forest clasification model
model = RandomForestClassificationModel.load('/opt/bitnami/spark/project/model-cls-randomforest')

# output schema while writing the result to kafka-topic
schema_target = {
    "type": "struct",
    "fields": [
        {
            "type": "string",
            "optional": False,
            "field": "customerID"
        },
        {
            "type": "string",
            "optional": True,
            "field": "gender"
        },
        {
            "type": "int32",
            "optional": True,
            "field": "SeniorCitizen"
        },
        {
            "type": "string",
            "optional": True,
            "field": "Partner"
        },
        {
            "type": "string",
            "optional": True,
            "field": "Dependents"
        },
        {
            "type": "int32",
            "optional": True,
            "field": "tenure"
        },
        {
            "type": "string",
            "optional": True,
            "field": "PhoneService"
        },
        {
            "type": "string",
            "optional": True,
            "field": "MultipleLines"
        },
        {
            "type": "string",
            "optional": True,
            "field": "InternetService"
        },
        {
            "type": "string",
            "optional": True,
            "field": "OnlineSecurity"
        },
        {
            "type": "string",
            "optional": True,
            "field": "OnlineBackup"
        },
        {
            "type": "string",
            "optional": True,
            "field": "DeviceProtection"
        },
        {
            "type": "string",
            "optional": True,
            "field": "TechSupport"
        },
        {
            "type": "string",
            "optional": True,
            "field": "StreamingTV"
        },
        {
            "type": "string",
            "optional": True,
            "field": "StreamingMovies"
        },
        {
            "type": "string",
            "optional": True,
            "field": "Contract"
        },
        {
            "type": "string",
            "optional": True,
            "field": "PaperlessBilling"
        },
        {
            "type": "string",
            "optional": True,
            "field": "PaymentMethod"
        },
        {
            "type": "int32",
            "optional": True,
            "field": "MonthlyCharges"
        },
        {
            "type": "int32",
            "optional": True,
            "field": "TotalCharges"
        },
        {
            "type": "string",
            "optional": True,
            "field": "Churn"
        },
        {
            "type": "string",
            "optional": True,
            "field": "Prediction"
        },
        {
            "type": "float",
            "optional": True,
            "field": "ProbabilityNo"
        },
        {
            "type": "float",
            "optional": True,
            "field": "ProbabilityYes"
        },
        {
            "type": "string",
            "optional": True,
            "field": "previous_data"
        },
        {
            "type": "string",
            "optional": True,
            "field": "operation"
        },
        {
            "type": "float",
            "optional": True,
            "field": "ts_ms"
        },
        {
            "type": "string",
            "optional": True,
            "field": "recorded_ts"
        },
    ],
    "optional": False,
    "name": "person_churn_history_predicted.Envelope"
}



def send_to_kafka(record):
    producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVER,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'))
    value = {
        'schema': json.loads(json.dumps(schema_target)),
        'payload': json.loads(record.payload)
    }    
    producer.send(TOPIC_NAME_DEST, value=value)


def write_postgres(stream_df, stream_id):
    stream_df.printSchema()
    stream_df.show(truncate = False)

    dump_df = spark.read.format('csv') \
                .option('header', True) \
                .option("inferSchema", True) \
                .load(f'{project_dir}/source/churn_validate.csv')
    
    pred_df = dump_df.unionByName(stream_df, allowMissingColumns=True)

    featureColumns = ["InternetService_index","OnlineBackup_index","MultipleLines_index",
                "StreamingTV_index","Partner_index","Dependents_index","StreamingMovies_index",
                "DeviceProtection_index","tenure_index","gender_index","PaperlessBilling_index",
                "OnlineSecurity_index","SeniorCitizen_index","TechSupport_index",
                "PhoneService_index","PaymentVec","ContractVec","MonthlyCharges","TotalCharges"]
    
    indexers = [StringIndexer(inputCol=column, outputCol=column+"_index").fit(pred_df) for column in list(set(pred_df.columns)-set(["previous_data","operation","ts_ms","recorded_ts"]))]
    onehotencoder1 = OneHotEncoder(inputCol="PaymentMethod_index", outputCol="PaymentVec", dropLast = False)
    onehotencoder2 = OneHotEncoder(inputCol="Contract_index", outputCol="ContractVec", dropLast = False)
    assembler = VectorAssembler(inputCols = featureColumns, outputCol = "features")

    stages1 = indexers
    stages1.append(onehotencoder1)
    stages1.append(onehotencoder2)
    stages1.append(assembler)

    pipeline = Pipeline(stages=stages1)
    pred_df_transformed = pipeline.fit(pred_df).transform(pred_df)
    pred_df_transformed.printSchema()
    pred_df_transformed.show(truncate = False)
    
    # https://stackoverflow.com/questions/58032291/pyspark-impossible-to-show-predictions-of-a-random-forest-model-failed-to-exe
    prediction = model.transform(pred_df_transformed)
    prediction.printSchema()
    prediction.show(truncate = False)

    result_df = prediction \
        .withColumn("Prediction", f.when(f.col("prediction") >= 0.5, "Yes").otherwise("No")) \
        .withColumn("probability", vector_to_array("probability").alias("probability")) \
        .withColumn("ProbabilityNo", f.col("probability").getItem(0).cast("float")) \
        .withColumn("ProbabilityYes", f.col("probability").getItem(1).cast("float")) \
        .select("customerID","gender","SeniorCitizen","Partner","Dependents","tenure","PhoneService",
            "MultipleLines","InternetService","OnlineSecurity","OnlineBackup","DeviceProtection","TechSupport",
            "StreamingTV","StreamingMovies","Contract","PaperlessBilling","PaymentMethod","MonthlyCharges","TotalCharges",
            "Churn","Prediction","ProbabilityNo","ProbabilityYes","previous_data","operation","ts_ms","recorded_ts") \
        .where(f.col("recorded_ts").isNotNull())
    
    result_df.write.mode("append").jdbc(conn, table=TABLE_DEST, properties=properties)
    rdd = result_df.withColumn("recorded_ts", f.col("recorded_ts").cast("string")) \
                .selectExpr("to_json(struct(*)) AS payload") \
                .rdd
    rdd.foreach(send_to_kafka)
    
    result_df.printSchema()
    result_df.show(truncate = False)



df \
    .withColumn("key", f.col("key").cast("STRING")) \
    .withColumn("value", f.col("value").cast("STRING")) \
    .withColumn("customerID", f.get_json_object(f.col("value"), "$.payload.after.customerid")) \
    .withColumn("gender", f.get_json_object(f.col("value"), "$.payload.after.gender")) \
    .withColumn("SeniorCitizen", f.get_json_object(f.col("value"), "$.payload.after.seniorcitizen").cast("integer")) \
    .withColumn("Partner", f.get_json_object(f.col("value"), "$.payload.after.partner")) \
    .withColumn("Dependents", f.get_json_object(f.col("value"), "$.payload.after.dependents")) \
    .withColumn("tenure", f.get_json_object(f.col("value"), "$.payload.after.tenure").cast("integer")) \
    .withColumn("PhoneService", f.get_json_object(f.col("value"), "$.payload.after.phoneservice")) \
    .withColumn("MultipleLines", f.get_json_object(f.col("value"), "$.payload.after.multiplelines")) \
    .withColumn("InternetService", f.get_json_object(f.col("value"), "$.payload.after.internetservice")) \
    .withColumn("OnlineSecurity", f.get_json_object(f.col("value"), "$.payload.after.onlinesecurity")) \
    .withColumn("OnlineBackup", f.get_json_object(f.col("value"), "$.payload.after.onlinebackup")) \
    .withColumn("DeviceProtection", f.get_json_object(f.col("value"), "$.payload.after.deviceprotection")) \
    .withColumn("TechSupport", f.get_json_object(f.col("value"), "$.payload.after.techsupport")) \
    .withColumn("StreamingTV", f.get_json_object(f.col("value"), "$.payload.after.streamingtv")) \
    .withColumn("StreamingMovies", f.get_json_object(f.col("value"), "$.payload.after.streamingmovies")) \
    .withColumn("Contract", f.get_json_object(f.col("value"), "$.payload.after.contract")) \
    .withColumn("PaperlessBilling", f.get_json_object(f.col("value"), "$.payload.after.paperlessbilling")) \
    .withColumn("PaymentMethod", f.get_json_object(f.col("value"), "$.payload.after.paymentmethod")) \
    .withColumn("MonthlyCharges", f.get_json_object(f.col("value"), "$.payload.after.monthlycharges").cast("integer")) \
    .withColumn("TotalCharges", f.get_json_object(f.col("value"), "$.payload.after.totalcharges").cast("integer")) \
    .withColumn("Churn", f.get_json_object(f.col("value"), "$.payload.after.churn")) \
    .withColumn("previous_data", f.get_json_object(f.col("value"), "$.payload.before").cast("string")) \
    .withColumn("operation", f.get_json_object(f.col("value"), "$.payload.op")) \
    .withColumn("ts_ms", f.get_json_object(f.col("value"), "$.payload.ts_ms").cast("float")) \
    .withColumn("recorded_ts", f.to_timestamp(f.col("timestamp"), "yyyy-MM-dd HH:MM:SS")) \
    .select("customerID","gender","SeniorCitizen","Partner","Dependents","tenure","PhoneService",
            "MultipleLines","InternetService","OnlineSecurity","OnlineBackup","DeviceProtection",
            "TechSupport","StreamingTV","StreamingMovies","Contract","PaperlessBilling","PaymentMethod",
            "MonthlyCharges","TotalCharges","Churn","previous_data","operation","ts_ms","recorded_ts") \
    .writeStream \
    .trigger(processingTime='5 seconds') \
    .foreachBatch(write_postgres) \
    .start() \
    .awaitTermination()