# 🌐 CyberScraper 2077

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

> Rip data from the net, leaving no trace. Welcome to the future of web scraping.

## 🔍 About

CyberScraper 2077 is not just another web scraping tool – it's a glimpse into the future of data extraction. Born from the neon-lit streets of a cyberpunk world, this AI-powered scraper uses OpenAI to slice through the web's defenses, extracting the data you need with unparalleled precision and style.

Whether you're a corpo data analyst, a street-smart netrunner, or just someone looking to pull information from the digital realm, CyberScraper 2077 has got you covered.

<p align="center">
  <img src="https://i.postimg.cc/3NHb15wq/20240821-074556.gif">
</p>

## ✨ Features

- 🤖 **AI-Powered Extraction**: Utilizes cutting-edge AI models to understand and parse web content intelligently.
- 💻 **Sleek Streamlit Interface**: User-friendly GUI that even a chrome-armed street samurai could navigate.
- 🔄 **Multi-Format Support**: Export your data in JSON, CSV, HTML, SQL or Excel – whatever fits your cyberdeck.
- 🌐 **Stealth Mode**: Implemented stealth mode parameters that helps it from getting detected as bot.
- 🤖 **Ollama Support**: Use a huge libarary of open source LLMs.
- 🚀 **Async Operations**: Lightning-fast scraping that would make a Trauma Team jealous.
- 🧠 **Smart Parsing**: Structures scraped content as if it was extracted straight from the engram of a master netrunner.
- 🛡️ **Ethical Scraping**: Respects robots.txt and site policies. We may be in 2077, but we still have standards.
- 📄 **Caching**: We implemented content-based and query-based caching using LRU cache and a custom dictionary to reduce redundant API calls.
- ✅ **Upload to Google Sheets**: Now you can easily upload your extract csv data to google sheets with one click.
- 🌐 **Proxy Mode (Coming Soon)**: Built-in proxy support to keep you ghosting through the net.
- 🛡️ **Navigate through the Pages (Coming Soon)**: Navigate through the webpage and scrap the data from different pages. 

## 🎥 Demo

Check out our Redisgned and Improved Version of CyberScraper-2077 with more functionality [YouTube video](https://www.youtube.com/watch?v=TWyensVOIvs) for a full walkthrough of CyberScraper 2077's capabilities.

Check out our first build (Old Video) [YouTube video](https://www.youtube.com/watch?v=iATSd5Ijl4M)

## 🪟 For Windows Users

Please follow the Docker Container Guide given below, As I won't be able to maintain another version for windows system.

## 🛠 Installation

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

5. Set OpenAI Key in your enviornment:

   Linux/Mac:
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```
   For Windows:
   ```bash
   set OPENAI_API_KEY=your-api-key-here
   ```
6. If you want to use the Ollama:

Note: I only recommend using OpenAI API as GPT4o-mini is really good at following instructions, If you are using open-source LLMs make sure you have a good system as the speed of the data generation/presentation depends on how good your system is in running the LLM and also you may have to fine-tune the prompt and add some additional filters yourself.
   ```bash
   1. Setup Ollama using `pip install ollama`
   2. Download the Ollama from the official website: https://ollama.com/download
   3. Now type: ollama pull llama3.1 or whatever LLM you want to use.
   4. Now follow the rest of the steps below.
   ```

## 🐳 Docker Installation

If you prefer to use Docker, follow these steps to set up and run CyberScraper 2077:

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
   - Without OpenAI API key:
     ```bash
     docker run -p 8501:8501 cyberscraper-2077
     ```
   - With OpenAI API key:
     ```bash
     docker run -p 8501:8501 -e OPENAI_API_KEY='your-actual-api-key' cyberscraper-2077
     ```

5. Open your browser and navigate to `http://localhost:8501`.

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
   On Linux you might need to use this below:
   ```bash
   docker run -e OLLAMA_BASE_URL=http://<your-host-ip>:11434 -p 8501:8501 cyberscraper-2077
   ```
   Replace `<your-host-ip>` with your actual host machine IP address.

5. In the Streamlit interface, select the Ollama model you want to use (e.g., "ollama:llama3.1").

Note: Ensure that your firewall allows connections to port 11434 for Ollama.

## 🚀 Usage

1. Fire up the Streamlit app:
   ```bash
   streamlit run main.py
   ```

2. Open your browser and navigate to `http://localhost:8501`.

3. Enter the URL of the site you want to scrape or ask a question about the data you need.

4. Ask the chatbot to extract the data in any format, Select whatever data you want to export or even everything from the webpage.

4. Watch as CyberScraper 2077 tears through the net, extracting your data faster than you can say "flatline"!

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

## Adjusting PlaywrightScraper Settings (optional)

Customize the `PlaywrightScraper` settings to fit your scraping needs, If some websites are giving you issues, You might want to check the behaviour of the website:

```bash
use_stealth: bool = True,
simulate_human: bool = False,
use_custom_headers: bool = True,
hide_webdriver: bool = True,
bypass_cloudflare: bool = True:
```

Adjust these settings based on your target website and environment for optimal results.

## 🤝 Contributing

We welcome all cyberpunks, netrunners, and code samurais to contribute to CyberScraper 2077!

## 🔧 Troubleshooting

Ran into a glitch in the matrix? Let me know by adding the issue to this repo so that we can fix it together.

## ❓ FAQ

**Q: Is CyberScraper 2077 legal to use?**
A: CyberScraper 2077 is designed for ethical web scraping. Always ensure you have the right to scrape a website and respect their robots.txt file.

**Q: Can I use this for commercial purposes?**
A: Yes, under the terms of the MIT License. But remember, in Night City, there's always a price to pay, Just kidding!

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. Use it, mod it, sell it – just don't blame us if you end up flatlined.

## 📞 Contact

Got questions? Need support? Want to hire me for a gig?

- 📧 Email: owensingh72@gmail.com
- 🐦 Twitter: [@_owensingh](https://x.com/_owensingh)
- 💬 Website: [Portfolio](https://www.owensingh.com)

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

---

<p align="center">
  <strong>CyberScraper 2077 – Because in 2077, what makes someone a criminal? Getting caught.</strong>
</p>

<p align="center">
  Built with ❤️ and chrome by the streets of Night City | © 2077 Owen Singh
</p>
