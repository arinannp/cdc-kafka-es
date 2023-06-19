import os
import logging
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

project_dir =  os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'project')
logging.info(f"Project Directory in Pod: {project_dir}")

spark = SparkSession \
    .builder \
    .config('spark.driver.extraClassPath', os.path.join(project_dir, 'connector/postgresql-42.5.1.jar')) \
    .appName('Spark ML Churn Prediction Using RandomForest') \
    .getOrCreate()

spark.sparkContext.setLogLevel('INFO')


df = spark.read.format('csv') \
                .option('header', True) \
                .option("inferSchema", True) \
                .load(f'{project_dir}/source/churn_train.csv')

df.show()
df.printSchema()

########################################################################################################################
logging.info("########################################## TRANSFORMING DATAFRAME ########################################")
featureColumns = ["InternetService_index","OnlineBackup_index","MultipleLines_index",
                  "StreamingTV_index","Partner_index","Dependents_index","StreamingMovies_index",
                  "DeviceProtection_index","tenure_index","gender_index","PaperlessBilling_index",
                  "OnlineSecurity_index","SeniorCitizen_index","TechSupport_index",
                  "PhoneService_index","PaymentVec","ContractVec","MonthlyCharges","TotalCharges"]

indexers = [StringIndexer(inputCol=column, outputCol=column+"_index").fit(df) for column in list(set(df.columns)-set(['date'])) ]
logging.info(indexers)

onehotencoder1 = OneHotEncoder(inputCol="PaymentMethod_index", outputCol="PaymentVec", dropLast = False)
onehotencoder2 = OneHotEncoder(inputCol="Contract_index", outputCol="ContractVec", dropLast = False)
logging.info(onehotencoder1)
logging.info(onehotencoder2)

assembler = VectorAssembler(inputCols = featureColumns, outputCol = "features")
logging.info(assembler)

########################################################################################################################
logging.info("########################################## APPLY TRANSFORMATION TO A DATAFRAME ########################################")
stages1 = indexers
stages1.append(onehotencoder1)
stages1.append(onehotencoder2)
stages1.append(assembler)

pipeline = Pipeline(stages=stages1)
df_clean = pipeline.fit(df).transform(df)
df_clean.show()
df_clean.printSchema()

########################################################################################################################
logging.info("########################################## SPLITTING AND CREATING ML MODEL ########################################")
(trainingData, testData) = df_clean.randomSplit([0.75, 0.25], seed=0)
rf = RandomForestClassifier(labelCol = "Churn_index", 
                            featuresCol = "features", 
                            numTrees = 15, 
                            maxBins = 100)
model = rf.fit(trainingData)

prediction = model.transform(testData)
prediction.show(20, truncate = False)
prediction.printSchema()
prediction.select("customerID", "Churn", "Churn_index", "probability", "prediction").show(20, truncate = False)
prediction.select("customerID", "Churn", "Churn_index", vector_to_array("probability").alias("probability"), "prediction") \
                .withColumn("Prob_0", f.col("probability").getItem(0)) \
                .withColumn("Prob_1", f.col("probability").getItem(1)) \
                .drop("probability") \
                .coalesce(1).write \
                .mode("overwrite") \
                .option("mapreduce.fileoutputcommitter.marksuccessfuljobs","false") \
                .option("header","true") \
                .csv("/opt/bitnami/spark/project/output/churn-randomforest-train")

########################################################################################################################
logging.info("########################################## EVALUATING ML MODEL ########################################")
evaluator = MulticlassClassificationEvaluator(labelCol="Churn_index", predictionCol="prediction", metricName="accuracy")
accuracy = evaluator.evaluate(prediction)
logging.info("Accuracy = %g" %  accuracy)

model.write().overwrite().save('/opt/bitnami/spark/project/model-cls-randomforest')
########################################################################################################################
logging.info("########################################## PREDICTING WITH NEW DATASET ########################################")
model_import = RandomForestClassificationModel.load('/opt/bitnami/spark/project/model-cls-randomforest')

df_test = spark.read.format('csv') \
                .option('header', True) \
                .option("inferSchema", True) \
                .load(f'{project_dir}/source/churn_test.csv')

df_test.show()
df_test.printSchema()

featureColumns = ["InternetService_index","OnlineBackup_index","MultipleLines_index",
                  "StreamingTV_index","Partner_index","Dependents_index","StreamingMovies_index",
                  "DeviceProtection_index","tenure_index","gender_index","PaperlessBilling_index",
                  "OnlineSecurity_index","SeniorCitizen_index","TechSupport_index",
                  "PhoneService_index","PaymentVec","ContractVec","MonthlyCharges","TotalCharges"]

indexers = [StringIndexer(inputCol=column, outputCol=column+"_index").fit(df_test) for column in list(set(df_test.columns)-set(['date'])) ]
logging.info(indexers)

onehotencoder1 = OneHotEncoder(inputCol="PaymentMethod_index", outputCol="PaymentVec", dropLast = False)
onehotencoder2 = OneHotEncoder(inputCol="Contract_index", outputCol="ContractVec", dropLast = False)
logging.info(onehotencoder1)
logging.info(onehotencoder2)

assembler = VectorAssembler(inputCols = featureColumns, outputCol = "features")
logging.info(assembler)

stages1 = indexers
stages1.append(onehotencoder1)
stages1.append(onehotencoder2)
stages1.append(assembler)

pipeline = Pipeline(stages=stages1)
df_test_clean = pipeline.fit(df_test).transform(df_test)
df_test_clean.show()
df_test_clean.printSchema()

prediction = model_import.transform(df_test_clean)
prediction.show(20, truncate = False)
prediction.printSchema()
prediction.select("customerID", "Churn", "Churn_index", "probability", "prediction").show(20, truncate = False)
prediction.select("customerID", "Churn", "Churn_index", vector_to_array("probability").alias("probability"), "prediction") \
                .withColumn("Prob_0", f.col("probability").getItem(0)) \
                .withColumn("Prob_1", f.col("probability").getItem(1)) \
                .drop("probability") \
                .coalesce(1).write \
                .mode("overwrite") \
                .option("mapreduce.fileoutputcommitter.marksuccessfuljobs","false") \
                .option("header","true") \
                .csv("/opt/bitnami/spark/project/output/churn-randomforest-test")