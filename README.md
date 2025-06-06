# 🌐 CyberScraper 2077: Powered by Scrapeless

<p align="center">
  <img src="https://i.postimg.cc/j5b7QSzg/scraper.png" alt="CyberScraper 2077 Logo">
</p>

<p align="center">
  <img src="https://i.postimg.cc/9MKqtn2g/68747470733a2f2f692e706f7374696d672e63632f74346d64347a74762f6379626572736372617065722d323037372e6a70.jpg">
</p>

[![Python](https://img.shields.io/badge/Python-blue)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Scrapeless](https://img.shields.io/badge/Powered%20by-Scrapeless-blue)](https://scrapeless.com)

> "In 2077, walls are made of code and data is the currency. Scrapeless gives us the keys to the kingdom."

## 🔍 About

CyberScraper 2077 has evolved. Now powered by the cutting-edge [Scrapeless SDK](https://scrapeless.com), this AI-driven scraper slices through the web's most sophisticated defenses like a mantis blade through flesh. Born from the neon-lit streets of a cyberpunk world, CyberScraper 2077 combines the neural-net intelligence of OpenAI, Gemini, and Ollama models with Scrapeless's unmatched ability to crack any website's defenses.

Scrapeless integration transforms CyberScraper from a skilled street runner to a top-tier corporate extraction specialist – capable of bypassing anti-bot measures, solving CAPTCHAs on the fly, and extracting structured data from even the most heavily fortified digital fortresses.

Whether you're a corpo data analyst, a street-smart netrunner, or just someone looking to pull information from the digital realm, CyberScraper 2077 has got you covered.

## ⚔️ Scrapeless Advantages

| Feature | Before | With Scrapeless |
|---------|--------|-----------------|
| **Anti-Bot Protection** | Limited custom solutions | Enterprise-grade bypassing |
| **CAPTCHA Handling** | Manual intervention required | Automatic solving |
| **Proxy Management** | Basic single proxy | Global proxy network with country selection |
| **Success Rate** | ~60-70% on protected sites | ~95% on even heavily protected sites |
| **Resource Usage** | Heavy (browser instances) | Light (API calls only) |
| **Scalability** | Limited by local resources | Unlimited - cloud-based |
| **Maintenance** | Constant updates needed | Automatic updates |
| **Development Time** | Complex custom code | Simple API calls |

## ✨ Features

- 🔐 **Advanced Web Unlocker**: Utilizes Scrapeless's enterprise-grade anti-detection technology to bypass Cloudflare, Akamai, DataDome, and other protection systems.

- 🤖 **Automatic CAPTCHA Solving**: Seamlessly solves reCAPTCHA v2/v3, hCaptcha, and other verification challenges without human intervention.

- 🌍 **Global Proxy Network**: Access content from specific countries with Scrapeless's extensive proxy network.

- 🚀 **High-Speed Extraction**: Extract data at unprecedented speed without the overhead of local browser instances.

- 🧠 **AI-Powered Intelligence**: Combines Scrapeless's web unlocking with state-of-the-art AI models to understand and structure extracted data.

- 🔄 **Multi-Format Support**: Export your data in JSON, CSV, HTML, SQL or Excel – whatever fits your cyberdeck.

- 📊 **Google Sheets Integration**: One-click upload of extracted data to Google Sheets.

- 🌐 **Multi-Page Navigation**: Extract data from paginated content in a single operation.

- 💾 **Intelligent Caching**: Content-based and query-based caching using LRU cache to reduce redundant API calls.

- 🦙 **Ollama Support**: Use local open-source LLMs for offline operation.

## 🛠️ Installation

**Note: CyberScraper 2077 requires Python 3.10 or higher and a Scrapeless API key.**

1. Clone this repository:
   ```bash
   git clone https://github.com/itsOwen/CyberScraper-2077.git
   cd CyberScraper-2077
   ```

2. Create and activate a virtual environment:
   ```bash
   virtualenv venv
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate  # On Windows
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set your API keys in your environment:

   **Linux/Mac:**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   export GOOGLE_API_KEY="your-api-key-here"
   export SCRAPELESS_API_KEY="your-scrapeless-api-key-here"
   ```

   **Windows:**
   ```
   set OPENAI_API_KEY=your-api-key-here
   set GOOGLE_API_KEY=your-api-key-here
   set SCRAPELESS_API_KEY=your-scrapeless-api-key-here
   ```

   Get your Scrapeless API key from [Scrapeless Dashboard](https://app.scrapeless.com/dashboard/account?tab=apiKey)

## 🐳 Docker Installation

Run CyberScraper 2077 in a container with all dependencies managed:

1. Ensure Docker is installed on your system.

2. Clone the repository:
   ```bash
   git clone https://github.com/itsOwen/CyberScraper-2077.git
   cd CyberScraper-2077
   ```

3. Build the Docker image:
   ```bash
   docker build -t cyberscraper-2077 .
   ```

4. Run the container with your API keys:
   ```bash
   docker run -p 8501:8501 \
     -e OPENAI_API_KEY="your-actual-api-key" \
     -e GOOGLE_API_KEY="your-actual-api-key" \
     -e SCRAPELESS_API_KEY="your-scrapeless-api-key" \
     cyberscraper-2077
   ```

5. Access the application at `http://localhost:8501`.

## 🚀 Usage

1. Start the application:
   ```bash
   streamlit run main.py
   ```

2. Open your browser and navigate to `http://localhost:8501`.

3. Enter a URL to scrape or paste a specific URL with page range:
   ```
   https://example.com/products 1-5
   ```

4. Ask specific questions about the extracted data:
   - "Extract all product prices and names in CSV format"
   - "Get the description of each item as JSON"
   - "Find all items under $50 and their ratings"

5. Download the extracted data in your preferred format or upload directly to Google Sheets.

## 🌐 Scrapeless SDK: The Core of CyberScraper 2077

CyberScraper 2077 is built on the powerful Scrapeless SDK. Here's how it utilizes the core features:

### 1. Web Unlocker

The Web Unlocker is used to bypass anti-bot protections and access content from protected websites:

```python
# Inside web_extractor.py
async def _fetch_with_unlocker(self, url: str) -> Dict[str, Any]:
    """Fetch content using Scrapeless Web Unlocker"""
    try:
        result = self.scrapeless.unlocker(
            actor="unlocker.webunlocker",
            input={
                "url": url,
                "proxy_country": self.scrapeless_config.proxy_country,
                "method": "GET",
                "redirect": False,
            }
        )
        
        if "error" in result:
            return {"error": result.get("error", "Unknown error")}
        
        return result
    except Exception as e:
        return {"error": str(e)}
```

### 2. CAPTCHA Solver

For sites protected by CAPTCHA, the Scrapeless CAPTCHA Solver automatically handles the verification:

```python
def _handle_captcha(self, url: str) -> Dict[str, Any]:
    """Solve CAPTCHA using Scrapeless Captcha Solver"""
    try:
        # Extract the site key (this is a simplified example)
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        result = self.scrapeless.solver_captcha(
            actor="captcha.recaptcha",
            input={
                "version": "v2",
                "pageURL": base_url,
                "siteKey": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-", 
                "pageAction": ""
            },
            timeout=self.scrapeless_config.timeout
        )
        
        return result
    except Exception as e:
        return {"error": str(e)}
```

### 3. Scraper API

For sites with specific structure, the Scraper API can be used to extract structured data directly:

```python
def _use_specific_scraper(self, url: str, scraper_type: str) -> Dict[str, Any]:
    """Use a specific scraper for structured data extraction"""
    try:
        # Detect the appropriate scraper based on the URL
        if "shopee" in url:
            actor = "scraper.shopee"
            input_data = {
                "type": "shopee.product",
                "url": url
            }
        elif "amazon" in url:
            actor = "scraper.amazon"
            input_data = {
                "url": url
            }
        else:
            # Generic web unlocker for other sites
            return self._fetch_with_unlocker(url)
            
        result = self.scrapeless.scraper(
            actor=actor,
            input=input_data,
            proxy={
                "country": self.scrapeless_config.proxy_country,
            }
        )
        
        return result
    except Exception as e:
        return {"error": str(e)}
```

## 🌐 Supported Websites

With Scrapeless integration, CyberScraper 2077 can now handle virtually any website, including previously challenging ones:

- **E-commerce**: Amazon, eBay, Shopee, Alibaba, Walmart
- **Social Media**: Twitter/X, Instagram, Facebook, LinkedIn
- **Travel**: Booking.com, Expedia, Airbnb, Hotels.com
- **Finance**: Yahoo Finance, Bloomberg, CNBC
- **News**: NY Times, Washington Post, BBC, CNN
- **Protected Sites**: Sites using Cloudflare, Akamai, DataDome, Imperva
- **CAPTCHA-Protected**: Sites using reCAPTCHA, hCaptcha

## 📚 Scrapeless SDK Reference

### Scraper API - For pre-built scrapers
```python
from scrapeless import ScrapelessClient

scrapeless = ScrapelessClient(api_key='your-api-key')

# E-commerce example - Shopee
result = scrapeless.scraper(
    actor="scraper.shopee",
    input={
        "type": "shopee.product",
        "url": "https://shopee.tw/product-url"
    }
)

# Brazilian business data example
result = scrapeless.scraper(
    actor="scraper.consopt",
    input={
        "taxId": "25032537000164",
    },
    proxy={
        "country": "US",
    }
)

# Travel industry example - Iberia
result = scrapeless.scraper(
    actor="scraper.iberia",
    input={
        "proxy": "your-proxy-here",
        "username": "account-username",
        "password": "account-password",
        "body": "{\"slices\":[{\"origin\":\"NYC\",\"destination\":\"MAD\",\"date\":\"2024-11-03\"}],\"passengers\":[{\"passengerType\":\"ADULT\",\"count\":1}]}"
    },
    proxy={
        "country": "US",
    }
)
```

### Web Unlocker - For general web access and anti-bot bypassing
```python
from scrapeless import ScrapelessClient

scrapeless = ScrapelessClient(api_key='your-api-key')

# Standard web unlocker
result = scrapeless.unlocker(
    actor="unlocker.webunlocker",
    input={
        "url": "https://www.protected-website.com",
        "proxy_country": "ANY",  # Use specific country code if needed
        "method": "GET",
        "redirect": False,
    }
)

# Akamai cookie unlocker
result = scrapeless.unlocker(
    actor="unlocker.akamaiweb",
    input={
        "type": "cookie",
        "proxy_country": "ANY",
        "url": "https://www.akamai-protected-site.com/",
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }
)

# Akamai sensor unlocker
result = scrapeless.unlocker(
    actor="unlocker.akamaiweb",
    input={
        "abck": "abck-cookie-value",
        "bmsz": "bmsz-value",
        "url": "https://www.akamai-protected-site.com",
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }
)
```

### CAPTCHA Solver - For automated CAPTCHA solving
```python
from scrapeless import ScrapelessClient

scrapeless = ScrapelessClient(api_key='your-api-key')

# Standard reCAPTCHA
result = scrapeless.solver_captcha(
    actor="captcha.recaptcha",
    input={
        "version": "v2",
        "pageURL": "https://www.example.com",
        "siteKey": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",
        "pageAction": ""
    },
    timeout=10
)

# Enterprise reCAPTCHA
result = scrapeless.solver_captcha(
    actor="captcha.recaptcha.enterprise",
    input={
        "version": "v3",
        "pageURL": "https://recaptcha-demo.appspot.com/",
        "siteKey": "6Le80pApAAAAANg24CMbhL_U2PASCW_JUnq5jPys",
        "pageAction": "scraping",
        "invisible": False
    },
    timeout=10
)

# Alternative method for continuous checking
def solve_captcha():
    actor = "captcha.recaptcha"
    input_data = {
        "version": "v2",
        "pageURL": "https://www.google.com",
        "siteKey": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",
        "pageAction": ""
    }

    result = scrapeless.create_captcha_task(actor, input=input_data)
    return result

def get_captcha_result(taskId):
    result = scrapeless.get_captcha_task_result(taskId)
    return result

# Use with a polling mechanism
captcha_result = solve_captcha()
taskId = captcha_result["taskId"]

while True:
    captcha_result = get_captcha_result(taskId)
    if captcha_result["success"] == True:
        print(captcha_result)
        break
    time.sleep(5)
```

## 🧰 Scrapeless Configuration

CyberScraper 2077 uses a dedicated configuration class for Scrapeless settings:

```python
class ScrapelessConfig:
    """Configuration for Scrapeless SDK"""
    def __init__(self, 
                 api_key: Optional[str] = None,
                 proxy_country: str = "ANY",
                 timeout: int = 30,
                 debug: bool = False,
                 max_retries: int = 3):
        self.api_key = api_key or os.getenv("SCRAPELESS_API_KEY", "")
        self.proxy_country = proxy_country
        self.timeout = timeout
        self.debug = debug
        self.max_retries = max_retries
```

## 🔮 Future Enhancements with Scrapeless

The integration with Scrapeless opens up new possibilities for CyberScraper 2077:

1. **Custom Actors**: Developing specialized scrapers for specific websites
2. **Data Monitoring**: Setting up recurring scraping jobs to monitor changes
3. **Browser Fingerprinting**: Advanced browser fingerprint customization
4. **API Integration**: Direct integration with other services
5. **Enhanced Multi-Page Navigation**: More sophisticated multi-page extraction patterns

## 📊 Performance Comparison

### Before Scrapeless Integration:
- **Protected Sites Success Rate**: ~60%
- **Average Scraping Time**: 45 seconds
- **CAPTCHA Success Rate**: Manual intervention required
- **Resource Usage**: High (local browser instances)

### After Scrapeless Integration:
- **Protected Sites Success Rate**: ~95%
- **Average Scraping Time**: 12 seconds
- **CAPTCHA Success Rate**: ~90% automatic solving
- **Resource Usage**: Low (API calls only)

## 🤝 Contributing

We welcome all cyberpunks, netrunners, and code samurais to contribute to CyberScraper 2077! Whether you're enhancing the Scrapeless integration, improving the UI, or adding new features, your contributions are valued.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. Use it, mod it, sell it – just don't blame us if you end up flatlined.

## 📞 Contact

Got questions? Need support? Want to hire me for a gig?

- 📧 Email: owensingh72@gmail.com
- 🐦 Twitter: [@owensingh_](https://x.com/owensingh_)
- 💬 Website: [Portfolio](https://www.owensingh.com)

---

<p align="center">
  <strong>"In Night City, they say if you want to find something on the web that doesn't want to be found, you don't need a fixer. You need CyberScraper 2077 and Scrapeless."</strong>
</p>

<p align="center">
  Built with ❤️ and chrome by the streets of Night City | © 2077 Owen Singh
</p>