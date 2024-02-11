FROM tensorflow/serving

ENV MODEL_NAME_1=waf_db_protector
ENV MODEL_NAME_2=waf_edge

COPY . .

EXPOSE 8501
EXPOSE 8500

CMD tensorflow_model_server --port=8500 --rest_api_port=8501 --model_name=$MODEL_NAME_1 --model_base_path=/models/$MODEL_NAME_1 --model_name=$MODEL_NAME_2 --model_base_path=/models/$MODEL_NAME_2
