# Contributing to CyberScraper 2077

> "In 2077, what makes someone a contributor? Pushing code." - Johnny Silverhand

Thanks for considering contributing to CyberScraper 2077! This document outlines the process and guidelines for contributing to make the experience smooth for everyone involved.

## 🤝 Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please read it before contributing.

## 🚀 How to Contribute

### Setting Up Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/CyberScraper-2077.git
   cd CyberScraper-2077
   ```
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install
   ```

### Making Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Test your changes thoroughly
4. Commit your changes:
   ```bash
   git commit -m "feat: add new feature"
   ```
5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
6. Create a Pull Request

## 📝 Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/). Your commit messages should be structured as follows:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semi-colons, etc)
- `refactor`: Code refactoring
- `test`: Adding missing tests
- `chore`: Changes to build process or auxiliary tools

Example:
```
feat(scraper): add support for dynamic loading websites
```

## 🧪 Testing Guidelines

- Write tests for new features
- Ensure all tests pass before submitting PR
- Follow existing test patterns
- Include both unit and integration tests when applicable

## 📚 Documentation Guidelines

- Update README.md if adding new features
- Add docstrings to new functions/classes
- Include code examples when appropriate
- Keep documentation clear and concise

## 🏗️ Project Structure

```
CyberScraper-2077/
├── app/
│   ├── scrapers/
│   ├── utils/
│   └── ui_components/
├── src/
│   └── models/
├── tests/
└── docs/
```

- Place new scraper implementations in `app/scrapers/`
- Add utility functions in `app/utils/`
- UI components go in `app/ui_components/`
- Model-related code goes in `src/models/`

## 🎯 Feature Requests

- Use GitHub Issues to propose new features
- Tag feature requests with `enhancement`
- Provide clear use cases
- Discuss implementation approach

## 🐛 Bug Reports

When reporting bugs, include:
- Detailed description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Screenshots if applicable

## 🔍 Pull Request Process

1. Update documentation
2. Add/update tests
3. Ensure CI/CD pipeline passes
4. Get at least one code review
5. Squash commits if requested
6. Ensure branch is up to date with main

## ⚙️ Development Best Practices

1. Follow PEP 8 style guide
2. Use type hints
3. Keep functions/methods focused and small
4. Comment complex logic
5. Use meaningful variable/function names
6. Handle errors appropriately
7. Log important operations

## 🚫 What to Avoid

- Breaking existing functionality
- Introducing unnecessary dependencies
- Making large, unfocused PRs
- Ignoring code review feedback
- Modifying core functionality without discussion

## 🏆 Recognition

Contributors will be added to our README.md and CONTRIBUTORS.md files. We value and appreciate all contributions!

## 📞 Getting Help

- Create an issue for questions
- Join our Discord community
- Check existing documentation
- Look through closed issues

## 📜 License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

Remember: In Night City - and in open source - style is everything, choom. Let's keep the code clean and the commits conventional.
