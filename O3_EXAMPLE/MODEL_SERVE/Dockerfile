FROM tensorflow/serving

COPY . .

EXPOSE 8500
EXPOSE 8501

CMD ["tensorflow_model_server", "--model_config_file=/models/model_config_list.pbtxt", "--port=8500", "--rest_api_port=8501"]
