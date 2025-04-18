# Anomalia

This project aims to detect server logs anomalies in real time. Here is a detailed outline of the project. 

Here’s your end‑to‑end roadmap for building the **Real‑Time Anomaly Detection** system locally with **Docker Compose**, using **Loki + Promtail + Grafana** instead of Elasticsearch/Kibana:

1. **Define Scope & Success Criteria**  
   - **Log sources**: e.g. Apache/Nginx access logs, application logs, system events.  
   - **Anomaly types**: traffic spikes, error‑rate surges, latency outliers.  
   - **KPIs**:  
     - Detection latency (goal: < 5 s from event to alert)  
     - False‑positive rate (< 5 %)  
     - Local stack uptime (Compose services healthy ≥ 99 %)

2. **Local Infra with Docker Compose**  
   - **Services** (all in one `docker-compose.yml`):  
     - **Zookeeper** → **Kafka** for messaging  
     - **Loki** for indexed logs & alerts  
     - **Promtail** for shipping raw logs into Loki  
     - **Grafana** (with Loki as default data source)  
     - **Faust app** for stream processing & anomaly inference  
     - **Filebeat** to tail host logs into Kafka  
   - **Volumes & Networks**: ensure each service can resolve others by their Compose service name.

   ```yaml
   version: '3.8'
   services:
     zookeeper:
       image: bitnami/zookeeper:3.8
       environment: [ALLOW_ANONYMOUS_LOGIN=yes]
     kafka:
       image: bitnami/kafka:3
       depends_on: [zookeeper]
       environment:
         KAFKA_CFG_ZOOKEEPER_CONNECT: zookeeper:2181
         ALLOW_PLAINTEXT_LISTENER: "yes"
     loki:
       image: grafana/loki:2.7.1
       ports: ["3100:3100"]
       volumes:
         - ./loki-config.yaml:/etc/loki/local-config.yaml:ro
       command: -config.file=/etc/loki/local-config.yaml
     promtail:
       image: grafana/promtail:2.7.1
       depends_on: [loki]
       volumes:
         - ./promtail-config.yaml:/etc/promtail/promtail.yaml:ro
         - /var/log:/var/log:ro
       command: -config.file=/etc/promtail/promtail.yaml
     grafana:
       image: grafana/grafana:9.5.0
       depends_on: [loki]
       ports: ["3000:3000"]
       environment:
         GF_SECURITY_ADMIN_USER: admin
         GF_SECURITY_ADMIN_PASSWORD: admin
         GF_AUTH_ANONYMOUS_ENABLED: 'true'
       volumes:
         - grafana-storage:/var/lib/grafana
         - ./provisioning:/etc/grafana/provisioning:ro
     faust-app:
       build: ./faust-app
       depends_on: [kafka, loki]
       environment:
         KAFKA_BROKER: kafka:9092
         LOKI_URL: http://loki:3100/loki/api/v1/push
       volumes:
         - ./faust-app:/app
       command: ['faust', '-A', 'worker.app', 'worker', '-l', 'info']
     filebeat:
       image: docker.elastic.co/beats/filebeat:7.17.0
       user: root
       volumes:
         - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
         - /var/log:/var/log:ro
       depends_on: [kafka]
   volumes:
     grafana-storage:
   ```

3. **Log Ingestion Pipeline**  
   - **Filebeat** tailed logs → publishes JSON events to Kafka topics:  
     - `logs.app`, `logs.access`, `logs.system`, etc.  
   - Ensure your `filebeat.yml` maps log paths to the right topics.

4. **Stream Processing with Faust**  
   - In `./faust-app/worker.py`:  
     1. Connect to Kafka (`KAFKA_BROKER`).  
     2. Parse incoming log events into structured records.  
     3. Window & aggregate (e.g. per‑minute counts, error rates, avg latency).  
     4. Normalize each feature vector (rolling z‑score or min–max).

5. **Model Training & Serialization (Offline)**  
   - **Collect** a representative batch of “normal” logs.  
   - **Train** your anomaly detector (e.g. Isolation Forest, One‑Class SVM, or LSTM‑autoencoder) in a Jupyter notebook.  
   - **Serialize** the trained model (joblib, ONNX, or TorchScript) and mount it into the Faust container via Docker volume.

6. **Real‑Time Inference & Loki Sink**  
   - Within the Faust agent:  
     ```python
     import os, time, json, requests
     LOKI_URL = os.environ['LOKI_URL']

     def send_to_loki(alert: dict):
         payload = {
           "streams": [{
             "stream": {"job": "anomaly-detector", "level": "warn"},
             "values": [[str(int(time.time() * 1e9)), json.dumps(alert)]]
           }]
         }
         resp = requests.post(LOKI_URL, json=payload)
         resp.raise_for_status()
     ```
   - For each scored feature vector above your threshold, call `send_to_loki(...)`.

7. **Grafana Dashboarding**  
   - **Data source**: Loki at `http://loki:3100`.  
   - **Panels**:  
     - **Log stream** panel querying `{job="anomaly-detector"}`  
     - **Graph** panel on `sum(rate({job="anomaly-detector"}[1m]))`  
     - **Heatmap** of anomaly severity over time  
     - **Drill-down**: raw logs from Promtail for forensic inspection

8. **Local Testing**  
   - **Unit tests** (pytest) for: parser logic, feature aggregation, model‑score thresholds.  
   - **Integration tests**:  
     ```bash
     docker-compose up --build --abort-on-container-exit
     ```
     Feed a directory of sample logs and assert alerts reach Loki (via its HTTP API).

9. **CI/CD for Local & Registry**  
   - **GitHub Actions**:  
     1. Lint & test Python code.  
     2. Build & push Docker images (`faust-app`, etc.).  
     3. On `main` merge, optionally run `docker-compose pull && docker-compose up -d` on your dev machine (or a dedicated VM).

10. **Monitoring & Healthchecks**  
    - Add `healthcheck:` blocks in Compose for Kafka, Loki, Promtail, Faust.  
    - Optionally stand up a minimal **Prometheus + Grafana** (another Compose project) to scrape Docker metrics and Faust consumer lag.

11. **Iteration & Maintenance**  
    - **Threshold tuning**: adjust based on operator feedback (false positives).  
    - **Retraining**: schedule a weekly job (cron or Airflow) to pull new “normal” logs, retrain, and replace the model artifact.  
    - **Feedback loop**: build a simple Grafana panel or form to mark alerts as true/false; export these labels for your next training cycle.
