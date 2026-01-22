# Contributing to Dexcom Sync System

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment for all contributors

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. Create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, Docker version)
   - Relevant log excerpts

### Suggesting Features

1. Open an issue with the "enhancement" label
2. Describe the feature and its benefits
3. Provide use cases
4. Consider implementation complexity

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/dexcom-sync.git
cd dexcom-sync

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest black flake8 mypy

# Setup pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

## Coding Standards

### Python Style
- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use meaningful variable names

### Code Formatting
```bash
# Format code with black
black .

# Check with flake8
flake8 .

# Type check with mypy
mypy .
```

### Naming Conventions
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

### Documentation
- Add docstrings to all functions and classes
- Use Google-style docstrings
- Update README.md for new features
- Comment complex logic

Example:
```python
def fetch_readings(start_date: datetime, end_date: datetime) -> List[Dict]:
    """Fetch glucose readings from Dexcom API.
    
    Args:
        start_date: Beginning of date range
        end_date: End of date range
        
    Returns:
        List of reading dictionaries with timestamp, value, and trend
        
    Raises:
        ConnectionError: If API is unreachable
        AuthenticationError: If credentials are invalid
    """
    pass
```

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_dexcom_client.py
```

### Writing Tests
- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use fixtures for setup/teardown
- Mock external API calls

Example:
```python
import pytest
from dexcom_client import DexcomClient

def test_get_readings():
    """Test fetching readings from Dexcom API"""
    client = DexcomClient()
    # Mock API response
    # Assert expected behavior
    pass
```

## Adding New Features

### New Connector
1. Create file in `connectors/` directory
2. Implement required methods:
   - `is_configured()` - Check if connector is setup
   - `upload_readings()` - Upload data to destination
3. Add to `connectors/__init__.py`
4. Update `sync_manager.py` to include new connector
5. Add settings fields to `templates/settings.html`
6. Update README.md with setup instructions
7. Add tests

### UI Changes
1. Maintain retro industrial theme
2. Ensure responsive design
3. Test on multiple browsers
4. Keep accessibility in mind

### Security Features
1. Always encrypt sensitive data
2. Use parameterized queries (no SQL injection)
3. Validate all user inputs
4. Follow OWASP guidelines

## Database Migrations

If you modify models:
1. Update `models.py`
2. Test migration path from previous version
3. Document any manual migration steps
4. Consider backward compatibility

## Documentation

### README Updates
- Keep installation steps current
- Update configuration examples
- Add new features to feature list
- Update troubleshooting section

### Code Comments
- Explain "why" not "what"
- Document edge cases
- Note any workarounds or limitations

## Release Process

1. Update version numbers
2. Update CHANGELOG.md
3. Tag release
4. Build Docker image
5. Test deployment
6. Update documentation

## Areas Needing Contribution

### High Priority
- [ ] Unit test coverage
- [ ] Integration tests
- [ ] Performance optimization
- [ ] Error handling improvements

### Medium Priority
- [ ] Additional connectors (InfluxDB, MongoDB)
- [ ] Data export features
- [ ] Alert/notification system
- [ ] Multi-user support

### Low Priority
- [ ] UI themes
- [ ] Mobile app
- [ ] Advanced analytics
- [ ] Webhooks

## Questions?

- Open a discussion on GitHub
- Check existing issues and documentation
- Reach out to maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Dexcom Sync System! 🎉
