CREATE TABLE person_identity (
   id           SERIAL PRIMARY KEY,
   login_date   DATE,
   first_name   VARCHAR(30),
   last_name    VARCHAR(30),
   address      VARCHAR(255),
   active       BOOLEAN
);

CREATE TABLE person_identity_captured (
   id             INTEGER,
   login_date     DATE,
   first_name     VARCHAR(30),
   last_name      VARCHAR(30),
   address        VARCHAR(255),
   active         BOOLEAN,
   previous_data  TEXT,
   operation      VARCHAR(15),
   ts_ms          FLOAT,
   recorded_ts    TIMESTAMP
);

CREATE TABLE person_churn_history (
   customerID           VARCHAR(20) PRIMARY KEY,
   gender               VARCHAR(10),
   SeniorCitizen        INTEGER,
   Partner              VARCHAR(50),
   Dependents           VARCHAR(50),
   tenure               INTEGER,
   PhoneService         VARCHAR(50),
   MultipleLines        VARCHAR(50),
   InternetService      VARCHAR(100),
   OnlineSecurity       VARCHAR(100),
   OnlineBackup         VARCHAR(100),
   DeviceProtection     VARCHAR(100),
   TechSupport          VARCHAR(100),
   StreamingTV          VARCHAR(100),
   StreamingMovies      VARCHAR(100),
   Contract             VARCHAR(50),
   PaperlessBilling     VARCHAR(50),
   PaymentMethod        VARCHAR(100),
   MonthlyCharges       INTEGER,
   TotalCharges         INTEGER,
   Churn                VARCHAR(10)
);

CREATE TABLE person_churn_history_captured (
   customerID           VARCHAR(20),
   gender               VARCHAR(10),
   SeniorCitizen        INTEGER,
   Partner              VARCHAR(50),
   Dependents           VARCHAR(50),
   tenure               INTEGER,
   PhoneService         VARCHAR(50),
   MultipleLines        VARCHAR(50),
   InternetService      VARCHAR(100),
   OnlineSecurity       VARCHAR(100),
   OnlineBackup         VARCHAR(100),
   DeviceProtection     VARCHAR(100),
   TechSupport          VARCHAR(100),
   StreamingTV          VARCHAR(100),
   StreamingMovies      VARCHAR(100),
   Contract             VARCHAR(50),
   PaperlessBilling     VARCHAR(50),
   PaymentMethod        VARCHAR(100),
   MonthlyCharges       INTEGER,
   TotalCharges         INTEGER,
   Churn                VARCHAR(10),
   Prediction           VARCHAR(10),
   ProbabilityNo        FLOAT,
   ProbabilityYes       FLOAT,
   previous_data        TEXT,
   operation            VARCHAR(10),
   ts_ms                FLOAT,
   recorded_ts          TIMESTAMP
);

ALTER SYSTEM SET wal_level TO 'logical';
ALTER TABLE person_identity REPLICA IDENTITY FULL;
ALTER TABLE person_churn_history REPLICA IDENTITY FULL;