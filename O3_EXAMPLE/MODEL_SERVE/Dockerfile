# Use the official TensorFlow Serving Docker image
FROM tensorflow/serving

# Copy the model configurations into the container
COPY . .

# Expose ports for gRPC (8500) and REST (8501)
EXPOSE 8500
EXPOSE 8501

# Start TensorFlow Serving when the container starts
CMD ["tensorflow_model_server", "--model_config_file=/models/model_config_list.pbtxt", "--port=8500", "--rest_api_port=8501"]
