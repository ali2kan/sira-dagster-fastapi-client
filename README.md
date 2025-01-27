# Dagster Job Trigger Service

A FastAPI service to trigger Dagster jobs via REST API, designed for integration with change detection services.

## Overview

This service provides REST endpoints to trigger Dagster jobs, primarily used with [changedetection.io](https://changedetection.io/) to update databases when external data sources change.

## Configuration

### Environment Variables

```bash
DAGSTER_HOST=10.10.10.34
DAGSTER_PORT=3000
DAGSTER_TIMEOUT_SECONDS=30
```

### Adding New Jobs

1. Edit `trigger_service/config.py` and add your job to `AVAILABLE_JOBS`:

```python
AVAILABLE_JOBS = {
    "countries_job": {
        "description": "Update countries database from external source",
        "repository_location": "dlt_pipelines",
        "repository_name": "__repository__",
    },
    "your_new_job": {
        "description": "Description of what this job does",
        "repository_location": "custom_location",  # Optional
        "repository_name": "custom_repo",         # Optional
    },
}
```

## Installation

### Using Docker (Recommended)

```bash
# Build the image
docker build -t dagster-trigger .

# Run the container
docker run -d \
  --name dagster-trigger \
  -p 8000:8000 \
  -e DAGSTER_HOST=your_dagster_host \
  -e DAGSTER_PORT=your_dagster_port \
  dagster-trigger
```

### Manual Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn trigger_service.trigger:app --host 0.0.0.0 --port 8000
```

## Usage

### API Endpoints

#### Health Check

```bash
curl http://localhost:8000/health
```

#### Trigger Job

```bash
curl -X POST http://localhost:8000/trigger/countries_job
```

### Integration with changedetection.io

1. Set up [changedetection.io](https://changedetection.io/) to monitor your data source
2. Configure a webhook notification:
   - URL: `http://your-service:8000/trigger/your_job_name`
   - Method: POST
   - Content Type: application/json

Example changedetection.io configurations:

#### Monitor REST API

```yaml
url: https://api.example.com/data
notification_urls:
  - http://localhost:8000/trigger/countries_job
```

#### Monitor Web Page

```yaml
url: https://example.com/data-page
notification_urls:
  - http://localhost:8000/trigger/countries_job
```

## Development

### Project Structure

```
trigger_service/
├── __init__.py
├── config.py      # Configuration settings
├── trigger.py     # Main FastAPI application
└── utils.py       # Optional utilities
```

### Adding New Features

1. Update configuration in `config.py`
2. Add new endpoints in `trigger.py`
3. Update tests if applicable
4. Update documentation

### Testing

```bash
# Run tests
pytest

# Check code style
flake8 trigger_service
```

## Monitoring

### Logs

Docker logs can be viewed with:

```bash
docker logs -f dagster-trigger
```

### Metrics

Access FastAPI metrics at `/metrics` endpoint (if enabled).

## Troubleshooting

Common issues and solutions:

1. **Connection Refused**
   - Check if Dagster is running
   - Verify DAGSTER_HOST and DAGSTER_PORT

2. **Job Not Found**
   - Verify job name in config.py
   - Check Dagster repository configuration

3. **Timeout Issues**
   - Adjust DAGSTER_TIMEOUT_SECONDS
   - Check network connectivity

## Security Considerations

1. Use HTTPS in production
2. Configure CORS appropriately
3. Add authentication if needed
4. Use environment variables for sensitive data

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

Create an issue in the repository for:

- Bug reports
- Feature requests
- General questions
