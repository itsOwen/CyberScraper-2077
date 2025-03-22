# CyberScraper API

A RESTful API service for web scraping using the powerful AI-driven capabilities of CyberScraper 2077.

## Features

- 🚀 **Simple REST API** for submitting scraping tasks
- 🔄 **Asynchronous processing** with task status tracking
- 🤖 **Multiple AI models** supported (OpenAI, Google Gemini)
- 📊 **Various output formats** (JSON, CSV, Excel, HTML, SQL)
- 🛡️ **API key security** with header-based authentication
- 🐳 **Docker support** for easy deployment

## API Endpoints

### POST /scrape

Submit a new scraping task.

**Headers:**
- `X-OpenAI-Key`: Your OpenAI API key (required for OpenAI models)
- `X-Google-Key`: Your Google API key (required for Gemini models)

**Request Body:**
```json
{
  "url": "https://example.com/page-to-scrape",
  "instructions": "Extract all product names and prices",
  "format": "json",
  "model": "gpt-4o-mini"
}
```

**Response:**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ab",
  "status": "pending",
  "message": "Task created and processing will begin shortly. Check /task/{task_id} for results."
}
```

### GET /task/{task_id}

Check the status and get results of a scraping task.

**Response:**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ab",
  "status": "completed",
  "url": "https://example.com/page-to-scrape",
  "format": "json",
  "data": [...],
  "error": null,
  "completed_at": "2025-03-22T14:30:45.123456"
}
```

## Installation and Deployment

### Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/kanalive/CyberScraper-2077.git
   cd CyberScraper-2077
   ```

2. Build and run the Docker container:
   ```bash
   docker build -t cyberscraper-api -f api_Dockerfile .
   docker run -p 8000:8000 cyberscraper-api
   ```

3. The API will be available at `http://localhost:8000`

### Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/kanalive/CyberScraper-2077.git
   cd CyberScraper-2077
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install fastapi uvicorn
   playwright install
   ```

3. Run the API server:
   ```bash
   uvicorn cyberscraper_api:app --host 0.0.0.0 --port 8000
   ```

## Client Usage Examples

### Using the Python Client

```bash
python api_client_example.py "https://example.com" "Extract all product names and prices" --openai-key "your-openai-key" --format json
```

### Using cURL

```bash
# Submit a scraping task
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -H "X-OpenAI-Key: your-openai-key" \
  -d '{
    "url": "https://example.com",
    "instructions": "Extract all product names and prices",
    "format": "json",
    "model": "gpt-4o-mini"
  }'

# Check task status and get results
curl -X GET "http://localhost:8000/task/your-task-id"
```

### Using JavaScript/Node.js

```javascript
const axios = require('axios');

async function scrapeWithAPI() {
  try {
    // Submit scraping task
    const response = await axios.post('http://localhost:8000/scrape', {
      url: 'https://example.com',
      instructions: 'Extract all product names and prices',
      format: 'json',
      model: 'gpt-4o-mini'
    }, {
      headers: {
        'X-OpenAI-Key': 'your-openai-key'
      }
    });
    
    const taskId = response.data.task_id;
    console.log(`Task submitted. ID: ${taskId}`);
    
    // Poll for results
    let result;
    let attempts = 0;
    
    while (attempts < 12) {
      await new Promise(resolve => setTimeout(resolve, 5000));
      
      const statusResponse = await axios.get(`http://localhost:8000/task/${taskId}`);
      result = statusResponse.data;
      
      if (result.status === 'completed' || result.status === 'failed') {
        break;
      }
      
      console.log(`Still processing... (attempt ${attempts + 1})`);
      attempts++;
    }
    
    console.log('Result:', result);
    return result;
  } catch (error) {
    console.error('Error:', error.response ? error.response.data : error.message);
  }
}

scrapeWithAPI();
```

## API Configuration Options

The API can be configured using environment variables:

- `HOST`: Host address (default: 0.0.0.0)
- `PORT`: Port number (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)
- `WORKERS`: Number of Uvicorn workers (default: 1)

Example:
```bash
HOST=127.0.0.1 PORT=5000 LOG_LEVEL=DEBUG uvicorn cyberscraper_api:app
```

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: The request was successful
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Task not found
- `500 Internal Server Error`: Server-side error

Error responses include a detail message explaining the issue.

## Limitations

- Long-running scraping tasks may timeout depending on server configuration
- Some websites with advanced bot protection might be difficult to scrape
- API keys are sent in headers and should be transmitted over HTTPS in production

## License

This project is licensed under the MIT License - see the LICENSE file for details.