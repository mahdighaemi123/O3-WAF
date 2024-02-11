# O3 WAF
A twin WAF with honeypot for SQL Injection Protection
- Brother -> waf edge
- Sister -> waf db protector

## WAF Edge
Check `POST data` (body) and `GET data` (params & query) from sql injection using deep learning and nlp
```
Train accuricy: - (soon)
Test accuricy: - (soon)
```

## WAF DB Protector
Check `db query` sending to the database to be free of sql injection using deep learning and nlp
```
Train accuricy: - (soon)
Test accuricy: - (soon)
```

## TRAIN
We use `distilbert-base-uncased` as pre-train model and finetune it with sqk injection dataset
- Train WAF DB Protector -> [open in kaggle](https://www.kaggle.com/mahdighaemi/waf-db-protector-sql-injection-detector)
- Train WAF Edge -> [open in kaggle](https://www.kaggle.com/code/mahdighaemi/waf-edge-sql-injection-detector)


## RUN

#### STEP 1 | CLONE REPOSITORY
`
git clone https://github.com/mahdighaemi123/O3-WAF
`

#### STEP 2 -|DOWNLOAD MODELS

- Download saved_model.zip from notebook output -> [open in kaggle](https://www.kaggle.com/mahdighaemi/waf-db-protector-sql-injection-detector) and extract it in MODEL_SERVE/models
- Download saved_model.zip from notebook output ->  [open in kaggle](https://www.kaggle.com/code/mahdighaemi/waf-edge-sql-injection-detector) and extract it in MODEL_SERVE/models

#### STEP 3 | RUN
```
cd O3_EXAMPLE
docker compose up
```

#### STEP 4 | ACCESS
```
WAF_EDGE LISTEN 0.0.0.0:5050
```