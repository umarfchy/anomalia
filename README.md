# Anomalia

This project aims to detect server logs anomalies in real time. Here is a detailed outline of the project. 

1. **Define Scope & Success Criteria**  
   - **Log sources:** e.g. Apache/Nginx access logs, application logs, system events.  
   - **Anomaly types:** traffic spikes, error‐rate surges, unusual response times.  
   - **KPIs:** detection latency (<5 s), false‑positive rate (<5%), uptime of the detection pipeline.

2. **Provision Infrastructure**  
   - **Kafka cluster:** spin up a small cluster (3‐node) on Kubernetes or via managed service.  
   - **Storage:** Elasticsearch for indexed logs; you can also use S3 for raw backups.  
   - **Orchestration:** Kubernetes (with Helm/Terraform) to manage all services.

3. **Log Ingestion Pipeline**  
   - **Log shippers:** use Filebeat or Fluentd agents on your servers to tail logs and publish to Kafka topics.  
   - **Topic design:** e.g. `logs.app`, `logs.access`, `logs.system`, with sensible partitions for scale.

4. **Stream Processing Setup**  
   - **Framework:** Python + Faust (or Kafka Streams if you prefer Java/Scala).  
   - **Skeleton:** write a Faust “agent” that reads from your Kafka topics, parses each log line, and emits structured events downstream.

5. **Feature Extraction**  
   - **Time windows:** aggregate features over sliding windows (e.g. per minute):  
     - total requests, error count, average latency  
     - unique IPs, request‐per‐second  
   - **Normalization:** apply rolling z‑score or min‑max scaling online so your model sees consistent distributions.

6. **Select & Train Your Anomaly Detector**  
   - **Algorithm choice:**  
     - **Statistical:** Z‑score thresholding, EWMA control charts.  
     - **ML‑based:** Isolation Forest, One‑Class SVM, or an LSTM‑autoencoder for sequence anomalies.  
   - **Offline training:**  
     - Collect a week’s worth of logs; label “normal” intervals.  
     - Train your model offline in Jupyter/Python; persist artifacts (e.g. with joblib or TorchScript).

7. **Embed Inference into Stream**  
   - **Model loading:** have your Faust agent load the serialized model at startup.  
   - **Decision logic:** for each feature vector, compute anomaly score; if above threshold, emit an “alert” event to a new Kafka topic `logs.alerts`.

8. **Alert Sink & Dashboard**  
   - **Sink:** consume from `logs.alerts` and index into Elasticsearch with relevant metadata (timestamp, severity, raw log snippet).  
   - **Visualization:** set up a Kibana dashboard (or build custom React app) to:  
     - List recent anomalies  
     - Show time‑series graphs of error rates vs. anomaly flags  
     - Drill down into raw logs for forensic analysis

9. **End‑to‑End Testing**  
   - **Unit tests:**  
     - Test your log parser on synthetic lines.  
     - Test feature aggregator logic with controlled inputs.  
     - Verify model scoring produces expected anomaly flags.  
   - **Integration tests:**  
     - Spin up a mini‑Kafka+Faust+Elasticsearch stack (e.g. with Docker Compose) and feed sample logs through; assert that alerts appear in ES/Kibana.

10. **CI/CD Pipeline**  
    - **Code repo:** host your agents, model‑training notebooks, infra‑as‑code (Helm charts/Terraform) on GitHub.  
    - **Pipelines:**  
      - On push to `main`, run linters, unit tests, build Docker images, push to registry.  
      - On merge to `release`, deploy to staging cluster via GitHub Actions + Helm.

11. **Monitoring & Alerting**  
    - **Service health:** Prometheus + Grafana to track Faust consumer lag, Kafka broker health, Elasticsearch cluster status.  
    - **Model drift:** log rolling statistics (e.g. average anomaly score) and trigger alerts if they swing significantly over baseline.

12. **Iteration & Maintenance**  
    - **Threshold tuning:** adjust anomaly score cutoffs based on false‑positive/negative feedback.  
    - **Retraining schedule:** automate weekly or monthly retraining using Airflow or a simple cron, updating the model artifact in production.  
    - **Feedback loop:** build a simple UI for operators to mark alerts as true/false positives—feed these labels back into your next training run.

