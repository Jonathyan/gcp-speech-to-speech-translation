# Phase 2 Hybrid STT Service - Cloud Run Deployment Guide

## 🚀 Quick Deploy

### Prerequisites
1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and configured
3. **Docker** installed
4. **Required APIs** enabled (done automatically by deploy script)

### One-Command Deployment
```bash
# Clone and deploy
git clone <your-repo>
cd gcp-speech-to-speech-translation

# Set your project ID
export GOOGLE_CLOUD_PROJECT="your-project-id"

# Deploy Phase 2 service
./deploy.sh
```

## 📋 Step-by-Step Deployment

### 1. **Prepare Environment**
```bash
# Set environment variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME="hybrid-stt-service"

# Authenticate with Google Cloud
gcloud auth login
gcloud config set project $PROJECT_ID
```

### 2. **Enable APIs**
```bash
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    speech.googleapis.com \
    translate.googleapis.com \
    texttospeech.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com
```

### 3. **Create Service Account**
```bash
# Create service account
gcloud iam service-accounts create hybrid-stt-service \
    --display-name="Hybrid STT Service Account"

# Grant permissions
SERVICE_ACCOUNT="hybrid-stt-service@$PROJECT_ID.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/speech.editor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/translate.editor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/texttospeech.editor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/monitoring.metricWriter"
```

### 4. **Deploy to Cloud Run**
```bash
# Build and deploy
./deploy.sh
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_STREAMING` | `true` | Enable Phase 2 streaming mode |
| `QUALITY_THRESHOLD` | `0.7` | Quality threshold for mode decisions |
| `STREAMING_THRESHOLD_BYTES` | `5000` | Chunk size threshold for streaming |
| `FAILURE_THRESHOLD` | `3` | Failures before fallback |
| `MAX_CONCURRENT_SESSIONS` | `20` | Max concurrent streaming sessions |
| `LOG_LEVEL` | `INFO` | Logging level |

### Resource Configuration
- **CPU**: 1 vCPU (1000m)
- **Memory**: 2 GiB
- **Concurrency**: 10 concurrent requests per instance
- **Scaling**: 1-10 instances (auto-scaling)
- **Timeout**: 1 hour max request timeout

## 📊 Monitoring & Observability

### Health Checks
- **Main**: `GET /health` - Service health
- **Readiness**: `GET /ready` - Readiness probe
- **Phase 2**: `GET /health/phase2` - Hybrid STT status

### Logs
```bash
# View logs
gcloud logs tail --service=$SERVICE_NAME

# Filter Phase 2 logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" --filter='jsonPayload.phase2=true'
```

### Metrics Dashboard
```bash
# Import monitoring dashboard
gcloud monitoring dashboards create --config-from-file=monitoring-dashboard.json
```

### Key Metrics
- **Request Rate**: Requests/second
- **Latency**: P50/P95 response times  
- **Quality Score**: Connection quality (0-1)
- **Mode Distribution**: Streaming vs buffered usage
- **Fallback Rate**: Automatic fallbacks/minute
- **Error Rate**: 4xx/5xx errors

## 🧪 Testing the Deployment

### Basic Health Check
```bash
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION --format="value(status.url)")

curl $SERVICE_URL/health
```

### WebSocket Test
```javascript
// Connect to WebSocket endpoint
const ws = new WebSocket(`${SERVICE_URL.replace('https', 'wss')}/ws/speak/test-stream`);

ws.onopen = () => {
    console.log('Connected to Phase 2 Hybrid STT Service');
    
    // Send audio chunk
    ws.send(audioChunk);
};

ws.onmessage = (event) => {
    console.log('Received:', event.data);
};
```

### Phase 2 Features Test
```bash
# Check Phase 2 status
curl $SERVICE_URL/health/phase2

# Expected response:
{
  "status": "ok", 
  "phase2_hybrid": "active",
  "streaming_enabled": true,
  "service_stats": {
    "hybrid_service": {
      "total_chunks": 0,
      "streaming_chunks": 0, 
      "buffered_chunks": 0,
      "active_streams": 0
    }
  }
}
```

## 🔒 Security

### IAM Permissions
- Service runs with least-privilege service account
- Only necessary Google Cloud API permissions
- Network access controlled via Cloud Run security

### Environment Security  
- Secrets managed via Google Secret Manager (recommended)
- Environment variables for non-sensitive config
- TLS/HTTPS enforced for all traffic

## 📈 Performance Tuning

### Scaling Configuration
```bash
# Update scaling
gcloud run services update $SERVICE_NAME \
    --region=$REGION \
    --min-instances=2 \
    --max-instances=20 \
    --concurrency=15
```

### Memory Optimization
```bash
# Increase memory for high-volume workloads
gcloud run services update $SERVICE_NAME \
    --region=$REGION \
    --memory=4Gi \
    --cpu=2
```

### Phase 2 Tuning
```bash
# Environment variables for performance tuning
gcloud run services update $SERVICE_NAME \
    --region=$REGION \
    --set-env-vars STREAMING_THRESHOLD_BYTES=3000,QUALITY_THRESHOLD=0.8,MAX_CONCURRENT_SESSIONS=30
```

## 🚨 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" --limit=50

# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID --filter="bindings.members:serviceAccount:hybrid-stt-service@$PROJECT_ID.iam.gserviceaccount.com"
```

#### High Latency
- Check `/health/phase2` for quality scores
- Review fallback rates in monitoring
- Consider increasing `QUALITY_THRESHOLD`
- Scale up instances for better performance

#### Memory Issues
- Increase memory allocation: `--memory=4Gi`
- Reduce `MAX_CONCURRENT_SESSIONS`
- Monitor memory usage in Cloud Console

#### Streaming Failures
- Check Google Cloud API quotas
- Verify service account permissions  
- Review `FAILURE_THRESHOLD` and `RECOVERY_INTERVAL_SECONDS`

### Support Commands
```bash
# Service details
gcloud run services describe $SERVICE_NAME --region=$REGION

# Recent revisions
gcloud run revisions list --service=$SERVICE_NAME --region=$REGION

# Traffic allocation
gcloud run services update-traffic $SERVICE_NAME --region=$REGION --to-latest
```

## 🎯 Success Metrics

### Performance Targets
- ✅ **Latency**: <800ms end-to-end translation
- ✅ **Availability**: >99.5% uptime
- ✅ **Throughput**: 50+ concurrent streams
- ✅ **Quality**: >95% successful transcriptions

### Phase 2 Specific Metrics
- **Streaming Mode Usage**: >70% when conditions allow
- **Fallback Recovery**: <2s switching time
- **Quality Score**: >0.7 average
- **Auto-scaling**: Efficient resource utilization

---

## 🚀 **Ready for Production!**

Your Phase 2 Hybrid STT Service is now deployed on Google Cloud Run with:
- ✅ Hybrid streaming/buffered architecture
- ✅ Intelligent quality-based mode switching
- ✅ Resilient fallback mechanisms
- ✅ Production monitoring and alerting
- ✅ Auto-scaling and high availability

**Service URL**: Check deployment output or run:
```bash
gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)"
```