# 🌐 CyberScraper 2077

<p align="center">
  <a href="https://get.brightdata.com/o-webscraper">
    <img src="https://i.ibb.co/5XfN86th/Start-collecting-728x90-1.png" alt="Collect-web-data-728x90" border="0">
  </a>
</p>

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
[![Scrapeless](https://img.shields.io/badge/Scrapeless%20Branch-Available-blue)](https://github.com/itsOwen/CyberScraper-2077/tree/CyberScrapeless-2077)

> Rip data from the net, leaving no trace. Welcome to the future of web scraping.

## 🔍 About

CyberScraper 2077 is not just another web scraping tool – it's a glimpse into the future of data extraction. Born from the neon-lit streets of a cyberpunk world, this AI-powered scraper uses OpenAI, Gemini and LocalLLM Models to slice through the web's defenses, extracting the data you need with unparalleled precision and style.

Whether you're a corpo data analyst, a street-smart netrunner, or just someone looking to pull information from the digital realm, CyberScraper 2077 has got you covered.

### 🚀 Two Powerful Versions Available

**Main Branch (Current)**: Traditional web scraping with advanced features
**[Scrapeless Integration Branch](https://github.com/itsOwen/CyberScraper-2077/tree/)**: Enterprise-grade scraping with [Scrapeless SDK](https://scrapeless.com) integration

<p align="center">
  <a href="https://get.brightdata.com/o-webscraper">
    <img src="https://i.ibb.co/qYS9TNXK/Collect-web-data-728x90-1.png" alt="Collect-web-data" border="0">
  </a>
</p>

<p align="center">
  <img src="https://i.postimg.cc/3NHb15wq/20240821-074556.gif">
</p>

## ✨ Features

### 🔧 Main Branch Features
- 🤖 **AI-Powered Extraction**: Utilizes cutting-edge AI models to understand and parse web content intelligently.
- 🖥️ **Sleek Streamlit Interface**: User-friendly GUI that even a chrome-armed street samurai could navigate.
- 🔄 **Multi-Format Support**: Export your data in JSON, CSV, HTML, SQL or Excel – whatever fits your cyberdeck.
- 🧅 **Tor Network Support**: Safely scrape .onion sites through the Tor network with automatic routing and security features.
- 🕵️ **Stealth Mode**: Implemented stealth mode parameters that help avoid detection as a bot.
- 🦙 **Ollama Support**: Use a huge library of open source LLMs.
- ⚡ **Async Operations**: Lightning-fast scraping that would make a Trauma Team jealous.
- 🧠 **Smart Parsing**: Structures scraped content as if it was extracted straight from the engram of a master netrunner.
- 💾 **Caching**: Implemented content-based and query-based caching using LRU cache and a custom dictionary to reduce redundant API calls.
- 📊 **Upload to Google Sheets**: Now you can easily upload your extracted CSV data to Google Sheets with one click.
- 🛡️ **Bypass Captcha**: Bypass captcha by using the -captcha at the end of the URL. (Currently only works natively, doesn't work on Docker)
- 🌐 **Current Browser**: The current browser feature uses your local browser instance which will help you bypass 99% of bot detections. (Only use when necessary)
- 🧭 **Navigate through the Pages (BETA)**: Navigate through the webpage and scrape data from different pages.

### ⚔️ Scrapeless Integration Branch Features
> **Want enterprise-grade scraping? Check out our [Scrapeless Integration Branch](https://github.com/itsOwen/CyberScraper-2077/tree/)!**

- 🔐 **Advanced Web Unlocker**: Utilizes Scrapeless's enterprise-grade anti-detection technology to bypass Cloudflare, Akamai, DataDome, and other protection systems.
- 🤖 **Automatic CAPTCHA Solving**: Seamlessly solves reCAPTCHA v2/v3, hCaptcha, and other verification challenges without human intervention.
- 🌍 **Global Proxy Network**: Access content from specific countries with Scrapeless's extensive proxy network.
- 🚀 **High-Speed Extraction**: Extract data at unprecedented speed without the overhead of local browser instances.
- 📈 **95% Success Rate**: Achieve ~95% success rate on even heavily protected sites (compared to ~60-70% with traditional methods).
- 🔄 **Auto-Updates**: Automatic updates to bypass new protection systems without manual maintenance.
- ⚡ **Lightweight Operations**: API-based calls instead of heavy browser instances.
- 🛡️ **Enterprise Security**: Professional-grade anti-bot detection bypassing.

### 📊 Scrapeless vs Traditional Comparison

| Feature | Main Branch | Scrapeless Branch |
|---------|-------------|-------------------|
| **Anti-Bot Protection** | Limited custom solutions | Enterprise-grade bypassing |
| **CAPTCHA Handling** | Manual intervention required | Automatic solving |
| **Proxy Management** | Basic single proxy | Global proxy network with country selection |
| **Success Rate** | ~60-70% on protected sites | ~95% on even heavily protected sites |
| **Resource Usage** | Heavy (browser instances) | Light (API calls only) |
| **Scalability** | Limited by local resources | Unlimited - cloud-based |
| **Maintenance** | Constant updates needed | Automatic updates |
| **Development Time** | Complex custom code | Simple API calls |

## 🎥 Demo

Check out our Redesigned and Improved Version of CyberScraper-2077 with more functionality [YouTube video](https://www.youtube.com/watch?v=TWyensVOIvs) for a full walkthrough of CyberScraper 2077's capabilities.

Check out our first build (Old Video) [YouTube video](https://www.youtube.com/watch?v=iATSd5Ijl4M)

## 🪟 For Windows Users

Please follow the Docker Container Guide given below, as I won't be able to maintain another version for Windows systems.

## 🛠 Installation

**Note: CyberScraper 2077 requires Python 3.10 or higher.**

### Main Branch Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/itsOwen/CyberScraper-2077.git
   cd CyberScraper-2077
   ```

2. Create and activate a virtual environment:
   ```bash
   virtualenv venv
   source venv/bin/activate  # Optional
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Install the playwright:
   ```bash
   playwright install
   ```

5. Set OpenAI & Gemini Key in your environment:

   Linux/Mac:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   export GOOGLE_API_KEY="your-api-key-here"
   ```

### Scrapeless Integration Branch Installation

For enterprise-grade scraping with automatic CAPTCHA solving and advanced anti-bot bypassing:

1. Clone the Scrapeless integration branch:
   ```bash
   git clone -b CyberScrapeless-2077 https://github.com/itsOwen/CyberScraper-2077.git
   cd CyberScraper-2077
   ```

2. Install requirements and set API keys:
   ```bash
   pip install -r requirements.txt
   
   # Set all API keys
   export OPENAI_API_KEY="your_openai_api_key_here"
   export GOOGLE_API_KEY="your_google_api_key_here"
   export SCRAPELESS_API_KEY="your_scrapeless_api_key_here"
   ```

3. Get your Scrapeless API key from [Scrapeless Dashboard](https://app.scrapeless.com/dashboard/account?tab=apiKey)

### Using Ollama (Both Branches)

Note: I only recommend using OpenAI and Gemini API as these models are really good at following instructions. If you are using open-source LLMs, make sure you have a good system as the speed of the data generation/presentation depends on how well your system can run the LLM. You may also have to fine-tune the prompt and add some additional filters yourself.

```bash
1. Setup Ollama using `pip install ollama`
2. Download Ollama from the official website: https://ollama.com/download
3. Now type: ollama pull llama3.1 or whatever LLM you want to use.
4. Now follow the rest of the steps below.
```

## 🐳 Docker Installation

If you prefer to use Docker, follow these steps to set up and run CyberScraper 2077:

### Main Branch Docker

1. Ensure you have Docker installed on your system.

2. Clone this repository:
   ```bash
   git clone https://github.com/itsOwen/CyberScraper-2077.git
   cd CyberScraper-2077
   ```

3. Build the Docker image:
   ```bash
   docker build -t cyberscraper-2077 .
   ```

4. Run the container:
   ```bash
   docker run -p 8501:8501 -e OPENAI_API_KEY="your-actual-api-key" -e GOOGLE_API_KEY="your-actual-api-key" cyberscraper-2077
   ```

### Scrapeless Branch Docker

For the Scrapeless integration branch:

```bash
git clone -b CyberScrapeless-2077 https://github.com/itsOwen/CyberScraper-2077.git
cd CyberScraper-2077
docker build -t cyberscrapeless .
docker run -p 8501:8501 \
  -e OPENAI_API_KEY="your-actual-api-key" \
  -e GOOGLE_API_KEY="your-actual-api-key" \
  -e SCRAPELESS_API_KEY="your-scrapeless-api-key" \
  cyberscrapeless
```

### Using Ollama with Docker

If you want to use Ollama with the Docker setup:

1. Install Ollama on your host machine following the instructions at https://ollama.com/download

2. Run Ollama on your host machine:
   ```bash
   ollama pull llama3.1
   ```

3. Find your host machine's IP address:
   - On Linux/Mac: `ifconfig` or `ip addr show`
   - On Windows: `ipconfig`

4. Run the Docker container with the host network and set the Ollama URL:
   ```bash
   docker run -e OLLAMA_BASE_URL=http://host.docker.internal:11434 -p 8501:8501 cyberscraper-2077
   ```

   Now visit the url: http://localhost:8501/
   
   On Linux you might need to use this below:
   ```bash
   docker run -e OLLAMA_BASE_URL=http://<your-host-ip>:11434 -p 8501:8501 cyberscraper-2077
   ```
   Replace `<your-host-ip>` with your actual host machine IP address.

5. In the Streamlit interface, select the Ollama model you want to use (e.g., "ollama:llama3.1").

Note: Ensure that your firewall allows connections to port 11434 for Ollama.

## 🚀 Usage

### Main Branch Usage

1. Fire up the Streamlit app:
   ```bash
   streamlit run main.py
   ```

2. Open your browser and navigate to `http://localhost:8501`.

3. Enter the URL of the site you want to scrape or ask a question about the data you need.

4. Ask the chatbot to extract the data in any format. Select whatever data you want to export or even everything from the webpage.

5. Watch as CyberScraper 2077 tears through the net, extracting your data faster than you can say "flatline"!

### Scrapeless Branch Usage

The Scrapeless integration branch offers the same user interface with enhanced capabilities:

1. **Enterprise Scraping**: Automatically bypasses advanced anti-bot systems like Cloudflare, Akamai, and DataDome
2. **CAPTCHA-Free**: No manual CAPTCHA solving required - handled automatically
3. **Global Access**: Choose proxy countries for geo-restricted content
4. **Higher Success Rate**: Achieve ~95% success rate on protected sites

Example usage with page ranges (both branches):
```
https://example.com/products 1-5
https://example.com/search?q=cyberpunk&page={page} 1-10
```

## 🌐 Multi-Page Scraping (BETA)

> **Note**: The multi-page scraping feature is currently in beta. While functional, you may encounter occasional issues or unexpected behavior. We appreciate your feedback and patience as we continue to improve this feature.

CyberScraper 2077 now supports multi-page scraping, allowing you to extract data from multiple pages of a website in one go. This feature is perfect for scraping paginated content, search results, or any site with data spread across multiple pages.

### How to Use Multi-Page Scraping

I suggest you enter the URL structure every time if you want to scrape multiple pages so it can detect the URL structure easily. It detects nearly all URL types.

1. **Basic Usage**:
   To scrape multiple pages, use the following format when entering the URL:
   ```
   https://example.com/page 1-5
   https://example.com/p/ 1-6
   https://example.com/xample/something-something-1279?p=1 1-3
   ```
   This will scrape pages 1 through 5 of the website.

2. **Custom Page Ranges**:
   You can specify custom page ranges:
   ```
   https://example.com/p/ 1-5,7,9-12
   https://example.com/xample/something-something-1279?p=1 1,7,8,9
   ```
   This will scrape pages 1 to 5, page 7, and pages 9 to 12.

3. **URL Patterns**:
   For websites with different URL structures, you can specify a pattern:
   ```
   https://example.com/search?q=cyberpunk&page={page} 1-5
   ```
   Replace `{page}` with where the page number should be in the URL.

4. **Automatic Pattern Detection**:
   If you don't specify a pattern, CyberScraper 2077 will attempt to detect the URL pattern automatically. However, for best results, specifying the pattern is recommended.

### Enhanced Multi-Page with Scrapeless

The [Scrapeless integration branch](https://github.com/itsOwen/CyberScraper-2077/tree/CyberScrapeless-2077) provides enhanced multi-page scraping with:
- **Automatic retry logic** for failed pages
- **Global proxy rotation** for different pages
- **CAPTCHA auto-solving** across all pages
- **Higher success rates** on protected paginated sites

### Tips for Effective Multi-Page Scraping

- Start with a small range of pages to test before scraping a large number.
- Be mindful of the website's load and your scraping speed to avoid overloading servers.
- Use the `simulate_human` option for more natural scraping behavior on sites with anti-bot measures.
- Consider using the [Scrapeless branch](https://github.com/itsOwen/CyberScraper-2077/tree/CyberScrapeless-2077) for heavily protected sites.
- Regularly check the website's `robots.txt` file and terms of service to ensure compliance.

### Example

```bash
URL Example : "https://news.ycombinator.com/?p=1 1-3 or 1,2,3,4"
```

If you want to scrape a specific page, just enter the query "please scrape page number 1 or 2". If you want to scrape all pages, simply give a query like "scrape all pages in csv" or whatever format you want.

## 🧅 Tor Network Scraping

> **Note**: The Tor network scraping feature allows you to access and scrape .onion sites. This feature requires additional setup and should be used responsibly and legally.

CyberScraper 2077 now supports scraping .onion sites through the Tor network, allowing you to access and extract data from the dark web safely and anonymously. This feature is perfect for researchers, security analysts, and investigators who need to gather information from Tor hidden services.

### Prerequisites

1. Install Tor on your system:
   ```bash
   # Ubuntu/Debian
   sudo apt install tor
   
   # macOS (using Homebrew)
   brew install tor
   
   # Start the Tor service
   sudo service tor start  # on Linux
   brew services start tor # on macOS
   ```

2. Install additional Python packages:
   ```bash
   pip install PySocks requests[socks]
   ```

### Using Tor Scraping

1. **Basic Usage**:
   Simply enter an .onion URL, and CyberScraper will automatically detect and route it through the Tor network:
   ```
   http://example123abc.onion
   ```

2. **Safety Features**:
   - Automatic .onion URL detection
   - Built-in connection verification
   - Tor Browser-like request headers
   - Automatic circuit isolation

### Configuration Options

You can customize the Tor scraping behavior by adjusting the following settings:
```python
tor_config = TorConfig(
    socks_port=9050,          # Default Tor SOCKS port
    circuit_timeout=10,        # Timeout for circuit creation
    auto_renew_circuit=True,   # Automatically renew Tor circuit
    verify_connection=True     # Verify Tor connection before scraping
)
```

### Security Considerations

- Always ensure you're complying with local laws and regulations
- Use a VPN in addition to Tor for extra security
- Be patient as Tor connections can be slower than regular web scraping
- Avoid sending personal or identifying information through Tor
- Some .onion sites may be offline or unreachable

### Docker Support

For Docker users, add these additional flags to enable Tor support:
```bash
docker run -p 8501:8501 \
  --network="host" \
  -e OPENAI_API_KEY="your-api-key" \
  cyberscraper-2077
```

### Example Usage

<p align="center">
  <img src="https://i.postimg.cc/3JvhgtMP/cyberscraper-onion.png" alt="CyberScraper 2077 Onion Scrape">
</p>

## Setup Google Sheets Authentication:

1. Go to the Google Cloud Console (https://console.cloud.google.com/).
2. Select your project.
3. Navigate to "APIs & Services" > "Credentials".
4. Find your existing OAuth 2.0 Client ID and delete it.
5. Click "Create Credentials" > "OAuth client ID".
6. Choose "Web application" as the application type.
7. Name your client (e.g., "CyberScraper 2077 Web Client").
8. Under "Authorized JavaScript origins", add:
   - http://localhost:8501
   - http://localhost:8502
   - http://127.0.0.1:8501
   - http://127.0.0.1:8502
9. Under "Authorized redirect URIs", add:
   - http://localhost:8501/
   - http://127.0.0.1:8501/
   - http://localhost:8502/
   - http://127.0.0.1:8502/
10. Click "Create" to generate the new client ID.
11. Download the new client configuration JSON file and rename it to `client_secret.json`.

## 🔧 Branch Selection Guide

### Choose Main Branch If:
- You need Tor network support for .onion sites
- You prefer local browser control
- You want to use your current browser session
- You're doing research or educational projects
- Budget is a primary concern (free tier friendly)

### Choose [Scrapeless Integration Branch](https://github.com/itsOwen/CyberScraper-2077/tree/CyberScrapeless-2077) If:
- You're scraping heavily protected sites (Cloudflare, Akamai, DataDome)
- You need enterprise-grade success rates (~95%)
- CAPTCHAs are blocking your scraping
- You want automatic proxy rotation
- You need reliable, scalable scraping for business use
- You value time over manual configuration

## Adjusting PlaywrightScraper Settings (optional)

Customize the `PlaywrightScraper` settings to fit your scraping needs. If some websites are giving you issues, you might want to check the behavior of the website:

```bash
use_stealth: bool = True,
simulate_human: bool = False,
use_custom_headers: bool = True,
hide_webdriver: bool = True,
bypass_cloudflare: bool = True:
```

Adjust these settings based on your target website and environment for optimal results.

You can also bypass the captcha using the ```-captcha``` parameter at the end of the URL. The browser window will pop up, complete the captcha, and go back to your terminal window. Press enter and the bot will complete its task.

## 🛠️ Advanced Features

### Scrapeless SDK Integration

For users of the [Scrapeless integration branch](https://github.com/itsOwen/CyberScraper-2077/tree/CyberScrapeless-2077), here are the core capabilities:

#### Web Unlocker API
```python
# Automatic anti-bot bypass
result = scrapeless.unlocker(
    actor="unlocker.webunlocker",
    input={
        "url": "https://protected-website.com",
        "proxy_country": "US",
        "js_render": True
    }
)
```

#### CAPTCHA Solver API
```python
# Automatic CAPTCHA solving
result = scrapeless.solver_captcha(
    actor="captcha.recaptcha",
    input={
        "version": "v2",
        "pageURL": "https://example.com",
        "siteKey": "your-site-key"
    }
)
```

#### Pre-built Scrapers
```python
# E-commerce scrapers
result = scrapeless.scraper(
    actor="scraper.shopee",
    input={"url": "https://shopee.com/product"}
)
```

## 🤝 Contributing

We welcome all cyberpunks, netrunners, and code samurais to contribute to CyberScraper 2077! Whether you're enhancing the main branch, improving the Scrapeless integration, or adding new features, your contributions are valued.

1. Fork the repository (choose your preferred branch)
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🔧 Troubleshooting

### Main Branch Issues
Ran into a glitch in the matrix? Let me know by adding the issue to this repo so that we can fix it together.

### Scrapeless Integration Issues
If you encounter issues with the [Scrapeless branch](https://github.com/itsOwen/CyberScraper-2077/tree/CyberScrapeless-2077):

1. **API Key Issues**: Verify your Scrapeless API key is valid
2. **High Success Rate Expected**: Scrapeless should achieve ~95% success on protected sites
3. **CAPTCHA Auto-Solve**: Should work automatically without manual intervention
4. **Proxy Network**: Test with different country codes if content is geo-restricted

## ❓ FAQ

**Q: Which branch should I use?**
A: Use the main branch for general scraping and Tor support. Use the [Scrapeless integration branch](https://github.com/itsOwen/CyberScraper-2077/tree/CyberScrapeless-2077) for enterprise-grade scraping with automatic CAPTCHA solving and anti-bot bypassing.

**Q: Is CyberScraper 2077 legal to use?**
A: CyberScraper 2077 is designed for ethical web scraping. Always ensure you have the right to scrape a website and respect their robots.txt file.

**Q: Can I use this for commercial purposes?**
A: Yes, under the terms of the MIT License. The Scrapeless integration branch is particularly well-suited for commercial use with its enterprise-grade features.

**Q: What's the success rate difference?**
A: Main branch: ~60-70% on protected sites. Scrapeless branch: ~95% on even heavily protected sites.

**Q: Do I need to pay for Scrapeless?**
A: Scrapeless offers various pricing tiers. Check their [pricing page](https://scrapeless.com/pricing) for current rates. The main branch remains free to use.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. Use it, mod it, sell it – just don't blame us if you end up flatlined.

## 📞 Contact

Got questions? Need support? Want to hire me for a gig?

- 📧 Email: owensingh72@gmail.com
- 🐦 Twitter: [@owensingh_](https://x.com/owensingh_)
- 💬 Website: [Portfolio](https://www.owensingh.com)

<p align="center">
  <a href="https://get.brightdata.com/o-webscraper">
    <img src="https://i.ibb.co/qYS9TNXK/Collect-web-data-728x90-1.png" alt="Start-collecting-728x90" border="0">
  </a>
</p>

## 🚨 Disclaimer

Listen up, choombas! Before you jack into this code, you better understand the risks:

1. This software is provided "as is", without warranty of any kind, express or implied.

2. The authors are not liable for any damages or losses resulting from the use of this software.

3. This tool is intended for educational and research purposes only. Any illegal use is strictly prohibited.

4. We do not guarantee the accuracy, completeness, or reliability of any data obtained through this tool.

5. By using this software, you acknowledge that you are doing so at your own risk.

6. You are responsible for complying with all applicable laws and regulations in your use of this software.

7. We reserve the right to modify or discontinue the software at any time without notice.

Remember, samurai: In the dark future of the NET, knowledge is power, but it's also a double-edged sword. Use this tool wisely, and may your connection always be strong and your firewalls impenetrable. Stay frosty out there in the digital frontier.

![Alt](https://repobeats.axiom.co/api/embed/80758496e19179f355d6d71c180db7aca66d396b.svg "Repobeats analytics image")

---

<p align="center">
  <strong>CyberScraper 2077 – Because in 2077, what makes someone a criminal? Getting caught.</strong>
</p>

<p align="center">
  Built with ❤️ and chrome by the streets of Night City | © 2077 Owen Singh
</p>
